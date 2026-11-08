# Client-side contiguous diffusion cartogram — go-cart-wasm prototype

Prototype only: no Vega-Lite chart was built here. The deliverable is a
verified cartogram GeoJSON plus this report, ready for the browser artifact
to render.

## Result (one line)

`go-cart-wasm@0.5.0` ran cleanly in Node on the 50 states: **12.10 s** wall
time, **mean absolute cartographic error 0.021%**, worst state **Alaska
+0.95%**, **107/107 adjacencies preserved**, Pearson r = 1.000000 between
area share and population share. One Alaska self-intersection was repaired
(area change −0.0000217%); the repaired file re-verifies identically.

## Library

- **go-cart-wasm 0.5.0**, MIT licence, zero dependencies.
  npm: `go-cart-wasm@0.5.0` (installed 2026-11-08 in `npm/`,
  `npm install go-cart-wasm@0.5.0`).
  Source: https://github.com/mthh/go-cart-wasm — JS/WASM port by Matthieu
  Viry (CNRS) of the reference implementation
  https://github.com/Flow-Based-Cartograms/go_cart (modified MIT licence).
- Algorithm: Gastner, Seguy & More (2018), "Fast flow-based algorithm for
  creating density-equalizing map projections", *PNAS* 115:E2156–E2164 —
  the same engine that powers go-cart.io.
- Installed files (`npm/node_modules/go-cart-wasm/dist/`): `cart.wasm`,
  `go-cart.cjs`, `go-cart.js`, `go-cart.mjs`. `package.json`:
  `"main": "./dist/go-cart.cjs"`, `"module": "./dist/go-cart.mjs"`.

## Exact API call

Per the library README (`npm/node_modules/go-cart-wasm/README.md`):

```js
import initGoCart from 'go-cart-wasm';

initGoCart({ locateFile: () => '<absolute path to cart.wasm>' })
  .then(GoCart => GoCart.makeCartogram(geojson, fieldName));
```

What this prototype ran (`run_gocart.mjs`, Node 24.22.1, main thread):

```js
import initGoCart from './npm/node_modules/go-cart-wasm/dist/go-cart.mjs';
const GoCart = await initGoCart({ locateFile: () => wasmPath }); // cart.wasm
const result = GoCart.makeCartogram(data, 'population');          // synchronous
```

