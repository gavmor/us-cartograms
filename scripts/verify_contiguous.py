"""Verify a contiguous cartogram GeoJSON against 2020 Census P1 populations:
per-state distorted-area share vs population share, mean/max abs relative
error, and adjacency preservation vs the undistorted input geometries.
Usage: verify_contiguous.py <cartogram.geojson> <input.geojson>
"""
import csv, json, sys
from shapely.geometry import shape

carto_path, input_path = sys.argv[1], sys.argv[2]
pop = {}
with open("/home/hatch/workspace/cartogram-census/states.csv") as f:
    for row in csv.DictReader(f):
        pop[row["state"]] = int(row["population"])

def load(path):
    with open(path) as f:
        d = json.load(f)
    return {ft["properties"]["STUSPS"]: shape(ft["geometry"]) for ft in d["features"]}

carto, orig = load(carto_path), load(input_path)
assert set(carto) == set(orig), (set(carto) ^ set(orig))
total_pop = sum(pop[a] for a in carto)
total_area = sum(g.area for g in carto.values())
errs = {}
for a, g in carto.items():
    area_share = g.area / total_area
    pop_share = pop[a] / total_pop
    errs[a] = (area_share - pop_share) / pop_share
mean_err = sum(abs(e) for e in errs.values()) / len(errs)
worst = sorted(errs.items(), key=lambda kv: -abs(kv[1]))[:6]
print(f"states: {len(carto)}  total cartogram area: {total_area:.3g} m^2")
print(f"mean abs relative area error: {mean_err*100:.2f}%")
print("worst states (area share vs pop share):")
for a, e in worst:
    print(f"  {a}: {e*100:+.1f}%  (pop {pop[a]:,})")
# adjacency: two states adjacent if polygons touch (incl. point touch)
def adjacencies(geoms):
    items = list(geoms.items())
    adj = set()
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i][1].touches(items[j][1]) or items[i][1].intersects(items[j][1]):
                adj.add((items[i][0], items[j][0]))
    return adj
a_orig, a_cart = adjacencies(orig), adjacencies(carto)
print(f"true adjacencies: {len(a_orig)}  cartogram adjacencies: {len(a_cart)}  "
      f"preserved: {len(a_orig & a_cart)}  lost: {len(a_orig - a_cart)}  gained: {len(a_cart - a_orig)}")
if a_orig - a_cart:
    print("lost:", sorted(a_orig - a_cart))
