# Territory Helper → New World Scheduler Migration Tools

Two lightweight, 100% offline helper tools designed to make migrating congregation territories from **Territory Helper** to **New World Scheduler (NWS)** faster and cleaner—especially for congregations that keep letter-writing or rural addresses inside Territory Helper's **Territory Notes** field.

---

## The Three Migration Challenges These Tools Solve

1. **Non-Standard Territory Numbering & Colliding Categories**
   - Many congregations in Territory Helper use prefix-first or text territory numbers (like `R-81`, `H-3`, `A12`, `North 5`, or `Downtown`), duplicate numbers inside the same category, or categories that share the same first letter (`Town` & `Telephone`, or `Category H` & `Category R` both defaulting to `C`).
   - In New World Scheduler, prefix-first numbers import as **Territory 0** and duplicate numbers overwrite each other.
   - **Tab 1** automatically audits and fixes territory numbering (`R-81` → `81-R`, `A12` → `12-A`, deduplicates collisions, optionally assigns unique Category Codes) and keeps both the GeoJSON and Locations CSV 100% synchronized.

2. **Territory Helper Notes Landing in NWS "Custom" with HTML Artifacts**
   - When importing a Territory Helper GeoJSON export into New World Scheduler:
     - `properties.description` imports into NWS **Notes** (often just a short title like `Territory #3`).
     - `properties.TerritoryNotes` imports into NWS **Custom**—and because Territory Helper stores notes as rich HTML, non-breaking spaces (`&nbsp;`) and formatting artifacts can appear in the imported text.
   - Congregations that store addresses or working notes in Territory Helper's Notes need those moved cleanly into NWS **Notes** (with HTML and `&nbsp;` cleaned up) and matched 1-to-1 to each territory.

3. **Converting Free-Form Addresses in Territory Notes into NWS Locations (CSV)**
   - Many congregations only pinned **Do Not Calls** as Locations in Territory Helper while typing letter-writing or rural street addresses inside each territory's Notes (using varied formats: street headings with `Address: ####`, comma-separated house numbers, bulleted lists, tables, PO Boxes, or multi-line address blocks).
   - Manually re-typing thousands of addresses into NWS Locations is time-consuming. **Tab 3** parses those note formats automatically and outputs Territory Helper's exact 19-column Locations CSV (or NWS standard/boundary CSV) ready for import.

---

## Included Files

### 1. `index.html` *(Recommended — Zero-Install Browser App)*
A single, self-contained HTML file (usable live via **GitHub Pages** or downloaded for offline use) that runs locally in any modern web browser (Chrome, Edge, Safari, Firefox) on Windows, macOS, or Chromebook. **No installation, no Python, and no internet connection required**—just double-click the file and drag-and-drop a Territory Helper `.json` export.

It guides congregations through **three synchronized tabs** in exact migration order:

#### Tab 1: Fix Territory Setup & Naming
- **Automatic NWS Readiness Audit:** Scans every territory on upload and flags prefix-first/non-numeric numbers (`R-81`, `H-3`, `A12`, `Downtown`, blanks), duplicate numbers within the same category, and categories sharing the same first-letter code.
- **One-Click Auto-Fixes:**
  - Normalizes numbers to NWS-safe `<Number>-<Suffix>` format (`R-81` → `81-R`, `A12` → `12-A`, fills blank numbers sequentially).
  - Auto-resolves duplicate numbers in the same category (`12` → `12-B`, `12-C`) so NWS never overwrites territories.
  - **Auto-Assign Unique Category Codes** button (plus inline Category Name & Code editing) so congregations starting fresh get clean, collision-free codes (`B`, `H`, `R`, `T`, `P`, `L`, etc.), while congregations already in NWS can leave codes blank to preserve existing naming.
  - Optional toggle to append each category's code as a suffix when missing (e.g., `3` in Rural → `3-R`).
- **Synchronized Pipeline:** Every fix applied in Tab 1 automatically updates both the **NWS-Ready GeoJSON (Tab 2)** and the **Locations CSV (Tab 3)** so territories and addresses always match 1-to-1.

#### Tab 2: Move Notes to NWS Notes (GeoJSON)
- Moves each territory's `TerritoryNotes` into `description` (NWS **Notes**) while keeping every territory matched 1-to-1 and preserving all boundary geometries untouched.
- Cleans HTML tags (`<p>`, `<div>`, `<table>`, `<ul>`, `<li>`, etc.) and HTML entities (`&nbsp;`, `&ndash;`, `&rsquo;`, etc.) into clean, readable plain text—including smart formatting for pasted tables.
- Offers three handling modes for existing short labels in `description`:
  1. **Prepend** existing label at the top of Notes & clear Custom *(Recommended)*
  2. **Replace** Notes with Territory Helper notes & clear Custom
  3. **Swap** Notes and Custom
