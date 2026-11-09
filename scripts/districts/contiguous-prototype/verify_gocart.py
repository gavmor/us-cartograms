"""Independently verify the go-cart-wasm districts cartogram.

Measures, all from the written files (not the solver's log):
- per-district area share vs 2020 Census CD119 P1 population share
  (projected EPSG:5070 output, areas in m^2): relative error, mean
  absolute error, worst district, Pearson r between the two shares,
  area ratio max-pop district / min-pop district.
- the program's own per-region `area_error` property (same quantity,
  as reported by go-cart itself) — mean abs, max.
- geometry validity (shapely is_valid — covers self-intersections),
  435-district completeness, properties preserved.
- adjacency preservation vs the projected input (touches-or-intersects
  definition, as in the states prototype), with spot checks: within-state
  pairs (CA-01/CA-02, NY-01/NY-02, TX-01/TX-02) and state-border pairs
  (CA-01/OR-02, TX-01/OK-02, NY-01/NJ-03 is NOT adjacent — negative check).
- lon/lat round-trip: re-project contiguous_districts_2020_gocart.geojson
  to EPSG:5070 and re-measure the mean abs error.

Writes error_table.csv (per-district) and contiguous_verification.json.
"""
import csv, json, math
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

BASE = "/home/hatch/workspace/cartogram-census"
D = BASE + "/districts"

pop = {}
with open(f"{BASE}/districts.csv") as f:
    for row in csv.DictReader(f):
        if row["is_delegate"] == "0":
            pop[row["geoid"]] = int(row["population"])
assert len(pop) == 435 and sum(pop.values()) == 330759736

def load(path):
    with open(path) as f:
        d = json.load(f)
    return {ft["properties"]["geoid"]: (shape(ft["geometry"]), ft["properties"])
            for ft in d["features"]}

def errors(geoms):
    total_pop = sum(pop[g] for g in geoms)
    total_area = sum(g.area for g, _ in geoms.values())
    return {g: ((geom.area / total_area) - (pop[g] / total_pop)) / (pop[g] / total_pop)
            for g, (geom, _) in geoms.items()}

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

w = load(f"{D}/contiguous_districts_2020_gocart_5070.geojson")
inp = load(f"{D}/districts_5070.geojson")
print(f"WASM output districts: {len(w)}  input districts: {len(inp)}  same set: {set(w) == set(inp)}")
print(f"props preserved (geoid/state/cd/name/population): "
      f"{all(w[g][1].get('population') == pop[g] for g in w)}")
print(f"program area_error present on all: {all('area_error' in w[g][1] for g in w)}")

errs = errors(w)
mean_abs = sum(abs(e) for e in errs.values()) / len(errs)
worst = sorted(errs.items(), key=lambda kv: -abs(kv[1]))[:10]
print(f"mean abs relative area error (re-measured): {mean_abs * 100:.3f}%")
print("worst districts:")
for g, e in worst:
    p = w[g][1]
    print(f"  {p['state']}-{p['cd']} ({g}): {e * 100:+.2f}%  (pop {pop[g]:,})")
xs = [w[g][0].area / sum(gg.area for gg, _ in w.values()) for g in sorted(w)]
ys = [pop[g] / sum(pop.values()) for g in sorted(w)]
r = pearson(xs, ys)
print(f"Pearson r (area share vs pop share): {r:.6f}")
own = [w[g][1]["area_error"] for g in w]
print(f"program's own area_error: mean abs {sum(abs(v) for v in own) / len(own) * 100:.3f}%  "
      f"max abs {max(abs(v) for v in own) * 100:.3f}%")
# area ratio: max-pop district (DE at-large, 989948) vs min-pop (MT-01, 542112)
g_max = max(pop, key=pop.get); g_min = min(pop, key=pop.get)
print(f"max/min-pop area ratio: {w[g_max][0].area / w[g_min][0].area:.3f} "
      f"(population ratio {pop[g_max] / pop[g_min]:.3f}; {g_max} vs {g_min})")
print(f"largest/smallest cartogram area ratio overall: "
      f"{max(g.area for g, _ in w.values()) / min(g.area for g, _ in w.values()):.3f}")

invalid = [g for g, (geom, _) in w.items() if not geom.is_valid]
print(f"invalid geometries: {len(invalid)} {invalid}")
for g in invalid:
    from shapely.validation import explain_validity
    print(f"  {g}: {explain_validity(w[g][0])}")

a_in, a_out = adjacencies(inp), adjacencies(w)
print(f"true adjacencies: {len(a_in)}  cartogram adjacencies: {len(a_out)}  "
      f"preserved: {len(a_in & a_out)}  lost: {len(a_in - a_out)}  gained: {len(a_out - a_in)}")
