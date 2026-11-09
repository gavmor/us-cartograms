# Contiguous diffusion cartogram — 435 voting US congressional districts (119th Congress)

`go-cart-wasm@0.5.0` (Gastner, Seguy & More 2018 flow-based algorithm, same
engine as go-cart.io) run in Node on the 435 voting districts. No Vega
chart was built here — the deliverable is a verified cartogram GeoJSON
plus this report, ready for the browser artifact to render.

## Result (one line)

Raw WASM output: **mean absolute cartographic error 0.018%**, worst
district **TX-23 +0.92%**, **1134/1134 adjacencies preserved** (0 lost),
Pearson r = 0.999916. The delivered file (99 self-intersections repaired)
re-measures at **mean abs error 0.084%**, worst **AZ-02 +6.33%** (a
repair artifact, see below), Pearson r = 0.997132, **1134/1134
adjacencies preserved**, 0 lost, 2 gained, all 435 geometries valid.

## Inputs

- `../districts.csv` — 2020 Census CD119 P1 populations; only the 435
  with `is_delegate=0` (voting). Excluded delegates: DC 689545, AS 49710,
  GU 153836, MP 47329, PR 3285874, VI 87146. Voting populations: min
  542,112 (MT-01, geoid 3001), max 989,948 (DE at-large, geoid 1000),
  mean 760,367, total **330,759,736**.
- `../cd119_5m.geojson` — 2024 Cartographic Boundary Files 1:5,000,000,
  119th Congress, EPSG:4269 (441 features; the 6 delegates dropped on
  `GEOID` join — all 435 voting GEOIDs matched, none missing).
- `districts_5070.geojson` — projected input, EPSG:5070 NAD83/Conus
  Albers (metres, equal-area). Reprojection is load-bearing: geographic
  coordinates give erroneous go-cart results, so lon/lat is never fed
  to the solver.

## Alaska / Hawaii decision — option (a): 48 CONUS states' districts + insets

Same decision as the states prototype. The 48 CONUS states' districts
keep true EPSG:5070 positions. Alaska at-large (geoid 0200) was scaled
**0.35 about its centroid** and moved so its centroid lands at
`(xmin + 350,000, ymin − 550,000)` in EPSG:5070, where
xmin/ymin are the CONUS-district bbox minima
(bbox x −2,356,114..2,258,200, y 268,976..3,172,568). Hawaii's 2
districts (1501, 1502) were translated together so their **combined**
centroid lands at `(xmin + 1,500,000, ymin − 550,000)`. In EPSG:5070
the inset centroids are AK (−2,006,114, −281,024) and HI combined
(−856,114, −281,024).

Consequence, stated plainly: **AK/HI are NOT at their true geographic
coordinates in any file here.** In the lon/lat deliverable their
centroids are:

| District | Centroid lon/lat |
|---|---|
| AK at-large (0200) | (−115.979, 17.771) |
| HI-01 (1501) | (−106.502, 22.086) |
| HI-02 (1502) | (−105.744, 20.667) |

Lon/lat bbox: lon −124.945..−64.122, lat 14.643..50.284. Render with an
**identity/fit projection, NOT Albers USA** — Albers USA would apply its
own inset transform on top of the baked-in one.

## Timing (Node v24.22.1, main thread, this VM)

| Step | Time |
|---|---|
| WASM module init | 0.04 s |
| `GoCart.makeCartogram(data, 'population')` | **22.92 s** wall |
| Inverse projection + write (Python) | < 5 s |

No errors, no warnings from the library. 435 features in, 435 out.
For scale: the 50-state run took 12.10 s; the districts run is ~1.9×
slower for 8.7× the regions.

## Cartographic error

Measured on the projected output in EPSG:5070 (areas in m²), per
district: `(area share − population share) / population share`.
Full 435-district table in `error_table.csv` (delivered geometry;
includes the program's own `area_error` and the repair area change
per district).

