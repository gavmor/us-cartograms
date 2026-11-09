# Congressional-district cartograms — 435 voting districts (119th Congress)

Prototype layouts only — no Vega chart yet. All three paradigms were computed
from the same verified Census data, verified independently from the written
files, and are ready for a Vega / Vega-Lite artifact.

## Scope — 435 voting districts, delegates excluded

- **Included: 435 voting districts** of the 119th Congress (seated Jan 2025–
  Dec 2026; boundaries per state info by May 31, 2024).
- **Excluded: 6 delegate districts** (CD119FP `98`), non-voting, listed
  explicitly — they would distort a seats/population cartogram, PR alone
  being 4.3× a typical district:

  | GEOID | District | Population |
  |---|---|---:|
  | 1198 | DC Delegate District (at Large) | 689,545 |
  | 6098 | AS Delegate District (at Large) | 49,710 |
  | 6698 | GU Delegate District (at Large) | 153,836 |
  | 6998 | MP Delegate District (at Large) | 47,329 |
  | 7298 | PR Resident Commissioner District (at Large) | 3,285,874 |
  | 7898 | VI Delegate District (at Large) | 87,146 |

- **Voting-district populations** (2020 Census CD119 P1, resident):
  min 542,112 (MT-01, geoid 3001), max 989,948 (DE at-large, geoid 1000),
  mean 760,367, median 766,987, SD 37,877, ratio **1.83×**, sum 330,759,736.
  Six states are at-large (AK, DE, ND, SD, VT, WY).
- **The near-equal finding, up front:** district populations are equalised
  by design, so any cartogram whose area encodes population alone is
  near-uniform by construction. Area ratio max/min is 1.826× in every
  layout below. That is the finding, not a bug — see §5.

## Inputs

- `../districts.csv` — 441 rows (435 voting + 6 delegates), 2020 Census P1.
- `../cd119_5m.geojson` / `../cd119_5m.topojson` — 2024 Cartographic
  Boundary Files, 1:5,000,000, 119th Congress.
- Centroids were recomputed from the geometry (shapely geometric centroid,
  EPSG:4269 → EPSG:5070) and cross-checked against `districts.csv`:
  CONUS mean 0.28 km, median 0.07 km, max 6.95 km (ID-01); overall max
  43.37 km is AK at-large alone (sprawling multi-polygon; it is an inset).
  37/435 centroids fall outside their own (non-convex / island) polygon;
  the centroid is still used as the anchor, as in the states work.
- True district adjacencies (touches-or-intersects, as in the states
  verify code): **1,134** (1,133 CONUS + HI-01–HI-02); 1,129 of the CONUS
  pairs share a border, 5 are point-touches only; 818 (72.1%) are
  same-state.
- Python: `~/workspace/.venvs/gis/bin/python` (shapely 2.2, pyproj 3.8,
  numpy, scipy). Node v24.22.1 for the WASM run.

## 1. Demers squares — `demers_districts.csv` (49 KB)

Method — **honest label: iterative overlap-removal (FRC-style baseline),
NOT Nickel et al. TOP-W-St LP.** No LP was solved; there are no H/V hard
separation constraints and no Lemma-1 overlap-free interpolation
guarantee. Squares start at Albers centroids in a 960×600 view, side =
0.023606·√population, total square area 32.0% of the view; phase 1
repulsion + weak anchor (0.002), phase 2 repulsion only. Adapted from
`../compute_layouts.py` (states solver); solver in
`compute_demers_districts.py`.

- Sides: min 17.38 units = 92.3 km (MT-01), max 23.49 units = 124.8 km
  (DE at-large); side ratio 1.351×, **area ratio 1.826× = population
  ratio by construction**. Size carries almost no information here; the
  cartogram's work is all in position.
- Overlaps, verified by re-reading the written CSV: **true overlaps
  (gap 0): 0; gap violations (gap 2): 0.** Cartographic error by
  construction ~6×10⁻¹⁶ (≈1×10⁻⁵ from the written CSV).
- Displacement, 432 CONUS districts: **mean 184.7 km, median 142.9 km,
  max 881.4 km (NJ-11, geoid 3411)**; next NJ-06 821.8, NY-12 768.7,
  NY-03 745.6, NJ-07 734.5 km — all NYC / northern-NJ / southern-CT.
  Much larger than states (mean 83.5, max 482.5 km): 435 near-equal
  ~110 km squares have to expand the north-east corridor enormously.
  MT-01 did not move at all (0.0 km).
