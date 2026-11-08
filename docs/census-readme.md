# US cartogram test — Census dataset (states + 119th congressional districts)

Vega-Lite-ready boundaries + populations, audited 2026-11-08. No chart built yet —
dataset preparation only.

## Files

| File | Size | Contents |
|---|---|---|
| `states.csv` | 5.2 KB | 56 state-equivalents: geoid, name, population, voting seats, land/water area, centroid |
| `districts.csv` | 49 KB | 441 districts: geoid, state, CD, delegate/at-large flags, population, ideal population, area, centroid |
| `states_5m.geojson` | 2.3 MB | 56 features, NAD83 (EPSG:4269), 5-decimal precision |
| `cd119_5m.geojson` | 4.4 MB | 441 features, same CRS/precision |
| `states_5m.topojson` | 1.3 MB | Same 56 features, shared arcs (`topojson-server`, default quantisation) |
| `cd119_5m.topojson` | 2.3 MB | Same 441 features |
| `cd_pop_cd119.json` | 7.4 KB | District GEOID → CD119 P1 population (441 entries) |
| `stats.json` | 1.8 KB | Min/max/mean/median/SD/sums for states and districts |
| `build_dataset.py`, `build_csvs.py` | — | Reproducible fetch + build scripts |
| `raw/` | 52 MB | Source zips, per-district API responses, validation files (see below) |

## Sources (all U.S. Census Bureau)

**Boundaries — 2024 Cartographic Boundary Files, 1:5,000,000 (simplified, web-friendly)**
- States: https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip
  (1.1 MB, md5 `cbd5db9f4474fc7c498090ae2a303870`, files dated 2025-04-02)
- 119th Congressional Districts: https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_5m.zip
  (2.1 MB, md5 `b6c27c4e8dd95089eb4d5a72860e4851`, files dated 2025-04-02)
- CRS: NAD83, EPSG:4269. Fields kept: GEOID, NAME/NAMELSAD, STATEFP, CD119FP,
  STUSPS, LSAD, CDSESSN (=119), ALAND, AWATER.
- Confirmed from the file's own ISO metadata abstract: the 119th Congress is seated
  **January 2025 – December 2026**; boundaries are based on information provided by
  the states **by May 31, 2024**. DC, PR and the four Island Areas each have a single
  non-voting delegate district. The metadata mentions a `ZZ` code for areas of CT/IL/NH
  with no CD defined — **no `ZZ` record actually occurs in this 5m file**.

**Populations — 2020 Census, Table P1 Total Population**
- Districts and states: **2020 Census 119th Congressional District Summary File
  (CD119)**, released **2024-12-05** — a retabulation of the 2020 DHC file to 119th
  boundaries. Table P1, via the data.census.gov table API
  (`DECENNIALCD1192020.P1`, dataset `2020/dec/cd119`).
  - Note: direct `api.census.gov` calls now 302-redirect to a missing-key page
    (observed 2026-11-08); the `data.census.gov/api/access/data/table` proxy works
    keyless. Parallel fetching was throttled (empty responses); sequential fetch with
    retries recovered all 441, the last 4 (CA-23, PA-16, TX-32, WV-01) individually.
  - State populations use the same CD119 P1 table at summary level 040 (52 rows:
    50 states + DC + PR). Cross-checked against **2020 Apportionment Table A,
    resident population** (`raw/apportionment-2020-tableA.pdf`): **0 mismatches**
    across all 51 rows parsed (50 states + DC). These are *resident* populations,
    not apportionment populations (which add overseas personnel — e.g. CA 39,538,223
    resident vs 39,576,757 apportionment; WY 576,851 vs 577,719).
