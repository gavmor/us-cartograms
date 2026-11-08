#!/usr/bin/env python3
"""Join populations to Census boundaries; write states.csv / districts.csv + stats.

Centroid method: geometry (NAD83, EPSG:4269 as shipped) -> EPSG:5070
(NAD83 / Conus Albers, equal-area) -> geometric centroid -> back to
lon/lat EPSG:4269. Projecting first avoids the Alaska dateline problem
(raw lon/lat averaging would put Alaska's centroid near lon 0).
"""
import csv, json, os, statistics
from osgeo import ogr, osr
ogr.UseExceptions()

BASE = os.path.expanduser("~/workspace/cartogram-census")
RAW = os.path.join(BASE, "raw")

# --- populations ------------------------------------------------------------
cd_pop = json.load(open(os.path.join(BASE, "cd_pop_cd119.json")))
# fill the 4 individually re-fetched districts
for g in ("0623", "4216", "4832", "5401"):
    with open(os.path.join(RAW, "cd119_p1", f"{g}.json")) as f:
        cd_pop[g] = int(json.load(f)["response"]["data"][1][2])
json.dump(cd_pop, open(os.path.join(BASE, "cd_pop_cd119.json"), "w"),
          indent=1, sort_keys=True)
assert all(v is not None for v in cd_pop.values()), "missing CD pops remain"
assert len(cd_pop) == 441

state_pop = {}
with open(os.path.join(RAW, "state_pop_cd119_p1.json")) as f:
    d = json.load(f)
for row in d["response"]["data"][1:]:
    state_pop[row[0][-2:]] = (row[3], int(row[2]))
ISLAND_POP = {"60": 49710, "66": 153836, "69": 47329, "78": 87146}
ISLAND_NAME = {"60": "American Samoa", "66": "Guam",
               "69": "Commonwealth of the Northern Mariana Islands",
               "78": "United States Virgin Islands"}
for fp, pop in ISLAND_POP.items():
    state_pop.setdefault(fp, (ISLAND_NAME[fp], pop))

# --- CRS transforms ---------------------------------------------------------
src = osr.SpatialReference(); src.ImportFromEPSG(4269)
src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)  # lon,lat as stored
alb = osr.SpatialReference(); alb.ImportFromEPSG(5070)
alb.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
to_alb = osr.CoordinateTransformation(src, alb)
to_lonlat = osr.CoordinateTransformation(alb, src)

def centroid_lonlat(geom):
    g = geom.Clone()
    g.Transform(to_alb)
    c = g.Centroid()
    c.Transform(to_lonlat)
    return round(c.GetX(), 5), round(c.GetY(), 5)

def read_shp(path):
    ds = ogr.Open(path)
    lyr = ds.GetLayer(0)
    rows = []
    for f in lyr:
        rows.append((dict(f.items()), f.GetGeometryRef().Clone()))
    ds = None
    return rows

# --- districts ---------------------------------------------------------------
cd_rows = read_shp(os.path.join(RAW, "cd119_5m/cb_2024_us_cd119_5m.shp"))
voting_seats = {}
for props, _ in cd_rows:
    if props["CD119FP"] != "98":
        voting_seats[props["STATEFP"]] = voting_seats.get(props["STATEFP"], 0) + 1
print("voting seats total:", sum(voting_seats.values()))

state_abbr = {}
st_rows = read_shp(os.path.join(RAW, "state_5m/cb_2024_us_state_5m.shp"))
for props, _ in st_rows:
    state_abbr[props["STATEFP"]] = props["STUSPS"]

districts = []
for props, geom in cd_rows:
    sfp, cdfp, geoid = props["STATEFP"], props["CD119FP"], props["GEOID"]
    lon, lat = centroid_lonlat(geom)
    seats = voting_seats.get(sfp, 0)
    state_name, state_p = state_pop[sfp]
    ideal = round(state_p / seats) if seats else None
    districts.append({
        "geoid": geoid, "state_fp": sfp, "state": state_abbr[sfp],
        "cd": cdfp, "name": props["NAMELSAD"],
        "is_delegate": 1 if cdfp == "98" else 0,
        "is_at_large": 1 if cdfp == "00" else 0,
        "population": cd_pop[geoid],
        "population_ideal": ideal,
        "population_source": ("2020 Island Areas Censuses" if sfp in ISLAND_POP
                              else "2020 Census CD119 P1"),
        "aland_sqkm": round(props["ALAND"] / 1e6, 2),
        "awater_sqkm": round(props["AWATER"] / 1e6, 2),
        "centroid_lon": lon, "centroid_lat": lat,
    })