- Ordering preserved (all 94,395 pairs): **E–W 96.3% (90,928/94,395),
  N–S 92.3% (87,171/94,394)** — lower than states (98.8% / 95.7%).
- Convergence, genuine: phase 1 did **not** converge in 3,000 iters /
  10.8 s (1,833 initial overlapping pairs → plateau ~560, 574 left);
  phase 2 (repulsion only) **converged in 4,142 iterations / 11.1 s**
  (fast to 84 pairs by iter 1,000, then a long tail at 7–14 pairs for
  ~600 iters before collapsing to 0). Total solve ~23 s. Detection was
  vectorised with numpy (435×435 matrix per iteration).
- Insets (flagged `inset=TRUE`, `side_km`/`displacement_km` blank):
  AK 0200 at (130, 515); HI-01 1501 at (268, 545), HI-02 1502 at
  (293, 545), centred on the states solver's HI position.
- Disclosed artefacts: the first write at 2 decimals showed 118 gap
  violations, all penetration ≤0.01 units — pure rounding, since
  hundreds of pairs sit within 0.02 units of the gap boundary. Rewrote
  at 4 decimals; re-verification gives 0 violations. 4 squares are
  clipped exactly to the view edge (FL-19, FL-25 bottom; NJ-09, NY-02
  right); at 4 dp their centres read up to 0.00005 units beyond the
  nominal bound — rounding only (~0.0003 km). See `demers_notes.md`
  and `demers_verification.json`.

## 2. Tile-grid mosaic — `tilegrid_districts.csv` (24 KB)

Method: rectangular grid over the CONUS Albers bbox; candidate cells are
those whose centres fall inside the CONUS landmask (`states_5m.geojson`,
48 CONUS states + DC unioned); **Hungarian assignment (scipy
`linear_sum_assignment`) minimising total displacement**. Solver +
verifier in `compute_tilegrid_districts.py`. No published square-grid
House-district layout was used: a published hexmap does exist — Daily
Kos `DKOS_CD_Hexmap_v1.1` (one hex per district), via Pitch Interactive
tilegrams / tilegramsR — but it is hexagonal, not a square grid, and
2018 vintage (pre-2020 redistricting), so it cannot supply CD119
square-grid coordinates. This layout was computed from scratch.

- Grid: **35 cols × 22 rows, cell 132 km**
  (√(CONUS land 7,809,227 km² / 432) = 134.4 km; 132 km is the nearest
  round size below that yielding ≥432 in-mask cells: 446 candidates,
  432 used, 14 spare — all 14 over the Great Lakes). Total extent incl.
  insets 35×24: rows 0–21 main grid, row 22 blank, row 23 insets.
  AK 0200 at (2, 23); HI-01 1501 at (8, 23), HI-02 1502 at (9, 23).
- Completeness, verified from the written CSV: **435/435 districts,
  435 unique cells, none missing/duplicated.**
- Displacement, CONUS, linear-cost assignment: **mean 659.4 km, median
  425.9 km, p90 1,639.6 km, max 3,247.9 km (NY-01, geoid 3601)**.
  107 districts (25%) move >1,000 km, 22 move >2,000 km. Worst states
  by mean: NY 1,528, RI 1,422, WI 1,336, NJ 1,312 km. Insets ~40 grid
  units from extrapolated true positions.
- Adjacency (4-neighbour, orthogonal): **preserved 215/1,134 (19.0%)**,
  lost 919, false 563. 8-neighbour (incl. diagonals): 339 (29.9%).
  Shared-border-only true count is 1,129 — same 19.0% preserved. Far
  worse than the states grid's 49.5%, and structural: districts are
  population-equal but land-unequal, so the dense East / California
  excess must flow hundreds of km outward.
- State grouping: 43.6% of grid-neighbour pairs are same-state (true:
  72.1%); only **18/50 states form a single 4-connected component**;
  32 fragmented, worst NJ (12 tiles, 10 components), NY (26, 10),
  OH (15, 10). Ordering preserved: E–W 84.3%, N–S 96.0%.
