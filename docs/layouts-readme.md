# US-states population cartogram layouts — test data (50 states)

Layouts only — **no Vega-Lite chart built**. Inputs: `states.csv`
(2020 Census CD119 P1 resident populations) and `states_5m.geojson`
(2024 Cartographic Boundary Files, 1:5,000,000). **50 states only.**
Excluded from all layouts: DC, Puerto Rico, American Samoa, Guam,
CNMI, US Virgin Islands (they are in `states.csv` but are not states).

Population range: CA 39,538,223 … WY 576,851; ratio 68.5×; mean
6,615,195; total 330,759,736.

## Files

| File | Contents |
|---|---|
| `demers_states.csv` | Demers squares: state, abbr, name, population, side (view units + km equiv.), x/y, centroid x/y, displacement, inset flag |
| `tilegrid_states.csv` | Tile grid: state, abbr, name, population, grid_col, grid_row |
| `contiguous_note.md` | Why there is NO contiguous layout in this folder (candidate found and rejected — read it) |
| `contiguous_states_2014est.topojson` / `.geojson` | Rejected 2014 candidate, kept as evidence only — do not use as the test layout |
| `layouts_verification.json` | Machine-readable verification numbers for the Demers layout |
| `tilegrid_adjacency.json` | Tile-grid adjacency check (true vs grid neighbours) |
| `demers_check.png` | Visual check: Demers squares (blue) vs Albers centroids (red +) |
| `compute_layouts.py` | Reproducible solver + tile-grid writer (system python3: pyproj/numpy/scipy) |

## 1. Demers squares — `demers_states.csv`

**Method, honestly labelled: iterative overlap-removal (FRC-style
baseline). This is NOT the Nickel et al. TOP-W-St linear program.**
No LP was solved. Squares start at their Albers centroids with side
`c·√population`, and overlaps are resolved by iterative pairwise
separation along the axis of least penetration, with a weak anchor pull
toward the starting position in phase 1 only. H/V separation
constraints in the Nickel sense are *not* enforced as hard constraints;
ordering preservation is measured afterwards (below). A real TOP-W-St
implementation would need an LP solver (e.g. scipy `linprog` /
HiGHS) formulating the H/V DAG constraints — that is the next step if
this baseline proves too crude, and its Lemma-1 overlap-free
interpolation guarantee does not apply to this baseline.

- **Projection**: centroids (lon/lat, EPSG:4269) → EPSG:5070 (NAD83 /
  Conus Albers, metres) via pyproj, fitted to a 960×600 view
  (CONUS into x 70–890, y 40–560; scale 0.19939 view-units/km,
  1 unit = 5.015 km). Y is flipped (north = top).
- **AK/HI insets**: raw EPSG:5070 would put Alaska/Hawaii thousands
  of km from the mainland and blow up the view, so they are placed as
  standard Albers-USA-style insets — AK centre (130, 515), HI centre
  (290, 545) — exactly as d3's `albersUsa` does. Their `side_km` and
  `displacement_km` are left blank; displacement is in view units
  only (both 0.0 — isolated in their insets, they never overlapped).
- **Sizing**: side = 0.023606 · √population, so side² is exactly
  proportional to population (cartographic error by construction
  ≈ 6×10⁻¹⁶, i.e. zero apart from CSV rounding). Total square area =
  32% of the view. CA side 148.4 units (≈744 km equiv.), WY 17.9.
- **Gap**: target minimum gap 2.0 view units between squares
  (a chosen ε-gap in the Nickel spirit, not a paper value).

**Verification (measured, not claimed)**
- True overlaps (gap 0): **0**; gap violations (gap 2): **0**.
  Max overlap area 0. Phase 1 (repulsion + weak anchor) did *not*
  converge in 3000 iterations (28 overlapping pairs left — the
  anchor fights the repulsion in the crowded north-east); phase 2
  (repulsion only) converged in 65 iterations.