districts.sort(key=lambda r: r["geoid"])
with open(os.path.join(BASE, "districts.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(districts[0].keys()))
    w.writeheader(); w.writerows(districts)

# --- states ------------------------------------------------------------------
states = []
for props, geom in st_rows:
    sfp = props["STATEFP"]
    lon, lat = centroid_lonlat(geom)
    name, pop = state_pop[sfp]
    states.append({
        "geoid": props["GEOID"], "state_fp": sfp, "state": props["STUSPS"],
        "name": props["NAME"],
        "population": pop,
        "population_source": ("2020 Island Areas Censuses" if sfp in ISLAND_POP
                              else "2020 Census CD119 P1"),
        "voting_seats": voting_seats.get(sfp, 0),
        "districts_total": sum(1 for d in districts if d["state_fp"] == sfp),
        "aland_sqkm": round(props["ALAND"] / 1e6, 2),
        "awater_sqkm": round(props["AWATER"] / 1e6, 2),
        "centroid_lon": lon, "centroid_lat": lat,
    })
states.sort(key=lambda r: r["geoid"])
with open(os.path.join(BASE, "states.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(states[0].keys()))
    w.writeheader(); w.writerows(states)

# --- stats -------------------------------------------------------------------
def stats(vals):
    return {"n": len(vals), "min": min(vals), "max": max(vals),
            "mean": round(statistics.mean(vals), 1),
            "median": statistics.median(vals),
            "stdev": round(statistics.pstdev(vals), 1),
            "sum": sum(vals), "max_min_ratio": round(max(vals) / min(vals), 2)}

voting = [d["population"] for d in districts if not d["is_delegate"]]
all_cd = [d["population"] for d in districts]
states50 = [s["population"] for s in states if s["state_fp"] not in ("11", "72", "60", "66", "69", "78")]
all56 = [s["population"] for s in states]
out = {
    "states_50": stats(states50),
    "states_56_incl_DC_PR_IA": stats(all56),
    "districts_voting_435": stats(voting),
    "districts_all_441": stats(all_cd),
    "state_min": min(states, key=lambda s: s["population"])["name"],
    "state_max": max(states, key=lambda s: s["population"])["name"],
    "district_voting_min": min((d for d in districts if not d["is_delegate"]),
                               key=lambda d: d["population"]),
    "district_voting_max": max((d for d in districts if not d["is_delegate"]),
                               key=lambda d: d["population"]),
    "district_ideal_vs_actual_max_abs_diff": max(
        abs(d["population"] - d["population_ideal"]) for d in districts
        if d["population_ideal"] is not None),
}
# smallest/largest states among 50 for the CA/WY claim
s50 = sorted([s for s in states if s["state_fp"] not in ("11", "72", "60", "66", "69", "78")],
             key=lambda s: s["population"])
out["state_50_min"] = (s50[0]["name"], s50[0]["population"])
out["state_50_max"] = (s50[-1]["name"], s50[-1]["population"])
out["state_50_max_min_ratio"] = round(s50[-1]["population"] / s50[0]["population"], 1)
json.dump(out, open(os.path.join(BASE, "stats.json"), "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
# sanity: district pops should sum to 50-state resident + DC + PR (CD119 universe)
print("sum voting districts:", sum(voting))
print("sum 50-state resident pops:", sum(states50))
print("sum all 441 districts:", sum(all_cd))
print("AK centroid check:", [ (s["name"], s["centroid_lon"], s["centroid_lat"]) for s in states if s["state"]=="AK"])
print("HI centroid check:", [ (s["name"], s["centroid_lon"], s["centroid_lat"]) for s in states if s["state"]=="HI"])
