# Demers squares layout — 435 voting US congressional districts

Layout CSV + verification only. **No Vega-Lite chart was built.**

## Files

| File | Contents |
|---|---|
| `demers_districts.csv` | Demers squares: geoid, state, cd, name, population, side (view units + km equiv.), x/y, centroid x/y, displacement, inset flag — 435 rows |
| `demers_verification.json` | Machine-readable verification numbers (all recomputed from the written CSV) |
| `compute_demers_districts.py` | Reproducible solver (Python, `~/workspace/.venvs/gis/bin/python`) |
| `demers_notes.md` | This file |

## Method — honestly labelled

**Iterative overlap-removal (FRC-style baseline). This is NOT the Nickel et
al. TOP-W-St linear program.** No LP was solved. Squares start at their
Albers centroids with side `c·√population`, and overlaps are resolved by
iterative pairwise separation along the axis of least penetration, with a
weak anchor pull toward the starting position in phase 1 only. H/V
separation constraints in the Nickel sense are *not* enforced as hard
constraints; ordering preservation is measured afterwards (below). A real
TOP-W-St implementation would need an LP solver (e.g. scipy `linprog` /
HiGHS) formulating the H/V DAG constraints — and its Lemma-1 overlap-free
interpolation guarantee does not apply to this baseline. Same method and
parameters as the states solver (`../compute_layouts.py`): 960×600 view,
gap 2.0 view units, total square area 32% of the view.

One adaptation was forced by scale (435 regions vs 50): overlap
*detection* is vectorised with numpy broadcasting (435×435 pairwise matrix
per iteration, 94,395 pairs), and only the overlapping pairs found are
pushed, sequentially (Gauss-Seidel, exactly as the states solver's inner
loop). A naive O(n²) Python pair loop per iteration was not used. Runtime
for the whole solve was ~23 s.

## Inputs

- `../districts.csv` — 441 rows; only the 435 with `is_delegate=0` are
  used. Excluded delegates: DC 1198 (689,545), AS 6098 (49,710), GU 6698
  (153,836), MP 6998 (47,329), PR 7298 (3,285,874), VI 7898 (87,146).
  Voting populations: min 542,112 (MT-01, geoid 3001), max 989,948 (DE
  at-large, geoid 1000), mean 760,367, median 766,987, SD 37,920,
  ratio 1.83×, sum 330,759,736.
- `../cd119_5m.geojson` — 2024 Cartographic Boundary Files 1:5,000,000,
  119th Congress (EPSG:4269). Centroids are geometric centroids computed
  here from the polygons with shapely (lon/lat), then projected — the
  `districts.csv` centroids were used only for the cross-check below, not
  for the layout.

## Projection and insets

Centroids (lon/lat, EPSG:4269) → EPSG:5070 (NAD83 / Conus Albers, metres)
via pyproj, fitted to the 960×600 view (CONUS into x 70–890, y 40–560;
scale 0.18821 view-units/km, 1 unit = 5.313 km; y flipped, north = top).

Alaska (0200, at-large) and Hawaii (1501, 1502) are Albers-USA-style
insets exactly as the states solver did (AK bottom-left, HI below CONUS):
AK centre (130, 515); HI has two districts, so they sit side by side at
(268, 545) and (293, 545), centred on the states solver's HI position
(290, 545). All three are flagged `inset=TRUE`; their `side_km` and
`displacement_km` are blank, displacement in view units only (all 0.0 —
isolated in their insets, they never overlapped and never moved).

## Centroid cross-check (geojson shapely centroid vs districts.csv)

Max difference **43.37 km (AK at-large, 0200)** — the geometric centroid of
Alaska's sprawling multi-polygon (Aleutians included) sits well away from
the CSV centroid; AK is an inset, so this does not affect the layout.
CONUS only (432 districts): max **6.95 km (ID-01, 1601)**, then CA-03
5.23 km, MN-07 4.51 km; mean 0.28 km, median 0.07 km; 26 of 435 differ
by >1 km, 3 by >5 km. The CSV centroids are evidently near-identical to
the geometric centroids for ordinary districts; the layout uses the
geojson centroids throughout.

## Sizing — near-equal squares, by construction

Side = 0.023606 · √population (same constant as the states layout — same
total population, same 32% area fraction). Total square area 184,320
(32.0% of the view).

- Side min **17.38 units = 92.3 km (MT-01, 3001)**, max **23.49 units =
  124.8 km (DE at-large, 1000)**; side ratio 1.351×.
- Area ratio max/min **1.826×** — exactly the population ratio (1.826×),
  by construction. Populations are near-equal, so the squares are
  near-equal in size: unlike the states layout (68.5× population range),
  size carries almost no information here — the cartogram's work is all
  in position, not area.
