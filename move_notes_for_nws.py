#!/usr/bin/env python3
"""
Adjust a Territory Helper GeoJSON export for New World Scheduler (NWS).

In New World Scheduler's GeoJSON import:
  - `properties.description`    -> imports into NWS "Notes"
  - `properties.TerritoryNotes` -> imports into NWS "Custom"

This script cleans HTML formatting and entities (like &nbsp;) out of each
territory's `TerritoryNotes`, prepends the existing `description` label (if any)
at the top, saves the combined result into `description`, and clears
`TerritoryNotes` so the notes appear cleanly inside NWS "Notes" instead of
"Custom". Each territory is processed independently so notes always stay
matched to their own territory.

Usage:
    python move_notes_for_nws.py [input.json] [output.json]

Defaults:
    input.json  -> territories.json
    output.json -> <input_stem>_NWS_Ready.json (e.g., territories_NWS_Ready.json)
"""

from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


BLOCK_TAGS = {
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "blockquote",
    "hr",
}


class _SimpleHTMLToText(HTMLParser):
    """Convert non-table HTML fragments into clean plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in {"style", "script", "colgroup", "col"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if t == "br":
            self.parts.append("\n")
        elif t == "li":
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")
            self.parts.append("• ")
        elif t in BLOCK_TAGS:
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"style", "script", "colgroup", "col"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if t in BLOCK_TAGS or t == "li":
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        # Ignore pure indentation/newlines from HTML source formatting between tags
        if data.strip() == "" and "\n" in data:
            return
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth:
            return
        if name == "yacute":
            # Wingdings checkbox artifact pasted from Word (used on Do Not Call lines)
            self.parts.append("- ")
        else:
            self.parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        if self._skip_depth:
            return
        self.parts.append(html.unescape(f"&#{name};"))

    def get_text(self) -> str:
        raw = "".join(self.parts)
        return normalize_text(raw)


def normalize_text(text: str) -> str:
    """Normalize whitespace, non-breaking spaces, and blank lines."""
    # Replace non-breaking spaces and odd unicode whitespace with regular spaces
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for line in text.split("\n"):
        # Collapse runs of multiple spaces/tabs into a single space
        cleaned = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(cleaned)

    # Collapse consecutive blank lines to at most one blank line
    out: list[str] = []
    prev_blank = True  # also trims leading blank lines
    for line in lines:
        if line == "":
            if not prev_blank:
                out.append("")
                prev_blank = True
        else:
            out.append(line)
            prev_blank = False

    # Trim trailing blank lines
    while out and out[-1] == "":
        out.pop()

    return "\n".join(out)


def fragment_to_text(fragment: str) -> str:
    parser = _SimpleHTMLToText()
    parser.feed(fragment)
    parser.close()
    return parser.get_text()


def render_table(table_html: str) -> str:
    """Convert an HTML <table> into clean plain text based on its structure."""
    row_matches = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table_html, re.IGNORECASE | re.DOTALL)
    grid: list[list[str]] = []
    for row_html in row_matches:
        cell_matches = re.findall(
            r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row_html, re.IGNORECASE | re.DOTALL
        )
        cells = [fragment_to_text(c) for c in cell_matches]
        grid.append(cells)

    if not grid:
        return ""

    max_cols = max((len(r) for r in grid), default=0)
    non_empty_cells = [c for r in grid for c in r if c]
    if not non_empty_cells:
        return ""

    multiline_count = sum(1 for c in non_empty_cells if "\n" in c)
    is_block_layout = multiline_count > (len(non_empty_cells) * 0.25)

    # Case 1: Wide column-oriented sheet (e.g., 10 columns where each column is a street + addresses)
    if max_cols >= 4 and not is_block_layout:
        col_blocks: list[str] = []
        for col_idx in range(max_cols):
            col_items = [
                row[col_idx].replace("\n", " ")
                for row in grid
                if col_idx < len(row) and row[col_idx]
            ]
            if col_items:
                col_blocks.append("\n".join(col_items))
        return "\n\n".join(col_blocks)

    # Case 2: Multi-line card/block layout table (each cell is a street section)
    if is_block_layout:
        return "\n\n".join(non_empty_cells)

    # Case 3: Standard 1-3 column tabular rows (e.g., Phone | Name, Number | City Zip)
    lines: list[str] = []
    for row in grid:
        non_empty = [c.replace("\n", " ") for c in row if c]
        if not non_empty:
            lines.append("")
        else:
            lines.append(" - ".join(non_empty))

    return normalize_text("\n".join(lines))


def html_notes_to_plain_text(raw_html: str) -> str:
    """Convert a Territory Helper HTML TerritoryNotes field to clean plain text."""
    # Split out any <table>...</table> blocks so they can be formatted smartly
    table_pattern = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
    segments: list[str] = []
    pos = 0
    for match in table_pattern.finditer(raw_html):
        before = raw_html[pos : match.start()]
        if before.strip():
            rendered = fragment_to_text(before)
            if rendered:
                segments.append(rendered)
        table_text = render_table(match.group(0))
        if table_text:
            segments.append(table_text)
        pos = match.end()

    after = raw_html[pos:]
    if after.strip():
        rendered = fragment_to_text(after)
        if rendered:
            segments.append(rendered)

    return normalize_text("\n\n".join(segments))


def transform_geojson(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Move cleaned TerritoryNotes into description and clear TerritoryNotes."""
    stats = {
        "total": 0,
        "combined_label_and_notes": 0,
        "moved_notes_only": 0,
        "kept_label_only": 0,
        "empty_both": 0,
    }

    for feature in data.get("features", []):
        stats["total"] += 1
        props = feature.get("properties")
        if not isinstance(props, dict):
            continue

        existing_desc = (props.get("description") or "").strip()
        raw_notes = props.get("TerritoryNotes")
        cleaned_notes = html_notes_to_plain_text(raw_notes) if raw_notes else ""

        if existing_desc and cleaned_notes:
            props["description"] = f"{existing_desc}\n\n{cleaned_notes}"
            stats["combined_label_and_notes"] += 1
        elif cleaned_notes:
            props["description"] = cleaned_notes
            stats["moved_notes_only"] += 1
        elif existing_desc:
            props["description"] = existing_desc
            stats["kept_label_only"] += 1
        else:
            props["description"] = None
            stats["empty_both"] += 1

        # Clear TerritoryNotes so NWS Custom field stays blank
        props["TerritoryNotes"] = None

    return data, stats


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("territories.json")
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.with_name(f"{input_path.stem}_NWS_Ready{input_path.suffix}")

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    updated, stats = transform_geojson(data)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Total territories processed:    {stats['total']}")
    print(f"  Label + Notes combined:       {stats['combined_label_and_notes']}")
    print(f"  Notes moved (no prior label): {stats['moved_notes_only']}")
    print(f"  Label kept (no notes):        {stats['kept_label_only']}")
    print(f"  Neither label nor notes:      {stats['empty_both']}")


if __name__ == "__main__":
    main()
