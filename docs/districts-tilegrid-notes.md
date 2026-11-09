# Tile-grid (mosaic) layout — 435 voting US congressional districts, 119th Congress

One equal tile per voting district. **No Vega chart — layout CSV + verification only.**
Solver: `compute_tilegrid_districts.py` (run with `~/workspace/.venvs/gis/bin/python`).

## Files

| File | Contents |
|---|---|
| `tilegrid_districts.csv` | **Main layout** (linear-cost Hungarian): geoid, state, cd, name, population, grid_col, grid_row, inset |
| `tilegrid_districts_squared.csv` | Sensitivity variant: same grid, squared-distance cost (see §5 — it is better on every quality metric except total displacement) |
| `tilegrid_verification.json` | All verification numbers, machine-readable |
| `compute_tilegrid_districts.py` | Reproducible solver + verifier (verification re-reads the written CSV) |
| `tilegrid_notes.md` | This file |

## Headline numbers (main layout, linear cost)

- **Grid: 35 cols × 22 rows, cell 132 km.** 446 candidate cells inside the CONUS landmask, 432 used, 14 unused. Total extent incl. insets: 35 × 24 (row 22 blank, row 23 insets).
- **Completeness: 435/435 districts, 435 unique cells, none missing or duplicated** (verified from the written CSV).
- **Displacement from geometric centroid (CONUS, km): mean 659, median 426, p90 1,640, max 3,248 (NY-01).** 107 districts (25%) move >1,000 km; 22 move >2,000 km; only 91 (21%) land within one cell (132 km) of their centroid.
- **Adjacency (4-neighbour, vs 1,133 true CONUS adjacencies): 215 preserved (19.0%), 919 lost, 563 false.** Counting diagonals as neighbours (8-neighbour): 339 preserved (29.9%). For comparison the states tile grid preserved 53/107 (49.5%).
- **State grouping:** 43.6% of grid-neighbour pairs are same-state (true adjacencies: 72.1%). Only 18 of 50 states have their tiles in a single 4-connected component (incl. the 6 single-district states + HI); 32 states are fragmented — worst NJ (12 tiles, 10 components), NY (26 tiles, 10), OH (15 tiles, 10).
- **Ordering preserved vs centroids (CONUS): E–W 84.3%, N–S 96.0%.**

## 1. Method

1. **Centroids.** Geometric centroid of each district polygon from `cd119_5m.geojson`
   (2024 Cartographic Boundary Files 1:5,000,000, 119th Congress), projected to
   EPSG:5070 (km). Cross-check vs `districts.csv` centroid_lon/lat: **CONUS mean
   0.28 km, median 0.07 km, max 6.95 km (ID-01)**; overall max 43.4 km is AK
   at-large alone. The CSV centroids are evidently the same geometric centroids
   (median discrepancy 67 m); the few km-level outliers (ID-01 6.9, CA-03 5.2,
   MN-07 4.5, MT-01 4.2 km) are large/split polygons where a slightly different
   geometry vintage shifts the centroid. 37 of the 435 voting districts have a
   geometric centroid that falls *outside* their own polygon (non-convex,
   multi-part, or island districts) — the centroid is still used as the
   assignment anchor, as specified.
2. **Grid.** CONUS landmask = 48 states + DC from `states_5m.geojson`, unioned,
   EPSG:5070: area 7,809,227 km², bbox 4,614 × 2,904 km. Cell size **132 km**:
   √(area/432) = 134.4 km per tile if tiles filled the land exactly; 132 km is
   the nearest round size below that yielding ≥432 candidate cells whose centres
   fall inside the landmask (446 candidates, 14 spare). Origin = NW corner of
   the landmask bbox; grid_col 0 = west, grid_row 0 = north. The 14 unused
   candidate cells are all over the Great Lakes (cols 4–7, rows 1–6) — lake
   water inside state polygons, where no district centroid sits.
3. **Assignment.** `scipy.optimize.linear_sum_assignment` (Hungarian) on the
   432 × 446 Euclidean-distance matrix (km), minimising **total** displacement.
   AK + HI are excluded from the CONUS assignment and placed as labelled inset
   cells below the main grid, Albers-USA style: AK (0200) at (2, 23); HI-01
   (1501) at (8, 23), HI-02 (1502) at (9, 23); row 22 left blank as a
   separator. Their displacement is reported in grid units from the
   extrapolated grid position of their true centroids: AK 41.0, HI-01 39.6,
   HI-02 39.5 grid units. (Their raw EPSG:5070 positions are thousands of km
   off the CONUS grid, so km displacement is meaningless for them.) The HI
   inset pair are adjacent cells, preserving the single non-CONUS true
   adjacency (HI-01–HI-02); AK has no true neighbours.
4. **Adjacency definition.** True = district polygons touch-or-intersect
   (incl. point touches), exactly as in the states verify code: **1,134** true
   adjacencies over all 435 districts (1,133 CONUS + HI-01–HI-02). Only 5 of
   the 1,134 are point-touches with no shared border (shared-border-only true
   count 1,129; preserved 214/1,129 = 19.0% — the point-touch inclusion barely
   matters).

## 2. Why displacement is so large — this is structural, not a solver failure

