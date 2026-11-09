# US Cartograms

Cartograms of the United States rendered with Vega-Lite — and, where
Vega-Lite proves inflexible, with its constitutive dependencies
(Vega, D3/TopoJSON, and go-cart-wasm).

The work starts from a simple fact, verified against the literature:
**no single cartogram algorithm can simultaneously guarantee zero
statistical error, perfect shape preservation, and intact topological
adjacencies** (Alam, Kobourov & Veeramoni 2015; Nusrat & Kobourov 2016).
So the rendering approach has to be chosen per dataset — and this repo
tests the three main paradigms side by side on the same authoritative
data, so the trade-offs are visible rather than asserted.

## The pages

All four are self-contained static pages in [`pages/`](pages/).
Open one directly in a browser, or serve the repo root and visit it:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/pages/zip-codes.html
```

Note: `pages/states-contiguous-cartogram.html` computes its cartogram
live in a Web Worker by fetching go-cart-wasm from the jsDelivr CDN,
so it needs an internet connection (the other two pages are fully
offline once loaded, apart from their Vega CDN scripts).

| Page | What it is |
|---|---|
| [`pages/zip-codes.html`](pages/zip-codes.html) | **US ZIP codes** — all 42,049 ZIP codes as 2 px squares under an Albers USA projection, coloured by the first digit of the ZIP code; hover shows ZIP, city, state, and county. Built from the Observable Vega-Lite API v6 notebook. |
| [`pages/states-cartogram-test.html`](pages/states-cartogram-test.html) | **US states cartogram test** — the 50 states by 2020 Census population, three ways side by side with linked hovering: undistorted Albers USA reference map, Demers squares (area ∝ population), and an equal-tile grid mosaic (population in colour). Infotips, readout panel, and a square area-to-value legend. |
| [`pages/states-contiguous-cartogram.html`](pages/states-contiguous-cartogram.html) | **Client-side contiguous diffusion cartogram** — the 50 states by population, computed live in the browser with go-cart-wasm (Gastner–Seguy–More flow-based method) in a Web Worker (~12 s), rendered with Vega-Lite geoshape beside the undistorted reference map. A verified precomputed reference is shown, clearly labelled, while the live run computes and as a toggleable comparison afterwards. |
| [`pages/districts-cartogram-test.html`](pages/districts-cartogram-test.html) | **Districts cartogram test** — the 435 voting congressional districts (119th Congress) by 2020 Census population, four ways with linked hovering, tile-grid mosaic first: squared-cost tile grid, contiguous diffusion, Demers squares, and the undistorted reference map. The 6 delegate districts are excluded. |

## Data

All boundaries and populations are U.S. Census Bureau material
(U.S. government public domain). Full sources, vintages, validation,
and caveats are in [`docs/census-readme.md`](docs/census-readme.md).

- **Boundaries:** 2024 Cartographic Boundary Files, 1:5,000,000
  (simplified, web-friendly) —
  [`cb_2024_us_state_5m.zip`](https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip)
  and
  [`cb_2024_us_cd119_5m.zip`](https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_5m.zip).
  119th Congress, seated January 2025 – December 2026; boundaries from
  state information provided by May 31, 2024. CRS: NAD83, EPSG:4269.
  The full-detail counterpart is TIGER/Line — deliberately not used
  here; it is far heavier than a browser needs.
- **Populations:** 2020 Census, 119th Congressional District Summary
  File (CD119), released 2024-12-05, Table P1 total population
  (resident populations, not apportionment populations — e.g. CA
  39,538,223 resident vs 39,576,757 apportionment). State values
  cross-checked against 2020 Apportionment Table A: 0 mismatches.
  Island Areas (not in CD119) come from the 2020 Island Areas Censuses.

| Set | n | Min | Max | Mean | Sum | Max/Min |
|---|---|---|---|---|---|---|
| States (50) | 50 | 576,851 (WY) | 39,538,223 (CA) | 6,615,195 | 330,759,736 | **68.5×** |
| Districts, voting (435) | 435 | 542,112 (MT-01) | 989,948 (DE at-large) | 760,367 | 330,759,736 | **1.83×** |

The 435 voting districts sum to exactly the 50-state total. Within-state
district ranges are tiny (max 27,372 in CA; 9 states exactly equal) —
districts are drawn to be near-equal by design, so a district
population cartogram is nearly uniform. That is a finding, not a bug,
and it drives the prioritisation below.

Files in [`data/`](data/): `states.csv` (56 state-equivalents),
`districts.csv` (441 = 435 voting + 6 delegate), `stats.json`,
`states_5m.geojson` / `.topojson`, `cd119_5m.geojson` / `.topojson`,
plus the derived layouts: `demers_states.csv`, `tilegrid_states.csv`,
`tilegrid_adjacency.json`, `layouts_verification.json`,
`contiguous_states_2020_gocart.geojson`, and the per-state
`error_table.csv` for the contiguous run — and for districts:
`demers_districts.csv`, `tilegrid_districts.csv`,
`tilegrid_districts_squared.csv`, `tilegrid_verification.json`,
`contiguous_districts_2020_gocart.geojson`, and the per-district
`districts_error_table.csv`.

## The three paradigms, and how to prioritise them

| Paradigm | Representation | Properties | Vega-Lite rendering |
|---|---|---|---|
| **Contiguous / diffusion** | Deformed geographic polygons | Near-zero cartographic error; preserves adjacencies and recognisable shapes; heavy polygons (~400 KB for a US map), seconds to compute | Precomputed GeoJSON, or — as here — computed client-side with go-cart-wasm and rendered as `geoshape` marks |
| **Demers** | Non-overlapping axis-aligned squares | Zero cartographic error by construction; uniform 1:1 aspect; sacrifices shapes and some adjacencies | `rect` marks from precomputed centres + side lengths |
| **Mosaic / tile grid** | Uniform square/hexagonal tiles | Low cartographic error; preserves recognisable shapes and ~half the adjacencies; ideal for discrete integer units (seats) | `rect` marks from precomputed grid coordinates |

**Prioritisation, in order** (see the full argument in the project
notes; the gates are, in order: metric type, unit semantics, dynamism,
size/skew, task):

1. **Is the metric additive?** Only totals that sum to an interpretable
   total may be encoded as area. Ratios and per-capita figures must
   not be — use equal tiles + colour, or area for the numerator and
   colour for the ratio (Duncan & Gastner 2024).
2. **What is one unit?** One region = one discrete thing (a seat, a
   district) → mosaic/hex first. One region = a continuous total
   (population, votes cast) → contiguous or Demers.
3. **One snapshot, or many metrics / time steps?** Single snapshot
   needing recognisability → contiguous first (best task performance
   in Nusrat et al.'s evaluation). Multiple weight vectors needing
   mental-map stability → Demers first (Nickel et al.'s TOP-W-St;
   Lemma 1 guarantees overlap-free interpolation between layouts
   sharing the same separation constraints).
4. **How many regions, and how skewed?** ~50 states: all viable.
   100–500 districts: mosaic/Demers stay cheap while diffusion
   polygons grow heavy. 1,000+: mosaic, usually after aggregating.
   Extreme skew (CA vs WY, 68.5×) strains contiguous shape
   preservation.
5. **What must the viewer do?** Locate a region or judge neighbours
   → contiguous first, Demers second with leader lines for lost
   adjacencies. Summarise the big picture → Dorling/Demers first.
   Read exact values → none of them alone; pair with an
   area-to-value legend and infotips with exact numbers.

Applied here: **states first** (68.5× skew gives every paradigm
visible work), **districts by population alone are a weak test**
(1.83×, near-equal by design) — for districts the interesting weight
is a genuinely varying one such as votes cast, turnout, or margin,
or else one tile per seat.

A Vega-Lite constraint applies to all three: **none can be computed
inside a Vega-Lite spec** (no LP solver, diffusion, or force layout),
so all are precompute-then-render — except the contiguous page here,
which precomputes in the browser itself via go-cart-wasm in a Web
Worker, which is the point of that page.

## Verification numbers

### ZIP codes (`pages/zip-codes.html`)

- 42,049 ZIP codes from `zipcodes.csv` (vega-datasets), plotted as
  2 px squares, Albers USA, coloured by first digit of ZIP.
- Verified headlessly with Vega-Lite 6.4.0 / Vega 6.2.0: all 42,049
  rows loaded; SVG render produced 42,085 paths using all 10 digit
  colours. Field check: the real CSV header is `zip_code` (with
  underscore) — the Observable notebook cell's `zipcode` would not
  have matched the data.

### States test (`pages/states-cartogram-test.html`)

- All three views render exactly 50 state marks; hovering CA, WY, or
  TX highlights that state at full opacity and dims the other 49 in
  **all** three views; mouseout clears everywhere; the readout shows
  correct figures (CA 39,538,223, 11.95%, 403,673 km²; TX 29,145,505,
  676,657 km²). No page errors (jsdom harness, pinned Vega 6.2.0 /
  Vega-Lite 6.4.0 / vega-embed 7.0.2).
- **Demers:** iterative overlap-removal baseline (FRC-style), **not**
  the Nickel TOP-W-St LP — labelled as such on the page, so no Lemma 1
  guarantee applies. Zero overlaps, zero gap violations; mean
  displacement from centroid 83.5 km, median 45.5 km, max 482.5 km
  (NY, pushed north by the PA/NJ/CT/MA cluster); ordering preserved
  98.8% east–west, 95.7% north–south; cartographic error ≈ 0 by
  construction (side² ∝ population). See
  [`docs/layouts-readme.md`](docs/layouts-readme.md).
- **Tile grid:** amCharts 12×9 grid, 50 states, 50 unique cells.
  Preserves 53/107 (49.5%) true adjacencies as orthogonal neighbours,
  with 19 false adjacencies. See
  [`docs/layouts-readme.md`](docs/layouts-readme.md).

### Contiguous cartogram (`pages/states-contiguous-cartogram.html`)

- **go-cart-wasm 0.5.0** (Gastner–Seguy–More 2018 flow-based method),
  run in Node on the 50 states: WASM init 0.03 s, `makeCartogram`
  **12.10 s** wall time, no errors. Mean absolute cartographic error
  **0.021%**, worst state Alaska **+0.95%** (all other states
  −0.002%), Pearson r = 1.000000, CA/WY area ratio 68.54 (= population
  ratio), **107/107 adjacencies preserved**. The browser page
  rehearsed the same pipeline in Node on its exact shipped input:
  12.19 s, same 0.021% error. Full report:
  [`docs/contiguous-prototype-readme.md`](docs/contiguous-prototype-readme.md).
- **CRS pipeline (load-bearing):** input to go-cart must be in a
  projected equal-area CRS — EPSG:5070 (NAD83 / Conus Albers) — never
  lon/lat, which gives erroneous results. Pipeline: lon/lat →
  EPSG:5070 → go-cart → inverse-project to lon/lat. The inverse
  Albers in the page was checked against pyproj on 200 vertices:
  max error 5.7e-14 degrees.
- **AK/HI are insets, not true positions:** 48 CONUS states computed,
  Alaska scaled 0.35 about its centroid to a bottom-left inset,
  Hawaii moved below CONUS. In the delivered GeoJSON their centroids
  are AK (−115.660, 18.180), HI (−105.432, 20.096). Render with an
  identity/fit projection, `reflectY: true` — **not** Albers USA,
  which would re-apply its own inset transform.
- **One defect, repaired and disclosed:** the raw WASM output has a
  single Alaska self-intersection (EPSG:5070 −1,892,420, −637,120),
  repaired with shapely `make_valid` (area change −0.0000217%);
  re-verification after repair is unchanged.
- **Edge effect:** northern-tier states show spiky northward
  stretching along the Canadian border — flow-field behaviour at the
  map edge, not a data error.
- Live end-to-end compute was **not** observed in the audit sandbox
  (its egress lockdown blocks jsDelivr); the worker there loaded and
  failed only at the CDN import, with a plain, accurate failure
  message. On a normal connection jsDelivr is reachable — the
  `+esm` module was fetched and its `locateFile` contract confirmed.

### Districts test (`pages/districts-cartogram-test.html`)

- **435 voting districts** (119th Congress), 2020 Census P1:
  MT-01 542,112 to DE at-large 989,948, mean 760,367, ratio
  **1.83×** — near-equal by design, so population-area at this scale
  is almost uniform; a differentiated districts cartogram would need
  a genuinely varying weight (votes cast, turnout, margin). The 6
  delegate districts are excluded (DC 689,545; AS 49,710; GU 153,836;
  MP 47,329; PR 3,285,874; VI 87,146). Full report:
  [`docs/districts-readme.md`](docs/districts-readme.md).
- **Tile-grid mosaic (lead view, squared-cost):** Hungarian
  point-set matching onto a 35×22 grid (132 km cells), 435 unique
  tiles. Max displacement 1,338 km (NY-25), zero districts over
  2,000 km, adjacency preserved 431/1,134 (**38.0%**). The
  linear-cost variant is worse (max 3,247.9 km, NY-01 by Montana;
  adjacency 215/1,134, 19.0%) and is not the main view.
- **Contiguous diffusion:** go-cart-wasm 0.5.0, EPSG:5070 pipeline,
  `makeCartogram` **22.92 s**. Raw solver: mean absolute error
  **0.018%**, worst TX-23 +0.92%, r = 0.999916, 1,134/1,134
  adjacencies. Delivered file after repair: mean **0.084%**, worst
  AZ-02 +6.33% (repair artefact, not solver error), r = 0.997132.
  Repair cost at 435 regions: 99 self-intersecting geometries in the
  raw output, repaired by nonzero-winding face selection (plain
  `make_valid` was tried and rejected — it would have degraded mean
  error to 0.155%). Rendered identity projection, `reflectY: true`,
  not Albers USA; AK/HI are insets.
- **Demers:** iterative overlap-removal baseline (FRC-style), **not**
  TOP-W-St LP. Zero true overlaps, zero gap violations; sides
  17.38–23.49 units, area ratio 1.826× = population ratio; mean
  displacement 184.7 km, median 142.9 km, max 881.4 km (NJ-11);
  ordering preserved 96.3% east–west, 92.3% north–south.
- All four views render 435 district marks each; hovering one
  district highlights it in all four views (verified headlessly,
  pinned Vega 6.2.0 / Vega-Lite 6.4.0).

## Literature

Cited only — the papers themselves are **not** included in this repo.

- Alam, M. J., Kobourov, S. G., & Veeramoni, S. (2015).
  Quantitative Measures for Cartogram Generation Techniques.
  *Computer Graphics Forum* 34(3), 351–360 (EuroVis 2015).
  doi:10.1111/cgf.12647 — the impossibility result (no algorithm
  satisfies all criteria), the 400 KB diffusion vs 8 KB rectangular
  US maps, 25–50 s diffusion on a 1024×1024 grid, 1–3 s for
  RECT/COMBT to negligible error.
- Nusrat, S., & Kobourov, S. (2016). The State of the Art in
  Cartograms. *Computer Graphics Forum* 35(3) (EuroVis STAR).
  doi:10.1111/cgf.12932 — the statistical / topological /
  geographical accuracy framework; Dorling for big-picture
  summarisation; mosaic for integer seats (Telegraph hex map);
  always show the cartogram alongside the undistorted map, with
  linked brushing.
- Nickel, S., Sondag, M., Meulemans, W., Kobourov, S., Peltonen, J.,
  & Nöllenburg, M. (2022). Multicriteria Optimization for Dynamic
  Demers Cartograms. *IEEE Transactions on Visualization and Computer
  Graphics* 28(6), 2376–2385 — Demers LP formulation, H/V
  separation DAGs, TOP-W-St recommended default, Lemma 1
  overlap-free interpolation, leader lines for lost adjacencies
  (K₄, ≤ 2 bends).
- Duncan, I. K., & Gastner, M. T. (2024). Comparative evaluation of
  the web-based contiguous cartogram generation tool go-cart.io.
  *PLOS ONE* 19(5): e0298192 — go-cart.io's fast flow-based
  generation, additive-only rule, linked brushing / infotips /
  area-to-value legend / 1-second morph, and the usability
  recommendations (CSV-only as studied; Excel/JSON upload,
  column auto-detection, full-column paste, tutorial overlay are
  recommendations, not existing capability).
- Gastner, M. T., Seguy, V., & More, P. (2018). Fast flow-based
  algorithm for creating density-equalizing map projections.
  *Proceedings of the National Academy of Sciences USA* 115,
  E2156–E2164 — the flow-based engine behind go-cart.io and
  go-cart-wasm; 1.5 s for a US Electoral College cartogram on a
  12-core workstation.

## Reproducing the layouts and the prototype

Requires Python 3 with `shapely` / `pyproj` (the GIS env used was
`~/workspace/.venvs/gis` / `~/workspace/cartogram-build`), Node 24,
and `npx` for TopoJSON. See the per-folder docs for exact commands.

```sh
# 1. Fetch + build the Census dataset (recreates data/states.csv etc.)
python3 scripts/build_dataset.py
python3 scripts/build_csvs.py