- Displacement from Albers centroid, 48 CONUS states:
  **mean 83.5 km, median 45.5 km, max 482.5 km (NY)**. Next largest:
  SC 357, MO 270, MA 265, PA 262 km — all in the crowded east.
  NY was pushed ~96 view units north by the PA/NJ/CT/MA cluster;
  FL was pushed ~31 units south by GA/AL (see `demers_check.png`).
  CA is clamped to the left view edge (x = side/2).
- Ordering preserved vs initial centroids: **E–W 98.8%**
  (1210/1225 pairs), **N–S 95.7%** (1172/1225 pairs). The violations
  are concentrated in the north-east cluster, as expected.
- Visual check (`demers_check.png`): the layout is recognisably the
  US; red + marks are the starting centroids, mostly inside their
  squares except NY (centroid well below its square) and FL
  (centroid above its square).

**Caveats**: this is a baseline, not TOP-W-St. It has no stability
model (no star/successive weighting across metrics), no guarantee
that interpolating between two such layouts stays overlap-free, and
the north-east displacements are large. If the Vega-Lite test needs
smooth metric-switching animation, solve the LP properly; if it only
needs one static population layout, this baseline is usable as-is.

## 2. Mosaic / tile grid — `tilegrid_states.csv`

- **Source**: the amCharts US tile-map demo grid,
  https://www.amcharts.com/demos/tile-map/ (accessed 2026-11-08),
  positions read directly from the page's data array. It is a
  **12-column × 9-row grid** (grid_col 0–11, grid_row 0–8, row 0 at
  top) — *not* the 11×8 grid mentioned in the brief; the NPR
  11×8 coordinates could not be verified from a citable source, so
  the fully-verifiable amCharts grid was used instead. The demo's
  51st entry (DC, col 10, row 4) was dropped; the 50 states remain.
- **Encoding**: one equal tile per state; population is *not* in the
  tile size — it must be encoded by colour in the chart (as the
  amCharts demo does). This layout discards the 68.5× skew by design.
- amCharts offsets even rows by +0.5 columns for its *circles*; the
  CSV keeps **integer** grid positions. A hex rendering should apply
  that half-cell stagger; a square rendering should not.
- **Verification**: 50 states present, **50 unique cells**, no
  duplicates, no missing states. Grid adjacency check against true
  geographic adjacency (derived from `states_5m.geojson` polygons,
  107 true adjacencies): the tile grid preserves **53/107 (49.5%)**
  as 4-neighbour (orthogonal) adjacencies, with **19 false
  adjacencies** (grid neighbours that are not true neighbours).
  Several "lost" pairs are diagonal neighbours in the grid, which
  the strict 4-neighbour metric counts as lost (e.g. MI–OH,
  CA–OR). Full lists in `tilegrid_adjacency.json`. ~50% adjacency
  preservation is typical for tile grids — report it, don't hide it.

## 3. Contiguous (diffusion) — NOT produced

See `contiguous_note.md`. In short: go-cart.io is interactive-only
(no direct download/API found); the only fetchable precomputed file
(subyfly/topojson, 2014 population estimates) **failed verification**
— mean absolute relative area error 50%, Montana +406%, California
under-sized — and is the wrong vintage, so it was rejected, not used.
A real 2020 contiguous cartogram needs go-cart.io driven in a
browser with our 2020 P1 values, or a server-side flow-based run.
Expected properties when it exists: near-zero error, all adjacencies
preserved, ~400 KB (Alam et al. 2015).

## What the Vega-Lite chart needs next

- Reference map (undistorted, from `states_5m.geojson`/`topojson`)
  juxtaposed with the cartogram, with linked brushing — per
  Nusrat & Kobourov (2016) and Duncan & Gastner (2024).
- Demers: `rect` marks from `demers_states.csv` (x, y, side);
  colour free for a second variable.
- Tile grid: `rect` marks from `tilegrid_states.csv`
  (grid_col, grid_row); colour = population (log scale recommended —
  68.5× range); state abbreviation labels on tiles.
- Contiguous: blocked on the go-cart.io run above; do not substitute
  the 2014 file.
