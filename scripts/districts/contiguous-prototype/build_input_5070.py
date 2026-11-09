"""Reproject the 435 voting US congressional districts to EPSG:5070 for
the go-cart-wasm districts cartogram.

Same pipeline as the states prototype
(~/workspace/cartogram-census/contiguous-prototype/build_input_5070.py):
- EPSG:4269 lon/lat (2024 CBF 1:5m, cd119_5m.geojson) -> EPSG:5070
  NAD83/Conus Albers (metres, equal-area; required by go-cart — never
  feed lon/lat to go-cart).
- Populations: 2020 Census CD119 P1 from ../districts.csv; only the 435
  with is_delegate=0 (voting). Excluded delegates: DC 689545, AS 49710,
  GU 153836, MP 47329, PR 3285874, VI 87146 (total pop 330,759,736).
- AK/HI decision (option a, same as states): the 48 CONUS states'
  districts keep true EPSG:5070 positions; Alaska at-large is scaled
  0.35 about its centroid and moved to a bottom-left inset; Hawaii's 2
  districts are moved together to an inset below CONUS (same offsets as
  the states build: AK centroid -> (xmin+350000, ymin-550000),
  HI combined centroid -> (xmin+1500000, ymin-550000), where xmin/ymin
  are the CONUS bbox minima). AK/HI are therefore NOT at true
  geographic coordinates in any output file — render with an
  identity/fit projection, not Albers USA.
"""
import csv, json
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform, unary_union
from shapely.affinity import scale, translate
from pyproj import Transformer

BASE = "/home/hatch/workspace/cartogram-census"
SRC = f"{BASE}/cd119_5m.geojson"
CSV = f"{BASE}/districts.csv"
OUT = f"{BASE}/districts/districts_5070.geojson"

pop = {}
meta = {}
with open(CSV) as f:
    for row in csv.DictReader(f):
        if row["is_delegate"] == "0":
            pop[row["geoid"]] = int(row["population"])
            meta[row["geoid"]] = row
assert len(pop) == 435, len(pop)
assert sum(pop.values()) == 330759736, sum(pop.values())

tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
def project(geom):
    return shp_transform(lambda x, y, z=None: tr.transform(x, y), geom)

with open(SRC) as f:
    data = json.load(f)

feats = []  # (geoid, state, cd, geom5070)
for feat in data["features"]:
    geoid = feat["properties"]["GEOID"]
    if geoid not in pop:
        continue  # delegate (DC/AS/GU/MP/PR/VI)
    g = project(shape(feat["geometry"]))
    feats.append((geoid, meta[geoid]["state"], meta[geoid]["cd"], g))
assert len(feats) == 435, len(feats)

# CONUS bbox (48 states' districts only; AK=02, HI=15 excluded)
xs, ys = [], []
for geoid, state, cd, g in feats:
    if state in ("AK", "HI"):
        continue
    b = g.bounds
    xs += [b[0], b[2]]; ys += [b[1], b[3]]
xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
print(f"CONUS bbox x {xmin:.0f}..{xmax:.0f}  y {ymin:.0f}..{ymax:.0f}")

# Hawaii inset translation, from the combined HI geometry centroid
hi_union = unary_union([g for geoid, state, cd, g in feats if state == "HI"])
hi_c = hi_union.centroid
hi_dx = (xmin + 1500000) - hi_c.x
hi_dy = (ymin - 550000) - hi_c.y
print(f"HI combined centroid 5070: ({hi_c.x:.0f}, {hi_c.y:.0f}) -> translate ({hi_dx:.0f}, {hi_dy:.0f})")

out_feats = []
for geoid, state, cd, g in feats:
    if state == "AK":
        c = g.centroid
        g = scale(g, xfact=0.35, yfact=0.35, origin=c)
        c2 = g.centroid
        g = translate(g, xoff=(xmin + 350000) - c2.x, yoff=(ymin - 550000) - c2.y)
        print(f"AK scaled 0.35 about centroid ({c.x:.0f}, {c.y:.0f}); "
              f"inset centroid 5070: ({(xmin + 350000):.0f}, {(ymin - 550000):.0f})")
    elif state == "HI":
        g = translate(g, xoff=hi_dx, yoff=hi_dy)
    out_feats.append({
        "type": "Feature",
        "properties": {
            "geoid": geoid, "state": state, "cd": cd,
            "name": meta[geoid]["name"],
            "is_at_large": int(meta[geoid]["is_at_large"]),
            "population": pop[geoid],
        },
        "geometry": mapping(g),
    })

out = {"type": "FeatureCollection", "features": out_feats}
with open(OUT, "w") as f:
    json.dump(out, f)
print(f"wrote {OUT}: {len(out_feats)} features")
print(f"population total: {sum(pop.values()):,}  min {min(pop.values()):,}  max {max(pop.values()):,}")
# input validity check
bad = [ft["properties"]["geoid"] for ft in out_feats
       if not shape(ft["geometry"]).is_valid]
print(f"invalid input geometries: {len(bad)} {bad}")