- Island Areas (AS/GU/MP/VI — not in CD119/DHC): **2020 Island Areas Censuses**,
  Census Bureau release 2021-10-28
  (https://www.census.gov/library/stories/2021/10/first-2020-census-united-states-island-areas-data-released-today.html):
  AS 49,710; GU 153,836; CNMI 47,329; VI 87,146; total 338,021.

**Validation sample — Alabama.** The CD119 FTP geo file (`algeo2020.cd19`,
in `raw/cd119_test/al2020.cd19.zip`, 42 MB) carries a `POP100` field per geography.
Its 7 CD values match the API P1 values exactly (717,754 ×6, 717,755 ×1).

## Record counts (actual, not assumed)

- **States: 56** — 50 states + DC + PR + AS + GU + MP + VI.
- **Districts: 441 = 435 voting + 6 delegate** (CD119FP `98`: DC, PR, AS, GU, MP, VI).
  At-large voting districts (`00`): 6 (AK, DE, ND, SD, VT, WY). No `ZZ` records.
  Voting seats sum to 435. CA 52, TX 38, FL 28, NY 26; MT has 2.

## Population ranges (2020 Census, P1 resident)

| Set | n | Min | Max | Mean | Median | SD | Sum | Max/Min |
|---|---|---|---|---|---|---|---|---|
| States (50) | 50 | 576,851 (WY) | 39,538,223 (CA) | 6,615,195 | 4,581,797 | 7,361,406 | 330,759,736 | **68.5×** |
| States (56, +DC/PR/IA) | 56 | 47,329 (CNMI) | 39,538,223 (CA) | 5,983,450 | 3,782,649 | 7,201,153 | 335,073,176 | 835× |
| Districts, voting (435) | 435 | 542,112 (MT-01) | 989,948 (DE at-large) | 760,367 | 766,987 | 37,877 | 330,759,736 | **1.83×** |
| Districts, all (441) | 441 | 47,329 (CNMI del.) | 3,285,874 (PR) | 759,803 | 766,987 | 141,595 | 335,073,176 | 69.4× |

Reconciliation check: the 435 voting districts sum to **exactly** the 50-state
resident total (330,759,736), and the 441 sum to exactly the 56-area total
(335,073,176). Within-state district ranges are tiny — max 27,372 (CA), and
**9 states have within-state range exactly 0** (perfectly equal districts, e.g.
Alabama: all 7 at 717,754/717,755). Largest deviation from the state ideal
(state pop ÷ seats) is CA-22, +21,897.

## CSV columns

- `states.csv`: geoid, state_fp, state (STUSPS), name, population,
  population_source, voting_seats, districts_total, aland_sqkm, awater_sqkm,
  centroid_lon, centroid_lat.
- `districts.csv`: geoid (STATEFP+CD119FP), state_fp, state, cd, name (NAMELSAD),
  is_delegate, is_at_large, population, population_ideal (= state pop ÷ voting
  seats; blank for delegates), population_source, aland_sqkm, awater_sqkm,
  centroid_lon, centroid_lat.
- `population_ideal` is a computed check, not a Census figure; the `population`
  column is the authoritative CD119 P1 value (Island Areas excepted, see above).

## Methods & caveats

- **Centroids are geometric centroids of the simplified 5m polygons**, computed in
  EPSG:5070 (NAD83 / Conus Albers, equal-area) and inverse-projected to lon/lat
  (EPSG:4269). Projecting first avoids the Alaska dateline error (raw lon/lat
  averaging would put Alaska near lon 0); AK centroid is (−152.43, 63.76), HI
  (−156.33, 20.26). These are *not* the Census internal points (INTPTLAT/LONG),
  which are guaranteed on-land points and differ (e.g. AL-01: centroid
  31.09, −86.68 vs Census internal point 31.03, −86.80).
- **Land area** is `ALAND` from the shapefile (m² → km² in the CSVs).
- **DHC disclosure avoidance:** CD119 is a retabulation of DHC data, which uses
  differential-privacy noise; district totals are nevertheless the published P1
  values and reconcile exactly to state totals (above).
- **5m simplification** is for small-scale thematic mapping; do not use these
  geometries for legal/precise boundary work — use TIGER/Line for that.
- TopoJSON was built with `topojson-server` (npx); GeoJSON via `ogr2ogr`
  (`-lco COORDINATE_PRECISION=5`, selected fields only).

## Recommendation — test on states first

**States (50) are the clear first test.** Population skew is 68.5× (CA vs WY),
so every paradigm has something visible to do: contiguous diffusion must grow
California ~68× relative to Wyoming; Demers squares vary 68× in area (~8.3× in
side length); a mosaic of equal tiles would discard the skew entirely, which is
wrong for a continuous total. States also keep N small (50), shapes recognisable,
and the file tiny (TopoJSON 1.3 MB).

**Districts by population alone are a weak test, by design.** The 435 voting
districts are drawn to be near-equal *within* each state (max within-state range
27,372 on ~760k; 9 states exactly equal), so a population cartogram of districts
is nearly uniform — the only real variation is *across* states (1.83×, driven by
state size ÷ seats: DE at-large 989,948 vs MT-01 542,112). Scaling 435 districts
by population mostly reproduces an equal-tile mosaic, and it tests the layout
machinery, not the weighting. Under the earlier prioritisation this implies:
- **States → contiguous diffusion** (single recognisable snapshot, high skew) or
  **Demers TOP-W-St** (if you will switch metrics/cycles and need stable animation).
- **Districts → mosaic/hex, one tile per district** — because the unit *is* the
  seat — or keep districts for the *second* test with a genuinely varying weight
  (votes cast, turnout, margin), where population is the wrong weight and the
  cartogram actually has work to do. Do not test districts with population as if
  it were a discriminating weight; the near-equality is the finding, not a bug.