`makeCartogram` returns a GeoJSON FeatureCollection. It preserves the
input properties and adds two per-feature properties: `cartogram_id`
and `area_error` (the program's own per-region relative area error).
Input must be a FeatureCollection of Polygon/MultiPolygon with the
weight field present as a property — here `population` (integer).

## Input data and CRS pipeline

```
states_5m.geojson  (2024 CBF 1:5m, EPSG:4269 lon/lat, 56 areas)
  |  build_input_5070.py (cartogram-build env: shapely 2.2.0, pyproj 3.8.0)
  v
states50_5070.geojson  (EPSG:5070 NAD83/Conus Albers, metres, equal-area)
  |  node run_gocart.mjs  ->  GoCart.makeCartogram(data, 'population')
  v
contiguous_states_2020_gocart_5070.geojson  (EPSG:5070, raw WASM output)
  |  inverse_project.py (EPSG:5070 -> EPSG:4269)
  v
../contiguous_states_2020_gocart.geojson  (EPSG:4269 lon/lat, DELIVERABLE)
```

- Populations: 2020 Census CD119 P1 resident populations from
  `../states.csv` (50 states, CA 39,538,223 → WY 576,851, total
  330,759,736).
- The EPSG:5070 input was generated independently by
  `build_input_5070.py` and checked against the earlier
  `../states50_albers.geojson`: **max coordinate difference 0 m**,
  same 50 states, same populations. The README's CRS rule is load-bearing:
  geographic coordinates (EPSG:4326/4269) give erroneous results, so the
  equal-area projection is not optional.
- The projected input and output are in metres; the lon/lat deliverable
  is EPSG:4269 (same datum as the source CBF files; the 4269-vs-4326
  difference is ~1–2 m and immaterial here).

## Alaska / Hawaii decision — option (a): 48 CONUS + insets

Alaska was scaled 0.35 about its centroid and moved to a bottom-left
inset; Hawaii was moved to an inset below CONUS (Albers-USA style, as
d3's `albersUsa` does and as the Demers layout did). Reasons:

1. In true EPSG:5070 Alaska sits ~1,500 km NW of CONUS and Hawaii
   ~3,800 km SW. Including them would stretch the flow grid over huge
   empty ocean, wasting grid resolution on CONUS.
2. Alaska is ~15% of US land area but 0.22% of population; under density
   equalisation it must shrink drastically anyway, so its true position
   carries no information the cartogram needs.
3. It matches the earlier C-run input exactly, so the WASM and C results
   are directly comparable.

Consequence, stated plainly: **AK/HI are NOT at their true geographic
coordinates in any file in this prototype.** In the lon/lat deliverable
their centroids are AK (−115.660, 18.180) and HI (−105.432, 20.096) —
below CONUS in the eastern Pacific. The lon/lat bbox is
lon −124.895…−65.366, lat 15.122…49.782. Render this file with an
**identity/fit projection, NOT Albers USA** — Albers USA would apply its
own inset transform on top of the baked-in one.

## Timing

Measured in Node 24.22.1, main thread, this VM:

| Step | Time |
|---|---|
| WASM module init | 0.03 s |
| `GoCart.makeCartogram` | **12.10 s** wall |
| Inverse projection + write (Python) | < 5 s |

No errors, no warnings from the library. Grid size / iteration count:
**not logged by the release build** — the DEBUG build (which prints grid
size, iterations, max area error, correction factor) requires rebuilding
with the Emscripten toolchain (`npm run build-debug`), which was not
done here. Wall time is the observable reported. For scale: the C
reference implementation took ~10 s for the same 50-state run.

## Cartographic error (independently re-measured, `verify_gocart.py`)

Measured on the projected output in EPSG:5070 (areas in m²), per state:
`(area share − population share) / population share`. Full 50-state table
in `error_table.csv`.

| Statistic | Value |
|---|---|
| Mean absolute relative error | **0.021%** |
| Worst state | **Alaska +0.95%** |
| All other 49 states | −0.002% each (uniform convergence residual) |
| Pearson r (area share vs pop share) | **1.000000** |
| CA/WY area ratio | 68.54 (population ratio 68.54) |
| Program's own `area_error` property | mean abs 0.021%, max 0.951% — agrees exactly with the re-measurement |

Top of the table (all states are within ±1%):

| State | Population | Area share | Pop share | Rel. error |
|---|---|---|---|---|
| California | 39,538,223 | 11.954% | 11.954% | −0.002% |
| Texas | 29,145,505 | 8.811% | 8.812% | −0.002% |
| Florida | 21,538,187 | 6.512% | 6.512% | −0.002% |
| New York | 20,201,249 | 6.107% | 6.107% | −0.002% |
| Alaska | 733,391 | 0.224% | 0.222% | **+0.951%** |
| Wyoming | 576,851 | 0.174% | 0.174% | −0.002% |

Comparison with the earlier C run (`../contiguous_states_2020.geojson`,
same input, same engine family): C mean abs error 0.054% (re-measured
here), worst Alaska +2.4%. The WASM run is slightly more accurate, and
the two agree closely — max difference in any state's area share is
0.003 percentage points (Alaska).

## Topology check (`verify_gocart.py`)

- All 50 states present; properties `STUSPS` / `NAME` / `population`
  preserved on every feature.
- Adjacencies (touches-or-intersects definition, same as
  `../verify_contiguous.py`): **107 true, 107 in cartogram, 107 preserved,
  0 lost, 0 gained.**
- Spot checks, all adjacent in both input and cartogram: CA–NV, CA–AZ,
  NV–AZ, NY–PA, NY–NJ, PA–NJ.
- One defect: **Alaska has a single self-intersection** in the raw WASM
  output, at EPSG:5070 (−1,892,420, −637,120) — the same defect class the
  C run found in its output. Repaired in the delivered lon/lat file with
  shapely `make_valid` (area change −0.0000217%); the raw projected
  output is left untouched as the verbatim library output. After repair:
  all 50 geometries valid, mean abs error still 0.021%, adjacencies
  still 107/107 (`repair_and_reverify.py`).
- Lon/lat round-trip: re-projecting the deliverable back to EPSG:5070
  reproduces the 0.021% mean abs error exactly (delta −0.0000 pp) —
  the inverse projection loses nothing.

## Visual check

`gocart_check.png` (rendered from the lon/lat deliverable, linear
lon/lat mapping, log-population colours): recognisably the US, correct
orientation (Maine top-right, Florida bottom-right, California left,
Texas large south-central). California, Texas, Florida and New York are
the largest shapes; Montana, Wyoming, Nevada and the Dakotas are small.
Alaska is the small pale inset at bottom-left, Hawaii the small islands
below CONUS. One observed edge effect: the northern-tier states show
spiky northward stretching along the Canadian border — the flow field
extends past the map edge, a known behaviour of diffusion cartograms,
not a data error.

## What the browser artifact must do

1. Load the library from jsDelivr as an ES module:
   `https://cdn.jsdelivr.net/npm/go-cart-wasm@0.5.0/+esm`, with
   `locateFile` returning
   `https://cdn.jsdelivr.net/npm/go-cart-wasm@0.5.0/dist/cart.wasm`.
   (In Node the equivalent is `import initGoCart from
   'go-cart-wasm/dist/go-cart.mjs'` with a local `locateFile` — proven
   in `run_gocart.mjs`.)
2. Run `makeCartogram` in a **Web Worker**, not the main thread: the
   computation takes ~12 s on this VM and would freeze the page. Show
   progress / a spinner while it runs (the release build emits no
   progress events, so the UI should say "computing…" without a fake
   percentage; a DEBUG build would be needed for real progress).
3. Feed it the EPSG:5070-projected 50-state GeoJSON with the
   `population` property — either ship the pre-projected
   `states50_5070.geojson` as an asset, or project client-side (proj4js
   with `EPSG:5070`). Do **not** feed it lon/lat.
4. Render the result with Vega-Lite `geoshape` and an **identity
   projection with `reflectY: true`** (latitude increases northward in
   the lon/lat file, so the y-flip is required or the map renders
   upside down — same as the C-run TopoJSON note). Do **not** use
   Albers USA: AK/HI insets are baked into the coordinates.
   Alternatively render the precomputed `contiguous_states_2020_gocart.geojson`
   directly (same rendering rule) and keep the live WASM run as an
   on-demand "recompute" path.
5. Disclose on the page: Alaska +0.95% is the only error above rounding;
   AK/HI are insets, not true positions; the computation takes ~12 s.

## Files

| File | What it is |
|---|---|
| `npm/` | npm scratch dir: `go-cart-wasm@0.5.0` install (`package.json`, `node_modules/`) |
| `build_input_5070.py` | 4269 → 5070 projection + AK/HI insets (reproduces `../build_contiguous.py`, verified 0 m difference) |
| `states50_5070.geojson` (3.6 MB) | Projected input to go-cart (EPSG:5070, 50 states) |
| `run_gocart.mjs` | Node runner: init WASM, `makeCartogram(data, 'population')`, timed |
| `contiguous_states_2020_gocart_5070.geojson` (3.5 MB) | Raw WASM output, EPSG:5070 (verbatim library output, AK unrepaired) |
| `inverse_project.py` | 5070 → 4269 inverse projection |
| `../contiguous_states_2020_gocart.geojson` (3.7 MB) | **Deliverable**: lon/lat (EPSG:4269), AK repaired, all 50 valid |
| `verify_gocart.py` | Independent error / validity / adjacency measurement |
| `repair_and_reverify.py` | `make_valid` repair of AK + re-verification of the deliverable |
| `error_table.csv` | Per-state area share vs pop share, all 50 states |
| `render_check.py`, `gocart_check.svg/.png` | Visual sanity render |
| `README.md` | This file |

Reproduce: `npm/` is already installed; then
`~/workspace/cartogram-build/bin/python build_input_5070.py`,
`node run_gocart.mjs`, `~/workspace/cartogram-build/bin/python inverse_project.py`,
`~/workspace/cartogram-build/bin/python verify_gocart.py`.