| Statistic | Raw WASM output | Delivered (repaired) |
|---|---|---|
| Mean absolute relative error | **0.018%** | **0.084%** |
| Worst district | TX-23 +0.92% | AZ-02 +6.33% (repair artifact) |
| 2nd / 3rd worst | AK-00 +0.53%, IL-15 +0.46% | WI-01 +2.44%, AZ-04 −1.66% |
| Pearson r (area share vs pop share) | 0.999916 | 0.997132 |
| DE-at-large / MT-01 area ratio | 1.826 (pop ratio 1.826) | 1.826 |
| Largest / smallest cartogram area ratio | 1.826 | 1.826 |
| Program's own `area_error` | mean abs 0.018%, max 0.918% — agrees with the re-measurement | — |

All 435 raw errors are within ±1%; the only districts above 0.5% in
the raw output are TX-23 (+0.92%) and AK-00 (+0.53%).

## Repairs — 99 self-intersections (read this before quoting the error)

The raw WASM output has **99 invalid geometries**, each a single
self-intersection pinch (same defect class the states run found once,
in Alaska — far more common here at 435 regions / 1:5m district
detail). Plain `shapely.make_valid` was tried first and **rejected on
measured grounds**: it keeps every face of the folded ring, inflating
areas by mean 0.39% / max +12.75% (AZ-02) and degrading mean abs error
to 0.155%.

Repair used instead — **nonzero-winding selection over `make_valid`
faces**: `make_valid` splits the folded ring into the faces of its
planar subdivision; a face is kept iff the original ring winds around
it with the same sign as the ring's own orientation (winding number
+1 after sign normalisation). That is exactly the nonzero fill rule a
renderer applies to the raw ring, so the repaired shape is what the
raw output already draws — only the formal validity and the area
accounting change. A self-intersecting ring has no unique "intended"
area (its signed/shoelace area counts negatively-wound faces
negatively, which no set of points can represent), so some area
movement is unavoidable; this rule minimises it. Alternatives measured
on the same 99 districts: plain `make_valid` mean abs error 0.155%,
largest-face-only 0.565%, nonzero-winding **0.084%**.

Repair cost (EPSG:5070 areas): 99 districts repaired, area change max
abs **+6.38% (AZ-02)**, mean abs 0.22%, area-weighted total +0.11%.
Worst five: AZ-02 +6.38% (5 faces, 2 dropped), WI-01 +2.47%,
AZ-04 −1.63%, NJ-12 +1.33%, NY-15 +1.26%. The delivered AZ-02 error
(+6.33%) is therefore a repair artifact, not a solver error — the
solver's own raw AZ-02 error was −0.02% (program `area_error` −0.015%).
The raw projected output is left untouched as the verbatim library
output; the repair lives in `contiguous_districts_2020_gocart_5070_repaired.geojson`
and the lon/lat deliverable.

After repair: **all 435 geometries valid** in the lon/lat deliverable,
and still valid after re-projection to EPSG:5070 (0 invalid).
Re-projecting the deliverable back to EPSG:5070 reproduces the 0.084%
mean abs error exactly (delta 0.0000 pp) — the inverse projection
loses nothing.

## Topology check

Adjacencies (touches-or-intersects definition, same as the states
prototype), measured on the delivered file re-projected to EPSG:5070
vs the projected input:

| | Count |
|---|---|
| True adjacencies (input) | 1134 |
| Cartogram adjacencies | 1136 |
| Preserved | **1134** |
| Lost | **0** |
| Gained | 2 — AZ-04/AZ-07 (0404/0407), WA-06/WA-07 (5306/5307) |

(The raw output had a third gained pair, NJ-12/PA-02 (3412/4202),
which disappeared when NJ-12's fold was repaired — it was a product
of the self-intersection, not the diffusion.)

Spot checks, all adjacent in both input and cartogram: CA-01/CA-02,
NY-01/NY-02, TX-01/TX-04 (within-state); CA-01/OR-02, TX-01/AR-04
(state-border pairs). Negative check: NY-01/NJ-03 not adjacent in
either. (Note: TX-01/TX-02 and TX-01/OK-02 are *not* adjacent in the
input — TX-02 is the Houston-area district and TX-01 borders AR-04,
not OK-02 — so they were not used as spot checks.)

