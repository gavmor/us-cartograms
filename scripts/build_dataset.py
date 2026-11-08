#!/usr/bin/env python3
"""Build Vega-Lite-ready Census datasets for the US cartogram test.

Sources (all U.S. Census Bureau):
- Boundaries: 2024 Cartographic Boundary Files, 1:5,000,000
  https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_5m.zip
  https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_5m.zip
- District populations: 2020 Census 119th Congressional District Summary File
  (CD119, released 2024-12-05), Table P1 Total Population, via the
  data.census.gov table API (keyless proxy to api.census.gov/data/2020/dec/cd119).
  Direct api.census.gov calls 302 to a missing-key page as of 2026-11-08, so the
  data.census.gov proxy endpoint is used instead.
- State populations: same CD119 P1 table, summary level 040 (52 rows: 50 states
  + DC + PR), cross-checked against 2020 Apportionment Table A resident pops.
- Island Areas (AS/GU/MP/VI, not in CD119/DHC): 2020 Island Areas Censuses,
  Census Bureau story 2021-10-28, total 338,021.

Centroids: geometric centroid computed in EPSG:5070 (NAD83 / Conus Albers,
equal-area, handles the Alaska dateline correctly), then inverse-projected
to lon/lat (EPSG:4269, NAD83 as shipped). Recorded as centroid_lon/lat.
"""
import json, os, re, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

BASE = os.path.expanduser("~/workspace/cartogram-census")
RAW = os.path.join(BASE, "raw")
os.makedirs(os.path.join(RAW, "cd119_p1"), exist_ok=True)

from osgeo import ogr, osr
ogr.UseExceptions()

# ---------------------------------------------------------------- state pops
state_pop = {}   # STATEFP -> (name, pop) from CD119 P1, summary level 040
with open(os.path.join(RAW, "state_pop_cd119_p1.json")) as f:
    d = json.load(f)
for row in d["response"]["data"][1:]:
    geoid, _na, pop, name = row
    state_pop[geoid[-2:]] = (name, int(pop))
print(f"state P1 rows (CD119): {len(state_pop)}")

# Cross-check vs Apportionment Table A resident population (parsed from PDF)
txt = subprocess.run(["pdftotext", "-layout",
                      os.path.join(RAW, "apportionment-2020-tableA.pdf"), "-"],
                     capture_output=True, text=True).stdout
# lines like: Alabama  5,030,053  5,024,279  5,774 ...
tableA = {}
for line in txt.splitlines():
    m = re.match(r"^([A-Za-z .]+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", line.strip())
    if m:
        tableA[m.group(1).strip()] = int(m.group(3).replace(",", ""))  # resident 2020
mismatch = []
for fp, (name, pop) in state_pop.items():
    if name in tableA and tableA[name] != pop:
        mismatch.append((name, pop, tableA[name]))
print(f"Table A cross-check: {len(tableA)} states parsed, mismatches vs CD119 P1: {mismatch}")

# Island Areas pops (2020 Island Areas Censuses, Census Bureau 2021-10-28)
ISLAND_POP = {"60": 49710, "66": 153836, "69": 47329, "78": 87146}
for fp, pop in ISLAND_POP.items():
    if fp not in state_pop:
        state_pop[fp] = (None, pop)  # name filled from shapefile later

# ---------------------------------------------------------------- CD GEOIDs
ds = ogr.Open(os.path.join(RAW, "cd119_5m/cb_2024_us_cd119_5m.shp"))
lyr = ds.GetLayer(0)
geoids = sorted({f["GEOID"] for f in lyr})
print(f"CD GEOIDs from shapefile: {len(geoids)}")
ds = None

# ---------------------------------------------------------------- fetch CD P1
def fetch(geoid):
    path = os.path.join(RAW, "cd119_p1", f"{geoid}.json")
    if os.path.exists(path) and os.path.getsize(path) > 50:
        with open(path) as f:
            return geoid, json.load(f)
    url = ("https://data.census.gov/api/access/data/table"
           f"?id=DECENNIALCD1192020.P1&g=500XX00US{geoid}")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cartogram-audit/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            with open(path, "w") as f:
                json.dump(data, f)
            return geoid, data
        except Exception as e:
            if attempt == 2:
                return geoid, {"error": str(e)}
    return geoid, {"error": "unreachable"}

cd_pop = {}
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(fetch, g): g for g in geoids}
    for i, fut in enumerate(as_completed(futs)):
        g, data = fut.result()
        try:
            row = data["response"]["data"][1]
            cd_pop[g] = int(row[2])
        except Exception:
            cd_pop[g] = None
            print(f"FAILED {g}: {str(data)[:200]}")
        if (i + 1) % 100 == 0:
            print(f"  fetched {i+1}/{len(geoids)}")
with open(os.path.join(BASE, "cd_pop_cd119.json"), "w") as f:
    json.dump(cd_pop, f, indent=1, sort_keys=True)
missing = [g for g, v in cd_pop.items() if v is None]
print(f"CD P1 fetched: {len(cd_pop) - len(missing)}/{len(cd_pop)}; missing: {missing}")
# Island Areas delegate districts are not in CD119: fill from Island Areas totals
for geoid, fp in [("6098", "60"), ("6698", "66"), ("6998", "69"), ("7898", "78")]:
    if cd_pop.get(geoid) is None:
        cd_pop[geoid] = ISLAND_POP[fp]
        print(f"filled {geoid} from 2020 Island Areas Census: {ISLAND_POP[fp]}")
with open(os.path.join(BASE, "cd_pop_cd119.json"), "w") as f:
    json.dump(cd_pop, f, indent=1, sort_keys=True)
print("saved cd_pop_cd119.json")