Districts are population-equal (~760k each) but land-unequal: the tile grid is
area-equal. The dense East Coast and California have far more districts than
their land area's share of cells (NJ: 12 districts on land that holds ~1 cell;
NY: 26 districts on ~7 cells' worth; CA: 52 on ~24), so the excess must flow
hundreds of km outward, cascading across the map — while the rural West has
surplus cells. A greedy nearest-cell baseline totals 311,648 km vs the
Hungarian optimum 284,875 km, confirming the assignment really is the
total-displacement minimum. Worst states by mean displacement: NY 1,528 km,
RI 1,422, WI 1,336, NJ 1,312, MI 1,199, OH 1,197, PA 1,052, CT 1,042 km.
The single worst tile: NY-01 (Long Island) lands at (8, 1) — up by the
Dakotas/Minnesota, 3,248 km from its centroid, next to Montana's tiles.

## 3. Grid-size sensitivity (tested, not cherry-picked)

Cell sizes 128–133 km, bbox-anchored origin, linear cost: candidate cells
437–476, total displacement 261,327–298,482 km, mean 605–691 km, 4-neighbour
preservation 17.1–18.9%. Grid-origin offsets (±¼, ±½ cell) at 132 km moved
total displacement by −6%…+5% and preservation by 17.9–19.2% — alignment is
second-order noise. 132 km was chosen on the area principle (§1.2), not by
minimising displacement across sizes (129 km would have given 261,327 km
total, but with 38 spare cells and no better adjacency).

## 4. Caveats — read before charting

- **Tile size encodes nothing.** All tiles are equal by construction; population
  (542,112–989,948, ratio 1.83×) must be encoded by **colour**, as with the
  states tile grid. Do not size tiles by population.
- **Adjacency loss is severe: 81% of true adjacencies are lost** (19.0%
  preserved 4-neighbour; 29.9% counting diagonals). Neighbouring tiles are
  wrong more often than right as geographic neighbours (563 false vs 215 kept).
  Do not present this grid as preserving district neighbourhoods; it preserves
  rough relative position (E–W 84%, N–S 96% ordering) and state groupings only
  loosely — a third of states are splintered into ≥4 pieces.
- **A quarter of districts sit >1,000 km from their true location.** Any
  annotation, label, or linked-brushing that assumes tiles sit near their
  districts will mislead in the Northeast, Great Lakes, and California.
- **Insets are conventional, not geographic.** AK/HI cells sit ~40 grid units
  from their extrapolated true positions; the gap row (22) marks the break.
- **Delegates excluded.** DC, AS, GU, MP, PR, VI (6 districts) are not in the
  layout; PR alone (3,285,874 people) would be ~4 tiles at House-district size.
- **Geometry vintage.** CD119 (2024) boundaries; several states have since
  redistricted for the 120th Congress, so this layout is CD119-specific.

## 5. The linear-cost optimum is ugly — squared cost is much better behaved

Minimising *total* (linear) displacement is indifferent to concentrating
displacement: it keeps the median district close (426 km) by exiling 22
districts >2,000 km and shredding adjacency (19.0%). Solving the **same grid**
with **squared-distance** cost (`tilegrid_districts_squared.csv`) trades a
small total increase for a far more usable map:

| Metric (CONUS) | Linear (main) | Squared (variant) |
|---|---|---|
| Total displacement | 284,875 km | 299,700 km (+5.2%) |
| Mean / median | 659 / 426 km | 694 / 738 km |
| p90 / max | 1,640 / 3,248 km (NY-01) | 1,087 / 1,338 km (NY-25) |
| Districts >1,000 km | 107 | 84 |
| Districts >2,000 km | 22 | 0 |
| Adjacency preserved (4-nb) | 215 / 1,133 (19.0%) | 431 / 1,133 (38.0%) |
| False adjacencies | 563 | 349 |

The squared variant doubles adjacency preservation, eliminates the exiled
tail, and keeps every district within 1,338 km — at the cost of moving the
*typical* district further (median 738 vs 426 km: the displacement is spread
around instead of concentrated). If the chart's purpose is a readable national
map, the squared layout is the better deliverable; the linear layout is kept
as the main file only because the brief specified minimising total
displacement. **Recommendation: consider switching the chart to
`tilegrid_districts_squared.csv`.**

## 6. Published-grid source — found, not used

A published House-district tilegram **does** exist, contrary to the premise
carried over from the states work: the **Daily Kos congressional-district
hexmap, `DKOS_CD_Hexmap_v1.1`** — one hex per district — distributed via
Pitch Interactive's tilegrams repo
(https://raw.githubusercontent.com/PitchInteractiveInc/tilegrams/master/us-congressional-districts-2018.html)
and the tilegramsR R package (https://bhaskarvk.github.io/tilegramsR/,
verified 2026-11-08). It was **not used**: it is hexagonal, not a square
(col, row) grid, and it is **2018 vintage** (pre-2020 redistricting — district
lines and per-state counts have changed for the 119th Congress), so it cannot
supply CD119 square-grid coordinates. This layout was computed from scratch
from CD119 geometry. No published *square-grid* House-district layout was
found.