- Includes a live **Before / After** preview dropdown per territory before downloading `*_NWS_Ready.json`.

#### Tab 3: Extract Locations → NWS CSV
- **Multi-format Address Parser:** Automatically extracts addresses from common Territory Helper note layouts:
  - Street headings followed by `Address: ####` lines
  - Street headings followed by comma-separated or one-per-line house numbers
  - Bulleted full addresses (`• 123 Main St`, `o 123 Main St`)
  - Multi-line Name / Street / City-State-ZIP address blocks
  - Multi-column tables (e.g., spreadsheet tables pasted into Territory Helper notes)
  - PO Boxes and apartment/facility unit lists
  - Optional Phone territory lists (off by default, toggleable on)
- **Automatic City / State / ZIP Detection:** Reads territory-wide hints (such as `All addresses are ...` or `Sample Address:` blocks) and street-level city/ZIP headers, while skipping sample envelope examples so they are not duplicated.
- **Flexible Do Not Call (DNC) Handling:**
  - *Include & mark Status as `DNC`*
  - *Exclude DNCs* — ideal for congregations that already have Do Not Calls pinned in Territory Helper and import them separately, preventing duplicate DNC entries
  - *Export DNCs Only*
- **Smart Deduplication:** Merges duplicate addresses within the same territory and preserves `DNC` status if an address appears in both a `DO NOT CALL` section and a street list.
- **Territory Number, CategoryCode & Suffix Preservation:** Automatically preserves `Category`, derives `CategoryCode` (e.g., `C`), and splits combined Territory Helper numbers like `3-H` into `TerritoryNumber = 3` and `Suffix = H` (matching NWS territory IDs like `C-2-B`, `C-3-H`, etc., so existing territories are never overwritten).
- **Optional Latitude / Longitude Geocoding:** Includes a built-in **"Resolve Lat/Lon (Filtered Rows)"** button (using OpenStreetMap Nominatim for single-territory testing) plus a companion bulk script (`geocode_nws_locations.py`) that uses the free official US Census Batch Geocoder and verifies every coordinate against your GeoJSON territory boundaries.
- **Interactive Review & Edit Table:**
  - Filter by Category, Territory, Status (`Available` / `DNC`), or search text.
  - Click any cell to edit values inline, click a Status badge to toggle `Available` / `DNC`, delete rows, or manually add rows.
  - **Unparsed Lines Review Drawer:** Lists any unusual lines (such as prose instructions or typos in original notes like `Address: 1o4`) grouped by territory so a Territory Servant can spot-check nothing was missed.
- **Clean UTF-8 (No BOM) CSV Export:**
  - Exports clean UTF-8 CSV without a Byte Order Mark (BOM) so column 1 is always recognized cleanly.
  - Supports Territory Helper's exact 19-column Locations CSV format (default), NWS Standard CSV, and NWS Boundary-Match CSV.
  - Download **all locations** as one CSV, or download a **single territory / filtered CSV** (recommended for testing 1 territory first).

---

### 2. `move_notes_for_nws.py` *(Optional Command-Line Script)*
A standalone Python 3 script (standard library only—no external packages needed) that performs the **GeoJSON Notes cleanup and move** (Tab 2) from the command line for batch processing or automation.

**Usage:**
```bash
python move_notes_for_nws.py TerritoryHelperExport.json Output_NWS_Ready.json
```
- Leaves the original `.json` file untouched.
- Writes a new `*_NWS_Ready.json` file with cleaned plain-text notes in `description` and `TerritoryNotes` set to `null`.

### 3. `geocode_nws_locations.py` *(Optional Bulk US Geocoder Script)*
A standalone Python 3 script (standard library only, no API key needed) that batch-geocodes an exported NWS Locations CSV using the free official **US Census Bureau Batch Geocoder** (`geocoding.geo.census.gov`) and verifies every returned `(Latitude, Longitude)` point against your Territory Helper GeoJSON boundaries (with a ~150m border-road tolerance so border-highway houses stay matched while wrong-town pins are rejected).

**Usage:**
```bash
python geocode_nws_locations.py Locations.csv TerritoryHelperExport.json Locations_Geocoded.csv
```

---

## Privacy & Security

Congregation territory files contain sensitive personal data (addresses, resident names, and Do Not Call records). Both tools were built with privacy first:

- **100% Offline & Local:** All parsing and file generation happen strictly on the user's own computer.
- **Zero Network Calls & Zero External Dependencies:** The HTML tool loads no external scripts, CDNs, fonts, or analytics.
- **Fully Auditable Plain Text:** Both `index.html` and `move_notes_for_nws.py` are unminified, human-readable source files that the NWS team can inspect line by line.

---

## Quick Start for Congregations

### Step 1: Fix Territory Setup & Naming
1. Export your territories from Territory Helper as GeoJSON (`.json`).
2. Double-click `index.html` to open it in your browser and drop in the `.json` file.
3. On **Tab 1 (Fix Territory Setup & Naming)**, review the automatic audit:
   - Prefix-first or text numbers (e.g., `R-81`, `H-3`, `A12`, `Downtown`) are automatically normalized to NWS-safe `<Number>-<Suffix>` format (`81-R`, `3-H`, `12-A`).
   - Duplicate territory numbers within the same category are automatically given unique suffixes (`12-B`, `12-C`) so NWS never overwrites them.
   - Starting fresh in NWS? Click **Auto-Assign Unique Category Codes** (or edit category names/codes inline). Already imported into NWS? Leave Category Codes blank so your existing codes stay unchanged.

### Step 2: Move Notes & Import Territories into NWS
1. Open **Tab 2 (Move Notes → NWS Notes)**, preview a territory's Before / After view, and click **Download NWS-Ready GeoJSON (.json)**. *(This includes all Tab 1 naming fixes and cleaned plain-text Notes.)*
2. Import that `.json` file into New World Scheduler so all territories, boundaries, and clean notes are in place.

### Step 3: Extract & Import Locations (Addresses) as CSV
1. Open **Tab 3 (Extract Locations → NWS CSV)**. *(Automatically uses your Tab 1 normalized category names and territory numbers.)*
2. Keep **CSV Export Format** on **Territory Helper Locations CSV** (recommended), set your **Default State**, and choose your **Do Not Calls (DNC) Handling** option *(select **Exclude DNCs** if you already import pinned Do Not Calls separately from Territory Helper)*.
3. *(Optional)* To add map pins (`Latitude`/`Longitude`), either click **Resolve Lat/Lon (Filtered Rows)** for a single territory or run `geocode_nws_locations.py` for fast bulk US geocoding.
4. Click **Download NWS Locations CSV** and import into New World Scheduler via **Territories → Import → Addresses (Locations) from Territory Helper** (or **Territory Addresses from CSV file** if using the NWS Standard/Boundary CSV format).

---

## Technical Reference

### GeoJSON Field Mapping Used
| Territory Helper GeoJSON Field | New World Scheduler Target | Action Taken |
|---|---|---|
| `properties.description` | **Notes** | Receives existing label + cleaned `TerritoryNotes` |
| `properties.TerritoryNotes` | **Custom** | Cleared (`null`) so Custom stays clean |
| All other properties & `geometry` | Territory metadata & boundaries | Preserved identically (1-to-1) |

### CSV Formats Generated (Clean UTF-8, No BOM)

1. **Territory Helper Locations CSV *(Default — for NWS: `Import → Addresses (Locations) from Territory Helper`)*:**
   Matches Territory Helper's native 19-column Locations export schema verbatim:
   ```text
   Territory type,Territory number,Location type,Status,Latitude,Longitude,Address,Number,Street,Unit,Floor,City,County,Postal code,State,Country code,Last visited,Last updated,Date created
   ```
   - Uses Territory Helper's exact `Status` values (`Default` and `Do not call`), `Location type` (`House`, `Apartment`, `Business`, `Other`), and normalized `<number>-<suffix>` territory numbers (e.g., `3-H`, `81-R`).

2. **NWS Standard / Boundary-Match CSV *(for NWS: `Import → Territory Addresses from CSV file`)*:**
   ```text
   Category,CategoryCode,TerritoryNumber,Suffix,Type,Status,Number,Street,ApartmentNumber,City,State,PostalCode,Name,Phone,Notes,Latitude,Longitude
   ```
   - **Territory Matching:** Populates `Category`, `CategoryCode`, `TerritoryNumber` (numeric), and `Suffix` (or omits territory columns in Boundary-Match mode to match purely via `Latitude`/`Longitude` polygons).
   - **Coordinates:** `Latitude` and `Longitude` can be populated using either the built-in browser geocoder (for single-territory testing) or `geocode_nws_locations.py` (for bulk US geocoding with polygon verification).
   - **Status Values:** Uses NWS-supported `Available` and `DNC` values.
   - **Type Values:** Uses NWS-supported `House`, `Apartment`, `Business`, and `Other` values.