- **Flag — linear cost is the specified optimum, but it is ugly.**
  Minimising total displacement concentrates displacement: median stays
  close (426 km) but 22 districts are exiled >2,000 km (NY-01's tile
  sits by Montana) and adjacency is shredded. The squared-cost variant
  on the same grid (`tilegrid_districts_squared.csv`, same columns)
  trades +5.2% total displacement (299,700 vs 284,875 km) for **max
  1,338 km (NY-25), zero districts >2,000 km, adjacency preserved
  431/1,134 (38.0%), false down to 349** — at the cost of a higher
  median (738 km). For a readable national map, the squared file is
  the better deliverable; the linear file is main only because the
  brief specified minimising total displacement. Sensitivity: 128–133 km
  cells and ±¼/±½-cell offsets move total displacement only −6%…+5%
  and preservation 17–19% — alignment is second-order.
  See `tilegrid_notes.md`, `tilegrid_verification.json`.

## 3. Contiguous diffusion — `contiguous_districts_2020_gocart.geojson` (7.1 MB)

Method: go-cart-wasm 0.5.0 (Gastner, Seguy & More 2018, fast flow-based),
in Node, reusing the installed module at
`../contiguous-prototype/npm/node_modules/go-cart-wasm/` and the states
pipeline (`run_gocart.mjs` pattern). Input reprojected to EPSG:5070
(equal-area — never lon/lat); output inverse-projected to lon/lat
(EPSG:4269). Scripts: `build_input_5070.py`, `run_gocart.mjs`,
`inverse_project.py`, `verify_gocart.py`, `repair_and_reverify.py`.

- Timing (Node v24.22.1): WASM init 0.04 s, **`makeCartogram` 22.92 s**
  wall, no errors/warnings. States took 12.10 s — districts ~1.9×
  slower for 8.7× the regions.
- Input verified: 435 voting districts, population total 330,759,736.
- **Raw WASM output: mean abs area error 0.018%, worst TX-23 +0.92%,
  Pearson r = 0.999916, 1,134/1,134 adjacencies preserved, 0 lost.**
  The solver itself is slightly more accurate than on states (0.021%).
- **Validity / repair — the main cost at 435 regions: 99 invalid
  geometries** in the raw output (self-intersection pinches; states
  had 1). Plain `shapely.make_valid` was tried and **rejected on
  measured grounds** (mean abs area change 0.39%, max +12.75% on
  AZ-02, degrading mean error to 0.155%). Repair used instead:
  nonzero-winding face selection over `make_valid` faces — the
  nonzero fill rule a renderer applies to the raw ring, so the
  repaired shape is what the raw output already draws. Cost: max abs
  +6.38% (AZ-02), mean abs 0.22%, area-weighted total +0.11%.
- **Delivered file (after repair): mean abs error 0.084%, worst AZ-02
  +6.33% (a repair artefact, not a solver error), Pearson r =
  0.997132**, still **1,134/1,134 adjacencies preserved, 0 lost,
  2 gained** (AZ-04/AZ-07, WA-06/WA-07). 0 invalid in lon/lat and
  0 after re-projection to EPSG:5070; round-trip re-measurement
  reproduces 0.084% exactly. Area ratio DE-at-large / MT-01 = 1.826,
  exactly the population ratio. The program's own per-region
  `area_error` property is preserved on every feature (mean abs
  0.018%, max 0.92% — the raw solver values).
- AK/HI (same decision as states): 432 CONUS districts keep true
  EPSG:5070 positions; AK at-large scaled 0.35 about its centroid to
  a bottom-left inset, HI's 2 districts translated together below
  CONUS. Inset centroids in the lon/lat output: **AK (−115.979,
  17.771), HI-01 (−106.502, 22.086), HI-02 (−105.744, 20.667)**.
  Lon/lat bbox −124.945..−64.122, 14.643..50.284.
- Files: `contiguous_districts_2020_gocart.geojson` (deliverable,
  lon/lat, 435 features, all valid), `districts_5070.geojson`
  (projected input, 7.0 MB),
  `contiguous_districts_2020_gocart_5070.geojson` (raw WASM output,
  verbatim, 99 invalid, 6.7 MB),
  `contiguous_districts_2020_gocart_5070_repaired.geojson` (repaired
  projected output, for audit, 7.0 MB), `error_table.csv`
  (per-district, 435 rows), `contiguous_verification.json`,
  `contiguous_notes.md`.

## 4. What this implies — the near-equal-population finding

By population alone, all three paradigms collapse toward uniformity:

- **Contiguous** is technically excellent (raw solver 0.018% error,
  all adjacencies intact) but visually near-uniform: every district
  is ~760k people, so the deformed map looks almost like an
  equal-area map with the north-east slightly swollen and the West
  slightly pinched. It proves the pipeline at 435 regions; it does
  not differentiate districts.
