#!/usr/bin/env python3
"""
Batch-geocode an NWS Locations CSV using the free official US Census Bureau
Batch Geocoder (no API key required) and verify coordinates against Territory
Helper GeoJSON territory boundaries.

Why this helps:
  - Resolves free-form note addresses into exact house-level Latitude & Longitude
    and standardized City / State / PostalCode so New World Scheduler can pin
    every address cleanly on the territory map.
  - Checks each geocoded (Latitude, Longitude) point against the matching
    territory polygon in territories.json so mis-geocoded pins are flagged rather
    than accidentally dropped into the wrong territory.
  - Writes pure UTF-8 CSV (NO BOM) with exact NWS headers including Category,
    CategoryCode, TerritoryNumber, Suffix, Latitude, Longitude.

Usage:
    python geocode_nws_locations.py locations.csv territories.json locations_geocoded.csv
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

CENSUS_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BATCH_SIZE = 1000  # Census accepts up to 10,000; 1,000 keeps requests fast & resilient


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test for a GeoJSON ring [[lon, lat], ...]."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_near_ring(lon: float, lat: float, ring: list[list[float]], tol_deg: float = 0.0015) -> bool:
    """Return True if point is within tol_deg (~150m) of any edge of the ring (handles border roads)."""
    if len(ring) < 2:
        return False
    tol_sq = tol_deg * tol_deg
    for i in range(len(ring) - 1):
        ax, ay = ring[i][0], ring[i][1]
        bx, by = ring[i + 1][0], ring[i + 1][1]
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            px, py = ax, ay
        else:
            t = max(0.0, min(1.0, ((lon - ax) * dx + (lat - ay) * dy) / seg_len_sq))
            px, py = ax + t * dx, ay + t * dy
        if (lon - px) ** 2 + (lat - py) ** 2 <= tol_sq:
            return True
    return False


def point_in_geometry(lon: float, lat: float, geom: dict[str, Any] | None) -> bool | None:
    """Return True if point is inside or on border (~150m) of Polygon/MultiPolygon, False if outside, None if no geometry."""
    if not geom or not geom.get("coordinates"):
        return None
    gtype = geom.get("type")
    coords = geom["coordinates"]
    if gtype == "Polygon":
        if point_near_ring(lon, lat, coords[0]):
            return True
        if not point_in_ring(lon, lat, coords[0]):
            return False
        for hole in coords[1:]:
            if point_in_ring(lon, lat, hole):
                return False
        return True
    if gtype == "MultiPolygon":
        for poly in coords:
            if point_near_ring(lon, lat, poly[0]):
                return True
            if point_in_ring(lon, lat, poly[0]):
                if not any(point_in_ring(lon, lat, hole) for hole in poly[1:]):
                    return True
        return False
    return None


def split_territory_number(raw: str) -> tuple[str, str]:
    s = str(raw or "").strip()
    m = re.match(r"^(\d+)\s*-\s*([A-Za-z0-9]+)$", s)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^([A-Za-z]+)\s*-\s*(\d+)$", s)
    if m:
        return m.group(2), m.group(1)
    m = re.match(r"^(\d+)([A-Za-z]+)$", s)
    if m:
        return m.group(1), m.group(2)
    return s, ""


def build_territory_geom_map(geojson_path: Path) -> dict[tuple[str, str, str], dict[str, Any] | None]:
    """Map (Category, TerritoryNumber, Suffix) -> GeoJSON geometry."""
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    mapping: dict[tuple[str, str, str], dict[str, Any] | None] = {}
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        cat = (props.get("TerritoryType") or "").strip()
        num, suf = split_territory_number(props.get("TerritoryNumber") or "")
        mapping[(cat, num, suf)] = feat.get("geometry")
    return mapping


def send_census_batch(batch_rows: list[tuple[str, str, str, str, str]]) -> dict[str, dict[str, str]]:
    """
    Submit [(id, street_addr, city, state, zip), ...] to US Census Batch Geocoder.
    Returns {id: {"match": "Match"|"No_Match"|..., "matched_addr": ..., "lon": ..., "lat": ...}}.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in batch_rows:
        writer.writerow(row)
    csv_bytes = buf.getvalue().encode("utf-8")

    boundary = "----NWSCensusGeocodeBoundary7e4b2a9"
    parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="benchmark"\r\n\r\n'
        f"Public_AR_Current\r\n".encode("utf-8"),
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="addressFile"; filename="addresses.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n".encode("utf-8")
        + csv_bytes
        + b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)

    req = urllib.request.Request(
        CENSUS_BATCH_URL,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "NWS-Territory-Geocoder/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    results: dict[str, dict[str, str]] = {}
    reader = csv.reader(io.StringIO(raw))
    for cols in reader:
        if len(cols) < 3:
            continue
        rid = cols[0].strip()
        match_status = cols[2].strip()
        matched_addr = cols[4].strip() if len(cols) > 4 else ""
        coords = cols[5].strip() if len(cols) > 5 else ""
        lon, lat = "", ""
        if "," in coords:
            lon_s, lat_s = coords.split(",", 1)
            lon, lat = lon_s.strip(), lat_s.strip()
        results[rid] = {
            "match": match_status,
            "matched_addr": matched_addr,
            "lon": lon,
            "lat": lat,
        }
    return results


def parse_census_matched_address(matched_addr: str) -> tuple[str, str, str]:
    """Extract (City, State, PostalCode) from Census matched string '123 MAIN ST, SPRINGFIELD, IL, 62704'."""
    parts = [p.strip() for p in matched_addr.split(",")]
    if len(parts) >= 4:
        city = parts[-3].title()
        state = parts[-2].upper()
        zipcode = parts[-1]
        return city, state, zipcode
    return "", "", ""


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python geocode_nws_locations.py <input.csv> [boundaries.json] [output.csv]")
        sys.exit(1)

    input_csv = Path(sys.argv[1])
    geojson_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("territories.json")
    output_csv = (
        Path(sys.argv[3])
        if len(sys.argv) > 3
        else input_csv.with_name(f"{input_csv.stem}_Geocoded{input_csv.suffix}")
    )

    # Read input CSV (strip BOM if present!)
    with input_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    geom_map = build_territory_geom_map(geojson_path) if geojson_path.exists() else {}

    # Ensure CategoryCode column exists on every row
    for r in rows:
        if not r.get("CategoryCode"):
            cat = (r.get("Category") or "").strip()
            r["CategoryCode"] = cat[0].upper() if cat else ""

    # Prepare geocodable rows (skip PO Boxes and rows without street number/street)
    to_geocode: list[tuple[int, tuple[str, str, str, str, str]]] = []
    for idx, r in enumerate(rows):
        num = (r.get("Number") or "").strip()
        street = (r.get("Street") or "").strip()
        if not num or not street or street.lower() == "po box":
            continue
        if r.get("Latitude") and r.get("Longitude"):
            continue
        street_line = f"{num} {street}"
        city = (r.get("City") or "").strip()
        state = (r.get("State") or "").strip()
        zipcode = (r.get("PostalCode") or "").strip().split("-")[0]
        to_geocode.append((idx, (str(idx), street_line, city, state, zipcode)))

    print(f"Loaded {len(rows)} rows; submitting {len(to_geocode)} street addresses to US Census Batch Geocoder...")

    matched_in_poly = 0
    matched_outside_poly = 0
    matched_no_poly = 0
    unmatched = 0

    total_batches = math.ceil(len(to_geocode) / BATCH_SIZE) if to_geocode else 0
    for b in range(total_batches):
        chunk = to_geocode[b * BATCH_SIZE : (b + 1) * BATCH_SIZE]
        print(f"  Batch {b + 1}/{total_batches} ({len(chunk)} addresses)...", flush=True)
        res = send_census_batch([item[1] for item in chunk])
        for idx, _ in chunk:
            info = res.get(str(idx))
            if not info or info["match"] != "Match" or not info["lat"] or not info["lon"]:
                unmatched += 1
                continue
            r = rows[idx]
            lat = float(info["lat"])
            lon = float(info["lon"])
            key = (r.get("Category", ""), r.get("TerritoryNumber", ""), r.get("Suffix", ""))
            geom = geom_map.get(key)
            inside = point_in_geometry(lon, lat, geom)

            if inside is False:
                # Don't put a wrong-territory pin into NWS; keep lat/lon blank & note it
                matched_outside_poly += 1
                continue

            r["Latitude"] = f"{lat:.6f}"
            r["Longitude"] = f"{lon:.6f}"

            # Fill missing City/State/PostalCode from Census standardized match
            c_city, c_state, c_zip = parse_census_matched_address(info["matched_addr"])
            if c_city and not r.get("City"):
                r["City"] = c_city
            if c_state and not r.get("State"):
                r["State"] = c_state
            if c_zip and not r.get("PostalCode"):
                r["PostalCode"] = c_zip

            if inside is True:
                matched_in_poly += 1
            else:
                matched_no_poly += 1

    # Write clean UTF-8 CSV (NO BOM!) with official NWS headers
    out_cols = [
        "Category",
        "CategoryCode",
        "TerritoryNumber",
        "Suffix",
        "Type",
        "Status",
        "Number",
        "Street",
        "ApartmentNumber",
        "City",
        "State",
        "PostalCode",
        "Name",
        "Phone",
        "Notes",
        "Latitude",
        "Longitude",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("\nDone!")
    print(f"  Output CSV:                    {output_csv}")
    print(f"  Geocoded & inside territory:   {matched_in_poly}")
    print(f"  Geocoded (no boundary polygon):{matched_no_poly}")
    print(f"  Skipped (fell outside polygon):{matched_outside_poly}")
    print(f"  Not matched by US Census:      {unmatched}")


if __name__ == "__main__":
    main()
