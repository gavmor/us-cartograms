"""Independently verify the go-cart-wasm cartogram (projected EPSG:5070 output).

Measures, all from the written files (not the solver's log):
- per-state area share vs 2020 Census P1 population share: relative error,
  mean absolute error, worst state, Pearson r between the two shares.
- the program's own per-region `area_error` property (same quantity, as
  reported by go-cart itself) — mean abs, max.
- geometry validity (shapely is_valid — covers self-intersections), 50-state
  completeness, properties preserved.
- adjacency preservation vs the projected input (touches-or-intersects
  definition, as in ../verify_contiguous.py), with spot checks CA/NV/AZ
  and NY/PA/NJ.
- comparison of area shares vs the earlier C-run
  (../contiguous_states_2020.geojson, normalized space — shares comparable).
- lon/lat round-trip: re-project ../contiguous_states_2020_gocart.geojson
  to EPSG:5070 and re-measure the mean abs error.

Usage: python verify_gocart.py
"""
import csv, json, math
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

BASE = "/home/hatch/workspace/cartogram-census"
PROTO = BASE + "/contiguous-prototype"
pop = {}
with open(f"{BASE}/states.csv") as f:
    for row in csv.DictReader(f):
        pop[row["state"]] = int(row["population"])

def load(path):
    with open(path) as f:
        d = json.load(f)
    return {ft["properties"]["STUSPS"]: (shape(ft["geometry"]), ft["properties"])
            for ft in d["features"]}

def errors(geoms):
    total_pop = sum(pop[a] for a in geoms)
    total_area = sum(g.area for g, _ in geoms.values())
    errs = {}
    for a, (g, _) in geoms.items():
        errs[a] = ((g.area / total_area) - (pop[a] / total_pop)) / (pop[a] / total_pop)
    return errs

def pearson(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
    return cov / math.sqrt(vx * vy)

def adjacencies(geoms):
    items = sorted(geoms.items())
    adj = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            g1 = items[i][1][0]; g2 = items[j][1][0]
            if g1.touches(g2) or g1.intersects(g2):
                adj.add((items[i][0], items[j][0]))
    return adj

# --- 1. projected WASM output ---
w = load(f"{PROTO}/contiguous_states_2020_gocart_5070.geojson")
inp = load(f"{PROTO}/states50_5070.geojson")
print(f"WASM output states: {len(w)}  input states: {len(inp)}  same set: {set(w) == set(inp)}")
print(f"props preserved (STUSPS/NAME/population): "
      f"{all(w[s][1].get('population') == pop[s] for s in w)}")
print(f"program area_error present on all: {all('area_error' in w[s][1] for s in w)}")

errs = errors(w)
mean_abs = sum(abs(e) for e in errs.values()) / len(errs)
worst = sorted(errs.items(), key=lambda kv: -abs(kv[1]))[:6]
print(f"mean abs relative area error (re-measured): {mean_abs * 100:.3f}%")
print("worst states:")
for a, e in worst:
    print(f"  {a}: {e * 100:+.2f}%  (pop {pop[a]:,})")
xs = [w[a][0].area / sum(g.area for g, _ in w.values()) for a in sorted(w)]
ys = [pop[a] / sum(pop[a] for a in w) for a in sorted(w)]
print(f"Pearson r (area share vs pop share): {pearson(xs, ys):.6f}")
own = [w[s][1]["area_error"] for s in w]
print(f"program's own area_error: mean abs {sum(abs(v) for v in own) / len(own) * 100:.3f}%  "
      f"max abs {max(abs(v) for v in own) * 100:.3f}%")
ca_wy = (w["CA"][0].area / w["WY"][0].area)
print(f"CA/WY area ratio: {ca_wy:.2f} (population ratio 68.54)")

# --- 2. validity ---
invalid = [s for s, (g, _) in w.items() if not g.is_valid]
print(f"invalid geometries: {len(invalid)} {invalid}")

# --- 3. adjacency ---
a_in, a_out = adjacencies(inp), adjacencies(w)
print(f"true adjacencies: {len(a_in)}  cartogram adjacencies: {len(a_out)}  "
      f"preserved: {len(a_in & a_out)}  lost: {len(a_in - a_out)}  gained: {len(a_out - a_in)}")
if a_in - a_out:
    print("  lost:", sorted(a_in - a_out))
if a_out - a_in:
    print("  gained:", sorted(a_out - a_in))
for pair in [("CA", "NV"), ("CA", "AZ"), ("NV", "AZ"), ("NY", "PA"), ("NY", "NJ"), ("PA", "NJ")]:
    p = tuple(sorted(pair))
    print(f"  spot {pair}: in input {p in a_in}, in cartogram {p in a_out}")

# --- 4. vs the earlier C run (area shares only) ---
c = load(f"{BASE}/contiguous_states_2020.geojson")
c_errs = errors(c)
c_mean = sum(abs(e) for e in c_errs.values()) / len(c_errs)
print(f"C-run mean abs error (re-measured here): {c_mean * 100:.3f}%")
diffs = {a: abs((w[a][0].area / sum(g.area for g, _ in w.values()))
                - (c[a][0].area / sum(g.area for g, _ in c.values()))) for a in w}
print(f"max |WASM area share - C area share|: {max(diffs.values()) * 100:.3f} pp "
      f"({max(diffs, key=diffs.get)})")

# --- 5. lon/lat round-trip ---
tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
ll = load(f"{BASE}/contiguous_states_2020_gocart.geojson")
print(f"lon/lat file states: {len(ll)}  same set: {set(ll) == set(w)}")
rt = {s: (shp_transform(lambda x, y, z=None: tr.transform(x, y), g), p)
      for s, (g, p) in ll.items()}
rt_errs = errors(rt)
rt_mean = sum(abs(e) for e in rt_errs.values()) / len(rt_errs)
print(f"lon/lat round-trip mean abs error: {rt_mean * 100:.3f}% "
      f"(vs {mean_abs * 100:.3f}% projected; delta {(rt_mean - mean_abs) * 100:+.4f} pp)")