- **Demers** is near-equal squares by construction; its entire signal
  is positional, bought at a mean displacement of 185 km and a max of
  881 km in the north-east corridor.
- **Tile-grid** is the only paradigm whose output is *designed* for
  this case — one tile per seat — but at 435 tiles it pays heavily:
  19% adjacency preservation (linear cost) or 38% (squared cost),
  mean displacement 659–694 km, and 32/50 states fragmented.

**Recommendation for the Vega artifact: lead with the tile-grid
mosaic, squared-cost variant** (`tilegrid_districts_squared.csv`) —
one tile per seat is the natural districts paradigm, and the squared
assignment is the readable one (max displacement 1,338 km, no
exiles, 38% adjacency). Show the contiguous cartogram second, as the
accuracy proof (raw 0.018% / delivered 0.084%) and the reference for
what population-proportional area actually looks like at this scale
— i.e. almost uniform. Show Demers third, or as a toggle, labelled
as the FRC-style baseline. **For a differentiated districts
cartogram, a genuinely varying weight is needed** — votes cast,
turnout, margin, or seats-won — not population; that is the next
data pull, and it would make all three paradigms informative again.

## 5. Files in this folder

| File | Size | Contents |
|---|---:|---|
| `demers_districts.csv` | 49 KB | Demers layout, 435 rows |
| `demers_verification.json` | 5 KB | Demers verification numbers |
| `demers_notes.md` | 9 KB | Demers method / caveats |
| `compute_demers_districts.py` | 19 KB | Demers solver (reproducible) |
| `tilegrid_districts.csv` | 24 KB | Tile grid, linear-cost (main) |
| `tilegrid_districts_squared.csv` | 24 KB | Tile grid, squared-cost variant |
| `tilegrid_verification.json` | 7 KB | Tile-grid verification numbers |
| `tilegrid_notes.md` | 10 KB | Tile-grid method / caveats |
| `compute_tilegrid_districts.py` | 22 KB | Tile-grid solver + verifier |
| `contiguous_districts_2020_gocart.geojson` | 7.1 MB | Contiguous deliverable, lon/lat |
| `contiguous_districts_2020_gocart_5070.geojson` | 6.7 MB | Raw WASM output, EPSG:5070 |
| `contiguous_districts_2020_gocart_5070_repaired.geojson` | 7.0 MB | Repaired projected output |
| `districts_5070.geojson` | 7.0 MB | Projected input, EPSG:5070 |
| `error_table.csv` | 37 KB | Per-district area error, 435 rows |
| `contiguous_verification.json` | 6 KB | Contiguous verification numbers |
| `contiguous_notes.md` | 11 KB | Contiguous method / AK-HI / repairs |
| `build_input_5070.py`, `run_gocart.mjs`, `inverse_project.py`, `verify_gocart.py`, `repair_and_reverify.py` | — | Contiguous pipeline scripts |
| `solver_run.log`, `solver_run2.log` | — | Demers solver run logs |

## 6. What the Vega artifact must do next

- **Tile grid (lead):** `rect` marks from
  `tilegrid_districts_squared.csv` (recommended) or
  `tilegrid_districts.csv` (linear-cost, as specified); equal tiles,
  population / votes in colour, not area; linked hover to the
  reference map; state grouping is fragmented — do not imply
  contiguity the grid does not have; note 38% (squared) / 19%
  (linear) adjacency preservation on the page.
- **Contiguous:** `geoshape` from
  `contiguous_districts_2020_gocart.geojson`, **identity/fit
  projection, `reflectY: true`, NOT Albers USA** — AK/HI insets are
  not at true coordinates (centroids above). Run live in a Web
  Worker with go-cart-wasm 0.5.0 as in the states artifact
  (~23 s at 435 regions, indeterminate progress), or show the
  delivered file labelled as precomputed — do not silently swap
  one for the other. Show the raw-vs-delivered error distinction:
  solver 0.018%, delivered 0.084% (AZ-02 repair artefact).
- **Demers:** `rect` marks from `demers_districts.csv` (960×600
  view, 1 unit = 5.313 km); label it as the iterative
  overlap-removal baseline, not TOP-W-St LP — no Lemma-1 guarantee.
- **Reference map alongside all three**, linked brushing, infotips
  (district, state, population, land area, cartographic error where
  applicable), and an area-to-value legend for the contiguous view.
  State clearly on the page that districts are population-equal
  by design (1.83×), so population-area cartograms are near-uniform,
  and that a votes/margin weight is the next step for a
  differentiated view.