All 435 districts present; properties `geoid` / `state` / `cd` /
`name` / `is_at_large` / `population` preserved on every feature,
plus the program-added `cartogram_id` and `area_error`.

## What the Vega artifact must do

1. Load the library from jsDelivr as an ES module:
   `https://cdn.jsdelivr.net/npm/go-cart-wasm@0.5.0/+esm`, with
   `locateFile` returning
   `https://cdn.jsdelivr.net/npm/go-cart-wasm@0.5.0/dist/cart.wasm`.
   (In Node the equivalent is `import initGoCart from
   'go-cart-wasm/dist/go-cart.mjs'` with a local `locateFile` — proven
   in `run_gocart.mjs`.)
2. Run `makeCartogram` in a **Web Worker**, not the main thread: the
   computation takes ~23 s on this VM and would freeze the page. Show
   progress / a spinner while it runs (the release build emits no
   progress events, so the UI should say "computing…" without a fake
   percentage; a DEBUG build would be needed for real progress).
3. Feed it the EPSG:5070-projected 435-district GeoJSON with the
   `population` property — either ship the pre-projected
   `districts_5070.geojson` as an asset, or project client-side (proj4js
   with `EPSG:5070`, applying the AK/HI inset transforms first). Do
   **not** feed it lon/lat.
4. Render the result with Vega-Lite `geoshape` and an **identity
   projection with `reflectY: true`** (latitude increases northward in
   the lon/lat file, so the y-flip is required or the map renders
   upside down). Do **not** use Albers USA: AK/HI insets are baked into
   the coordinates. Alternatively render the precomputed
   `contiguous_districts_2020_gocart.geojson` directly (same rendering
   rule) and keep the live WASM run as an on-demand "recompute" path.
5. Disclose on the page: the delivered file's mean abs error is 0.084%
   (raw solver error 0.018%); AZ-02 at +6.33% is a validity-repair
   artifact, not a solver error; AK/HI are insets, not true positions;
   the computation takes ~23 s.

## Files

| File | What it is |
|---|---|
| `build_input_5070.py` | 4269 → 5070 projection + AK/HI insets |
| `districts_5070.geojson` (7.3 MB) | Projected input to go-cart (EPSG:5070, 435 districts) |
| `run_gocart.mjs` | Node runner: init WASM, `makeCartogram(data, 'population')`, timed |
| `contiguous_districts_2020_gocart_5070.geojson` (6.9 MB) | Raw WASM output, EPSG:5070 (verbatim library output, 99 invalid) |
| `contiguous_districts_2020_gocart_5070_repaired.geojson` | Repaired projected output, EPSG:5070 (nonzero-winding rule) |
| `inverse_project.py` | 5070 → 4269 inverse projection (reference; the repair script performs it on the repaired file) |
| `contiguous_districts_2020_gocart.geojson` (7.3 MB) | **Deliverable**: lon/lat (EPSG:4269), 99 repaired, all 435 valid |
| `verify_gocart.py` | Independent error / validity / adjacency measurement (raw output) |
| `repair_and_reverify.py` | Nonzero-winding repair + re-verification of the deliverable |
| `error_table.csv` | Per-district area share vs pop share, all 435 (delivered geometry) |
| `contiguous_verification.json` | Machine-readable verification summary (delivered + raw) |
| `contiguous_notes.md` | This file |

Reproduce: `~/workspace/.venvs/gis/bin/python build_input_5070.py`,
`node run_gocart.mjs`,
`~/workspace/.venvs/gis/bin/python verify_gocart.py`,
`~/workspace/.venvs/gis/bin/python repair_and_reverify.py`.
The go-cart-wasm install is reused from
`../contiguous-prototype/npm/node_modules/go-cart-wasm/` (0.5.0);
nothing was reinstalled.