if a_in - a_out:
    print("  lost:", sorted(a_in - a_out)[:20], "..." if len(a_in - a_out) > 20 else "")
if a_out - a_in:
    print("  gained:", sorted(a_out - a_in)[:20], "..." if len(a_out - a_in) > 20 else "")
for pair in [("0601", "0602"), ("3601", "3602"), ("4801", "4804"), ("0601", "4102"),
             ("4801", "0504"), ("3601", "3403")]:
    p = tuple(sorted(pair))
    print(f"  spot {pair}: in input {p in a_in}, in cartogram {p in a_out}")

# lon/lat round-trip
tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
ll = load(f"{D}/contiguous_districts_2020_gocart.geojson")
print(f"lon/lat file districts: {len(ll)}  same set: {set(ll) == set(w)}")
rt = {g: (shp_transform(lambda x, y, z=None: tr.transform(x, y), geom), p)
      for g, (geom, p) in ll.items()}
rt_errs = errors(rt)
rt_mean = sum(abs(e) for e in rt_errs.values()) / len(rt_errs)
print(f"lon/lat round-trip mean abs error: {rt_mean * 100:.3f}% "
      f"(vs {mean_abs * 100:.3f}% projected; delta {(rt_mean - mean_abs) * 100:+.4f} pp)")

# --- write error_table.csv ---
total_area = sum(g.area for g, _ in w.values())
total_pop = sum(pop.values())
with open(f"{D}/error_table.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["geoid", "state", "cd", "name", "population",
                 "area_share_pct", "pop_share_pct", "rel_error_pct",
                 "program_area_error_pct"])
    for g in sorted(w):
        geom, p = w[g]
        wr.writerow([g, p["state"], p["cd"], p["name"], pop[g],
                     f"{geom.area / total_area * 100:.6f}",
                     f"{pop[g] / total_pop * 100:.6f}",
                     f"{errs[g] * 100:+.4f}",
                     f"{p['area_error'] * 100:+.4f}"])
print(f"wrote {D}/error_table.csv")

# --- write contiguous_verification.json ---
worst_g, worst_e = worst[0]
ver = {
    "regions": len(w),
    "population_total": total_pop,
    "mean_abs_rel_area_error_pct": round(mean_abs * 100, 4),
    "worst_district": {
        "geoid": worst_g, "state": w[worst_g][1]["state"], "cd": w[worst_g][1]["cd"],
        "population": pop[worst_g], "rel_error_pct": round(worst_e * 100, 4),
    },
    "top10_worst": [{"geoid": g, "state": w[g][1]["state"], "cd": w[g][1]["cd"],
                     "population": pop[g], "rel_error_pct": round(e * 100, 4)}
                    for g, e in worst],
    "pearson_r_area_share_vs_pop_share": round(r, 6),
    "program_area_error_mean_abs_pct": round(sum(abs(v) for v in own) / len(own) * 100, 4),
    "program_area_error_max_abs_pct": round(max(abs(v) for v in own) * 100, 4),
    "max_min_pop_area_ratio": round(w[g_max][0].area / w[g_min][0].area, 3),
    "max_min_pop_ratio": round(pop[g_max] / pop[g_min], 3),
    "max_min_pop_districts": [g_max, g_min],
    "largest_smallest_area_ratio": round(max(g.area for g, _ in w.values()) / min(g.area for g, _ in w.values()), 3),
    "invalid_geometries": invalid,
    "all_properties_preserved": all(w[g][1].get("population") == pop[g] for g in w),
    "adjacencies": {
        "input": len(a_in), "cartogram": len(a_out),
        "preserved": len(a_in & a_out), "lost": len(a_in - a_out),
        "gained": len(a_out - a_in),
        "lost_pairs": sorted(a_in - a_out), "gained_pairs": sorted(a_out - a_in),
    },
    "spot_checks": {
        "CA-01/CA-02": tuple(sorted(("0601", "0602"))) in a_out,
        "NY-01/NY-02": tuple(sorted(("3601", "3602"))) in a_out,
        "TX-01/TX-04": tuple(sorted(("4801", "4804"))) in a_out,
        "CA-01/OR-02 (state border)": tuple(sorted(("0601", "4102"))) in a_out,
        "TX-01/AR-04 (state border)": tuple(sorted(("4801", "0504"))) in a_out,
        "NY-01/NJ-03 (not adjacent)": tuple(sorted(("3601", "3403"))) not in a_out,
    },
    "lonlat_roundtrip_mean_abs_error_pct": round(rt_mean * 100, 4),
    "lonlat_roundtrip_delta_pp": round((rt_mean - mean_abs) * 100, 4),
}
with open(f"{D}/contiguous_verification.json", "w") as f:
    json.dump(ver, f, indent=2)
print(f"wrote {D}/contiguous_verification.json")