# 2. Demers + tile-grid layouts
python3 scripts/compute_layouts.py

# 3. Contiguous cartogram, go-cart-wasm prototype
#    (install go-cart-wasm@0.5.0 first: npm install go-cart-wasm@0.5.0)
python3 scripts/contiguous-prototype/build_input_5070.py
node scripts/contiguous-prototype/run_gocart.mjs
python3 scripts/contiguous-prototype/inverse_project.py
python3 scripts/contiguous-prototype/verify_gocart.py
```

`scripts/build_contiguous.py` and `scripts/verify_contiguous.py`
reproduce the **earlier C-run** contiguous cartogram (see "Excluded"
below); they need the `go_cart` C binary built from
<https://github.com/Flow-Based-Cartograms/go_cart>.

## What is deliberately NOT in this repo

- **Literature PDFs** — copyrighted papers; cited above, not shipped.
- **The rejected 2014 cartogram** (`contiguous_states_2014est.*`) —
  a 2014 population-estimate file from subyfly/topojson that failed
  verification (mean absolute relative area error 50%, Montana +406%,
  Alaska +352%, California under-sized) and is the wrong vintage.
  Kept out; its rejection is documented in
  [`docs/contiguous-note.md`](docs/contiguous-note.md).
- **The earlier C-run contiguous cartogram**
  (`contiguous_states_2020.geojson`, 3.6 MB, and its TopoJSON
  `contiguous_states_2020_q1e6.topojson`, 604 KB) — verified in its
  own right (mean error 0.054%, Alaska +2.4%, 107/107 adjacencies),
  but **superseded by the go-cart-wasm run** (0.021%, Alaska +0.95%),
  which is the file shipped here as
  `data/contiguous_states_2020_gocart.geojson`. The C-run scripts
  are kept in `scripts/` for reproducibility; the C-run output files
  are not.
- **`raw/` (52 MB)** — the source Census zips, per-district API
  responses, and validation files. Excluded via `.gitignore`; re-fetch
  from the Census URLs in [`docs/census-readme.md`](docs/census-readme.md)
  and re-run `scripts/build_dataset.py`. Likewise `node_modules/`,
  `*.zip`, `__pycache__/`, `.DS_Store` are git-ignored.

## Licence

MIT — see [`LICENSE`](LICENSE). Copyright (c) 2026 Gavin N. Morgan.
Census data in this repo is U.S. government public-domain material.
go-cart-wasm is MIT licensed; the underlying Gastner–Seguy–More
flow-based code is under a modified MIT licence. Vega, Vega-Lite,
D3, and TopoJSON are used via CDN in the pages under their own
licences.
