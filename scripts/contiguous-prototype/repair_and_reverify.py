"""Repair the single self-intersection in the delivered lon/lat file and re-verify.

The raw go-cart-wasm output has one invalid geometry: Alaska, a single
self-intersection pinch at EPSG:5070 (-1892420, -637120) — the same defect
class the earlier C run found in its output. Repair with shapely
make_valid (area change -0.0000217%, negligible), exactly as the C run
did, and record the repair. The raw projected output in
contiguous_states_2020_gocart_5070.geojson is left untouched as the
verbatim library output.

Then re-verify the repaired lon/lat file: validity, area error
(re-projected to EPSG:5070), and adjacency vs the projected input.
"""
import csv, json
from shapely.geometry import shape, mapping
from shapely import make_valid
from shapely.ops import transform as shp_transform
from pyproj import Transformer

BASE = "/home/hatch/workspace/cartogram-census"
PROTO = BASE + "/contiguous-prototype"
PATH = f"{BASE}/contiguous_states_2020_gocart.geojson"

pop = {}
with open(f"{BASE}/states.csv") as f:
    for row in csv.DictReader(f):
        pop[row["state"]] = int(row["population"])

with open(PATH) as f:
    data = json.load(f)

for feat in data["features"]:
    g = shape(feat["geometry"])
    if not g.is_valid:
        gv = make_valid(g)
        print(f"repair {feat['properties']['STUSPS']}: {g.geom_type} -> {gv.geom_type}, "
              f"area delta {(gv.area - g.area) / g.area * 100:+.6f}%")
        feat["geometry"] = mapping(gv)

with open(PATH, "w") as f:
    json.dump(data, f)
print(f"rewrote {PATH}")

# --- re-verify the repaired file ---
tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
geoms = {}
for feat in data["features"]:
    g = shape(feat["geometry"])
    geoms[feat["properties"]["STUSPS"]] = shp_transform(
        lambda x, y, z=None: tr.transform(x, y), g)

print(f"states: {len(geoms)}  all valid: {all(g.is_valid for g in geoms.values())}")
total_pop = sum(pop[a] for a in geoms)
total_area = sum(g.area for g in geoms.values())
errs = {a: ((g.area / total_area) - (pop[a] / total_pop)) / (pop[a] / total_pop)
        for a, g in geoms.items()}
mean_abs = sum(abs(e) for e in errs.values()) / len(errs)
worst = sorted(errs.items(), key=lambda kv: -abs(kv[1]))[:3]
print(f"repaired mean abs area error: {mean_abs * 100:.3f}%")
print("worst:", [(a, f"{e * 100:+.2f}%") for a, e in worst])

with open(f"{PROTO}/states50_5070.geojson") as f:
    inp = {ft["properties"]["STUSPS"]: shape(ft["geometry"])
           for ft in json.load(f)["features"]}

def adjacencies(d):
    items = sorted(d.items())
    adj = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][1].touches(items[j][1]) or items[i][1].intersects(items[j][1]):
                adj.add((items[i][0], items[j][0]))
    return adj

a_in, a_out = adjacencies(inp), adjacencies(geoms)
print(f"adjacencies: true {len(a_in)}  repaired {len(a_out)}  "
      f"preserved {len(a_in & a_out)}  lost {len(a_in - a_out)}  gained {len(a_out - a_in)}")
