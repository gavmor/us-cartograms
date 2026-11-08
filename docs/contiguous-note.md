# Contiguous (diffusion) cartogram — status: NOT obtained for the 2020 test

No trustworthy precomputed US-states population cartogram matching the
2020 Census P1 data could be obtained, so **no deformed polygons were
invented**. The chart should show reference + Demers + mosaic only, until a
real contiguous cartogram is generated server-side (see below).

## What was tried

1. **go-cart.io** (Shi, Duncan & Gastner; evaluated in Duncan & Gastner
   2024, PLOS ONE 19(5): e0298192) — the fast flow-based method, cloud
   server, SVG/GeoJSON export. It is **interactive-only**: the site
   (https://go-cart.io/, fetched 2026-11-08) offers "Make Your Cartogram"
   as a browser workflow (pick a geography, paste/upload a CSV, compute
   server-side, export). No direct download URL or public API for a
   precomputed 2020 US-states population cartogram was found, and the
   PLOS paper reports no precomputed export. Generating the real thing
   means driving go-cart.io in a browser with our 2020 P1 values, or
   running a flow-based/diffusion implementation server-side
   (Alam et al. 2015 report 25–50 s for a 1024×1024-grid diffusion run
   on a US map — this is not an in-browser Vega-Lite computation).

2. **Candidate found and REJECTED**: `contiguous_states_2014est.topojson`
   (367 KB; converted copy `contiguous_states_2014est.geojson`, 2.3 MB),
   from https://github.com/subyfly/topojson —
   `united-states/us-cartogram-2014-est-population.json` (MIT licence,
   51 geometries: 50 states + DC, with embedded `pop_2014` fields).
   It was fetched and verified, not used:
   - **Vintage mismatch**: distorted to **2014 population estimates**,
     not our 2020 Census P1 values.
   - **Fails the area-proportionality check**: distorted-area share vs
     2014 population share gives Pearson r = 0.97, but mean absolute
     relative error **50%**, worst **Montana +406%** (area share 1.63%
     vs population share 0.32%), Alaska +352%, North Dakota +200%.
     California is under-sized (area share 9.3% vs population share
     12.2%). A genuine diffusion cartogram should be near-zero error;
     this file retains much of the states' geographic area (large
     low-population western states stay large). The distortion
     algorithm and its provenance are undocumented in the repo
     ("README does not provide explicit source URLs for these
     specialized projections").
   - AK/HI are inset into the Mexico/Central-America area of the
     coordinate space (AK bounds approx. x −119 to −107, y 22 to 32),
     i.e. the file is a display layout, not a geographic one.

   Kept in this folder as evidence of the attempt, with `_2014est` in
   the name so it cannot be mistaken for the 2020 test layout. **Do not
   render it as "the population cartogram" for the 2020 data.**

## What a real contiguous layout needs

- The 2020 P1 populations from `states.csv` (50 states), run through
  go-cart.io (upload CSV, export GeoJSON) or an equivalent flow-based
  implementation, on the 2024 Cartographic Boundary 5m geometries.
- Expected properties when it exists: near-zero cartographic error
  (Alam et al.'s DIFF run: ε ≈ 0.013), all adjacencies preserved,
  file ~400 KB for a US map (Alam §2.3), recognisable shapes.
- Until then, the honest comparison is Demers vs mosaic vs the
  undistorted reference map — which is also what Nusrat & Kobourov
  (2016) recommend showing alongside any cartogram anyway.