- Cartographic error by construction ≈ 6×10⁻¹⁶ (side² exactly
  proportional to population); from the written CSV (4dp rounding) 1.04×10⁻⁵.

## Convergence history (honest)

Initial state: **1,833 overlapping pairs** at gap 2.0 (1,608 true
geometric overlaps at gap 0) — the dense metro clusters (NYC, LA,
Chicago, …) start piled on top of each other.

- **Phase 1** (repulsion + weak anchor 0.002): did **not** converge in
  3000 iterations, 10.8 s. Overlaps fell 1833 → ~533 in the first 100
  iterations, then plateaued at ~560 for the remaining 2900 (the anchor
  fights the repulsion in the crowded north-east — same pattern as the
  states solver, which also failed to converge in phase 1 with 28 pairs
  left). Final: 574 overlapping pairs.
- **Phase 2** (repulsion only): **converged in 4,142 iterations,
  11.1 s.** Decline was fast at first (559 → 106 by iter 500 → 84 by
  iter 1000 → 51 by iter 2000 → 19 by iter 3000) then a long tail: the
  count hovered at 7–14 pairs, bouncing up and down, for the last ~600
  iterations before collapsing to 0 at iteration 4141 — a jammed cluster
  resolving one pair at a time. Total solve ≈ 22 s. Convergence is real
  (0 overlapping pairs in the solver), not claimed on the basis of the
  iteration cap.

## Verification — recomputed from the written CSV, not the solver log

- True overlaps (gap 0): **0**; max overlap area 0.000 sq units.
- Gap violations (gap 2.0): **0**.
- Displacement from centroid, 432 CONUS districts: **mean 184.7 km,
  median 142.9 km, max 881.4 km (NJ-11, geoid 3411)**. Next largest:
  NJ-06 821.8, NY-12 768.7, NY-03 745.6, NJ-07 734.5, CT-04 700.4,
  NY-04 694.5, NY-07 681.3, NJ-05 680.2, NY-17 679.8 km — all in the
  NYC/northern-NJ/southern-CT cluster. Displacements are far larger than
  the states layout's (mean 83.5 km, max 482.5 km): 435 near-equal
  ~20-unit squares have to expand the north-east corridor enormously,
  because dozens of districts whose centroids are kilometres apart each
  need a ~110 km square. Even Alabama moved a lot (AL-01: 204 km).
  MT-01 (3001) did not move at all (0.0 km) — isolated, never overlapped.
- Ordering preserved vs initial centroids (all 94,395 pairs):
  **E–W 96.3%** (90,928/94,395), **N–S 92.3%** (87,171/94,394; one pair
  ties exactly in initial y and is excluded from the N–S total). Lower
  than the states layout (98.8% / 95.7%), as expected at this density;
  violations concentrate in the north-east cluster.
- All 435 geoids present, population sum 330,759,736, no delegates.

## Two rounding artefacts, both negligible and disclosed

- **2dp → 4dp.** The first write used 2 decimals (as the states file
  does). Verification from that file showed 118 gap violations — but all
  with penetration ≤0.01 units, i.e. pure rounding: hundreds of pairs sit
  within 0.02 units of the gap boundary. The file was rewritten at 4
  decimals for positions, sides and displacements (side_km /
  displacement_km stay at 1dp, informational only); re-verification
  from the rewritten CSV gives 0 violations. The solver itself was not
  changed.
- **Edge-clamped squares.** 4 squares are clipped exactly to the view
  edge by the solver (FL-19 1219, FL-25 1225 on the bottom edge; NJ-09
  3409, NY-02 3602 on the right edge). At 4dp their written centres read
  up to 0.00005 view units beyond the nominal half-side bound — rounding
  only (≈0.0003 km). No square extends beyond the view by any meaningful
  amount.
- Smallest single-axis clearance among diagonally separated pairs is
  0.0021 units (other axis ≥2 units) — not a gap violation; the Demers
  gap condition is per-axis-pair and is satisfied.

## Caveats

- Baseline, not TOP-W-St: no LP, no H/V hard constraints, no stability
  model, no guarantee that interpolating between two such layouts stays
  overlap-free. If a Vega chart needs smooth metric-switching animation,
  solve the LP properly; for one static population layout this baseline
  is usable as-is.
- The north-east displacements are very large (up to 881 km) and the
  layout there will look substantially rearranged relative to geography —
  that is the honest cost of giving every district a ~110 km square.
  Report it, don't hide it.
- Insets (AK, HI) are placed by convention, not by projection; their
  displacement figures are view units only.
