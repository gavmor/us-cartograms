#!/usr/bin/env python3
"""Tile-grid (mosaic) layout for the 435 voting US congressional districts
(119th Congress), one equal tile per district.

Method
------
1. Geometric centroid of each district polygon from cd119_5m.geojson
   (shapely), projected to EPSG:5070 (km). Cross-checked against the
   centroid_lon/lat columns in districts.csv.
2. Rectangular grid over the CONUS landmask (48 states + DC from
   states_5m.geojson, unioned, EPSG:5070). Cell size 132 km: the CONUS
   land area is 7,809,227 km^2, so sqrt(area / 432) = 134.4 km per tile
   if tiles filled the land exactly; 132 km is the nearest round size
   below that which still yields >= 432 candidate cells whose centres
   fall inside the landmask (446 candidates, 14 spare). Origin = NW
   corner of the landmask bbox; grid_col 0 = west, grid_row 0 = north.
3. Assignment: scipy linear_sum_assignment (Hungarian) minimising TOTAL
   displacement, i.e. sum of Euclidean distances (km) from each district
   centroid to its assigned cell centre. AK + HI (3 districts) are NOT
   in the CONUS assignment: they are inset cells below the main grid,
   Albers-USA style (row 23, with row 22 left blank as a separator).
4. Sensitivity variant: the same grid solved with SQUARED-distance cost
   (tilegrid_districts_squared.csv). Linear cost minimises the total but
   concentrates displacement on a few exiled districts (max ~3,250 km);
   squared cost spreads it (max ~1,340 km) and nearly doubles adjacency
   preservation, at +5% total displacement. See tilegrid_notes.md.

No published grid was used: the only published House-district tilegram
found is the Daily Kos hexmap (DKOS_CD_Hexmap_v1.1, via Pitch
Interactive tilegrams / tilegramsR) -- hexagonal, not a square grid,
and 2018 vintage, so it cannot supply CD119 square-grid coordinates.
This layout is computed from scratch from CD119 geometry.

Usage: ~/workspace/.venvs/gis/bin/python compute_tilegrid_districts.py
Outputs (in this directory): tilegrid_districts.csv,
tilegrid_districts_squared.csv, tilegrid_verification.json,
tilegrid_notes.md (notes file is written by hand, not by this script).
"""
import csv
import json
import math
import warnings
from collections import defaultdict, deque

import numpy as np
from pyproj import Transformer
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, shape
from shapely.ops import transform as shp_transform
from shapely.ops import unary_union
from shapely.strtree import STRtree

warnings.filterwarnings("ignore")

BASE = "/home/hatch/workspace/cartogram-census"
OUT = f"{BASE}/districts"
CELL_KM = 132.0
# Inset cells (grid_col, grid_row); main grid rows are 0..21, row 22 blank.
INSETS = {"0200": (2, 23), "1501": (8, 23), "1502": (9, 23)}
CONUS_STATE_FPS = {
    "01", "04", "05", "06", "08", "09", "10", "11", "12", "13", "16", "17",
    "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41",
    "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55",
    "56",
}  # 48 CONUS states + DC


def load_districts():
    with open(f"{BASE}/districts.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    voting = [r for r in rows if r["is_delegate"] == "0"]
    delegates = [r for r in rows if r["is_delegate"] == "1"]
    assert len(rows) == 441 and len(voting) == 435 and len(delegates) == 6
    assert {r["geoid"] for r in delegates} == {
        "1198", "6098", "6698", "6998", "7298", "7898"}, delegates
    return voting


def main():
    voting = load_districts()
    by_geoid = {r["geoid"]: r for r in voting}
    conus = [r for r in voting if r["state"] not in ("AK", "HI")]
    insets = [r for r in voting if r["state"] in ("AK", "HI")]
    assert len(conus) == 432 and len(insets) == 3

    with open(f"{BASE}/cd119_5m.geojson") as f:
        gj = json.load(f)
    geoms = {ft["properties"]["GEOID"]: shape(ft["geometry"])
             for ft in gj["features"]}
    assert set(geoms) == {r["geoid"] for r in
                          list(csv.DictReader(open(f"{BASE}/districts.csv")))}
    tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)

    # ---- 1. centroids + cross-check vs districts.csv -------------------
    cent_ll, cent_km = {}, {}
    for r in voting:
        c = geoms[r["geoid"]].centroid
        cent_ll[r["geoid"]] = (c.x, c.y)
        x, y = tr.transform(c.x, c.y)
        cent_km[r["geoid"]] = (x / 1000.0, y / 1000.0)
    diffs, diffs_conus = [], []
    for r in voting:
        x1, y1 = tr.transform(cent_ll[r["geoid"]][0], cent_ll[r["geoid"]][1])
        x2, y2 = tr.transform(float(r["centroid_lon"]), float(r["centroid_lat"]))
        d = math.hypot(x1 - x2, y1 - y2) / 1000.0
        diffs.append((d, r["geoid"]))
        if r["state"] not in ("AK", "HI"):
            diffs_conus.append((d, r["geoid"]))
    diffs.sort(reverse=True)
    diffs_conus.sort(reverse=True)
    centroid_check = {
        "all_435": {
            "mean_km": float(np.mean([d for d, _ in diffs])),
            "median_km": float(np.median([d for d, _ in diffs])),
            "max_km": float(diffs[0][0]), "max_geoid": diffs[0][1],
            "n_over_10km": int(sum(1 for d, _ in diffs if d > 10)),
        },
        "conus_432": {
            "mean_km": float(np.mean([d for d, _ in diffs_conus])),
            "median_km": float(np.median([d for d, _ in diffs_conus])),
            "max_km": float(diffs_conus[0][0]), "max_geoid": diffs_conus[0][1],
            "worst_5": [[g, round(d, 2)] for d, g in diffs_conus[:5]],
        },
    }
    print("centroid cross-check:", json.dumps(centroid_check, indent=1))

    # ---- 2. CONUS landmask grid ----------------------------------------
    with open(f"{BASE}/states_5m.geojson") as f:
        sj = json.load(f)
    union = unary_union([shape(ft["geometry"]) for ft in sj["features"]
                         if ft["properties"]["GEOID"] in CONUS_STATE_FPS])
    union5070 = shp_transform(tr.transform, union)
    xmin, ymin, xmax, ymax = [v / 1000.0 for v in union5070.bounds]
    land_km2 = union5070.area / 1e6
    s = CELL_KM
    nx = int(math.ceil((xmax - xmin) / s))
    ny = int(math.ceil((ymax - ymin) / s))
    cells = []  # (col, row, cx_km, cy_km), row 0 = north
    for j in range(ny):
        cy = ymax - (j + 0.5) * s
        for i in range(nx):
            cx = xmin + (i + 0.5) * s
            if union5070.contains(Point(cx * 1000.0, cy * 1000.0)):
                cells.append((i, j, cx, cy))
    print(f"landmask {land_km2:,.0f} km2, sqrt(area/432)={math.sqrt(land_km2/432):.1f} km; "
          f"grid {nx}x{ny}, candidate cells in mask: {len(cells)}")
    assert len(cells) >= 432

    pts = np.array([cent_km[r["geoid"]] for r in conus])
    cellxy = np.array([[c[2], c[3]] for c in cells])
    dist = np.hypot(pts[:, None, 0] - cellxy[None, :, 0],
                    pts[:, None, 1] - cellxy[None, :, 1])

    def solve(cost, label):
        ri, ci = linear_sum_assignment(cost)
        assert len(set(ci)) == 432
        assign = {conus[i]["geoid"]: cells[j] for i, j in zip(ri, ci)}
        d = dist[ri, ci]
        print(f"{label}: total={d.sum():,.0f} km mean={d.mean():.1f} "
              f"median={np.median(d):.1f} p90={np.percentile(d, 90):.0f} "
              f"max={d.max():.0f} ({conus[int(np.argmax(d))]['geoid']})")
        return assign, d

    assign_lin, d_lin = solve(dist, "linear-cost")
    assign_sq, d_sq = solve(dist ** 2, "squared-cost")

    # ---- 3. insets ------------------------------------------------------
    def grid_float(geoid):
        x, y = cent_km[geoid]
        return ((x - xmin) / s - 0.5, (ymax - y) / s - 0.5)

    inset_disp_units = {}
    for r in insets:
        col, row = INSETS[r["geoid"]]
        cf, rf = grid_float(r["geoid"])
        inset_disp_units[r["geoid"]] = float(math.hypot(cf - col, rf - row))
        print(f"inset {r['geoid']} {r['state']}-{r['cd']}: cell ({col},{row}), "
              f"extrapolated grid pos ({cf:.1f},{rf:.1f}), "
              f"displacement {inset_disp_units[r['geoid']]:.1f} grid units")

    def write_csv(path, assign):
        rows_out = []
        for r in voting:
            g = r["geoid"]
            if g in assign:
                col, row = assign[g][0], assign[g][1]
                inset = "FALSE"
            else:
                col, row = INSETS[g]
                inset = "TRUE"
            rows_out.append({"geoid": g, "state": r["state"], "cd": r["cd"],
                             "name": r["name"], "population": r["population"],
                             "grid_col": col, "grid_row": row, "inset": inset})
        rows_out.sort(key=lambda x: x["geoid"])
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["geoid", "state", "cd", "name",
                                              "population", "grid_col",
                                              "grid_row", "inset"])
            w.writeheader()
            w.writerows(rows_out)
        return rows_out

    write_csv(f"{OUT}/tilegrid_districts.csv", assign_lin)
    write_csv(f"{OUT}/tilegrid_districts_squared.csv", assign_sq)
    print("wrote tilegrid_districts.csv + tilegrid_districts_squared.csv")

    # ---- 4. verification, re-read from the written CSV ------------------
    with open(f"{OUT}/tilegrid_districts.csv", newline="") as f:
        got = list(csv.DictReader(f))
    pos = {(int(r["grid_col"]), int(r["grid_row"])): r["geoid"] for r in got}
    assert len(got) == 435 and len(pos) == 435
    assert {r["geoid"] for r in got} == set(by_geoid)
    assert all(r["geoid"] in by_geoid and
               by_geoid[r["geoid"]]["population"] == r["population"] for r in got)

    # displacement from the CSV (CONUS only; insets in grid units)
    disp = {}
    for r in got:
        if r["inset"] == "TRUE":
            continue
        g = r["geoid"]
        col, row = int(r["grid_col"]), int(r["grid_row"])
        cx = xmin + (col + 0.5) * s
        cy = ymax - (row + 0.5) * s
        x, y = cent_km[g]
        disp[g] = math.hypot(x - cx, y - cy)
    dvals = np.array(list(disp.values()))
    worst = sorted(disp.items(), key=lambda kv: -kv[1])[:10]
    # per-state mean displacement
    by_state = defaultdict(list)
    for r in got:
        if r["inset"] == "FALSE":
            by_state[r["state"]].append(disp[r["geoid"]])
    state_mean = sorted(((st, float(np.mean(v)), len(v))
                         for st, v in by_state.items()),
                        key=lambda t: -t[1])[:8]

    # true adjacencies: touches-or-intersects (as in states verify code)
    items = [(r["geoid"], geoms[r["geoid"]]) for r in voting]
    tree = STRtree([g for _, g in items])
    true_adj, true_border = set(), set()
    for i, (gid, g) in enumerate(items):
        for j in tree.query(g, predicate="intersects"):
            if j > i:
                pair = tuple(sorted((gid, items[j][0])))
                true_adj.add(pair)
                # shared border (not just a point touch): project to 5070
                gi = shp_transform(tr.transform, g)
                gjj = shp_transform(tr.transform, items[j][1])
                if gi.intersection(gjj).length > 1.0:  # > 1 m of shared border
                    true_border.add(pair)
    conus_true = {a for a in true_adj
                  if a[0] not in INSETS and a[1] not in INSETS}
    conus_true_border = {a for a in true_border
                         if a[0] not in INSETS and a[1] not in INSETS}

    def grid_adj_pairs(nbr):
        # Offsets are +1-only, so each unordered pair is visited exactly
        # once; do NOT filter on geoid order (that would drop ~half the
        # pairs -- each pair is only ever seen from one side here).
        out = set()
        for (c, r), g in pos.items():
            for dc, dr in nbr:
                h = pos.get((c + dc, r + dr))
                if h:
                    out.add(tuple(sorted((g, h))))
        return out

    adj4 = grid_adj_pairs([(1, 0), (0, 1)])
    adj8 = grid_adj_pairs([(1, 0), (0, 1), (1, 1), (1, -1)])
    kept4 = true_adj & adj4
    kept8 = true_adj & adj8
    # same-state neighbour rate (grid pairs) vs true-adjacency baseline
    st_of = {r["geoid"]: r["state"] for r in voting}
    same_grid = sum(1 for a, b in adj4 if st_of[a] == st_of[b])
    same_true = sum(1 for a, b in true_adj if st_of[a] == st_of[b])
    # state tile contiguity: 4-connected components per state
    cells_by_state = defaultdict(set)
    for r in got:
        cells_by_state[r["state"]].add((int(r["grid_col"]), int(r["grid_row"])))
    frag, single = [], 0
    for st, cs in sorted(cells_by_state.items()):
        if len(cs) < 2:
            single += 1
            continue
        seen, comp = set(), 0
        for start in cs:
            if start in seen:
                continue
            comp += 1
            dq = deque([start])
            seen.add(start)
            while dq:
                c, r = dq.popleft()
                for nb in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                    if nb in cs and nb not in seen:
                        seen.add(nb)
                        dq.append(nb)
        if comp == 1:
            single += 1
        else:
            frag.append([st, len(cs), comp])
    # ordering preservation vs centroids (CONUS only)
    cg = [r for r in got if r["inset"] == "FALSE"]
    ew_ok = ew_tot = ns_ok = ns_tot = 0
    for i in range(len(cg)):
        for j in range(i + 1, len(cg)):
            a, b = cg[i]["geoid"], cg[j]["geoid"]
            dx = cent_km[a][0] - cent_km[b][0]
            dc = int(cg[i]["grid_col"]) - int(cg[j]["grid_col"])
            if abs(dx) > 1e-9 and dc != 0:
                ew_tot += 1
                ew_ok += int((dc > 0) == (dx > 0))
            dy = cent_km[a][1] - cent_km[b][1]
            dr = int(cg[i]["grid_row"]) - int(cg[j]["grid_row"])
            if abs(dy) > 1e-9 and dr != 0:  # row grows south, y grows north
                ns_tot += 1
                ns_ok += int((dr > 0) == (dy < 0))
    # unused candidate cells
    used_cells = {(int(r["grid_col"]), int(r["grid_row"])) for r in got
                  if r["inset"] == "FALSE"}
    unused = sorted(set((c[0], c[1]) for c in cells) - used_cells)

    # squared-variant adjacency (same grid, different assignment)
    with open(f"{OUT}/tilegrid_districts_squared.csv", newline="") as f:
        got_sq = list(csv.DictReader(f))
    pos_sq = {(int(r["grid_col"]), int(r["grid_row"])): r["geoid"]
              for r in got_sq}
    adj4_sq = set()
    for (c, r), g in pos_sq.items():
        for dc, dr in ((1, 0), (0, 1)):
            h = pos_sq.get((c + dc, r + dr))
            if h:
                adj4_sq.add(tuple(sorted((g, h))))
    disp_sq = {}
    for r in got_sq:
        if r["inset"] == "TRUE":
            continue
        g = r["geoid"]
        cx = xmin + (int(r["grid_col"]) + 0.5) * s
        cy = ymax - (int(r["grid_row"]) + 0.5) * s
        x, y = cent_km[g]
        disp_sq[g] = math.hypot(x - cx, y - cy)
    dsq = np.array(list(disp_sq.values()))

    ver = {
        "inputs": {
            "districts_csv_rows": 441, "voting_districts": 435,
            "excluded_delegates": ["1198", "6098", "6698", "6998", "7298", "7898"],
            "geometry": "cd119_5m.geojson (2024 Cartographic Boundary Files 1:5,000,000, 119th Congress)",
            "landmask": "states_5m.geojson, 48 CONUS states + DC unioned",
            "projection": "EPSG:5070 (NAD83 / Conus Albers), km",
            "population_voting": {
                "min": 542112, "max": 989948, "mean": 760367,
                "ratio_max_min": 1.83, "total": 330759736},
        },
        "centroid_cross_check_km": centroid_check,
        "grid": {
            "method": "rectangular grid over CONUS Albers bbox; candidate cells = centres inside CONUS landmask; Hungarian assignment minimising total displacement",
            "cell_size_km": CELL_KM,
            "cell_size_rationale": "sqrt(CONUS land area / 432) = 134.4 km; 132 km is the nearest round size below that yielding >= 432 in-mask cells",
            "land_area_km2": round(land_km2),
            "cols": nx, "rows_main": ny,
            "grid_col_range": [0, nx - 1], "grid_row_range_main": [0, ny - 1],
            "total_grid_extent_incl_insets": {"cols": nx, "rows": 24,
                                              "rows_note": "rows 0-21 main grid, row 22 blank separator, row 23 insets"},
            "candidate_cells_in_landmask": len(cells),
            "cells_used_conus": 432, "unused_candidate_cells": len(unused),
            "unused_cells_col_row": [[c, r] for c, r in unused],
            "insets": {g: {"cell": list(INSETS[g]),
                           "displacement_grid_units": round(inset_disp_units[g], 1)}
                       for g in ("0200", "1501", "1502")},
        },
        "completeness_from_csv": {
            "rows": len(got), "unique_cells": len(pos),
            "unique_geoids": len({r["geoid"] for r in got}),
            "missing_geoids": [], "duplicate_cells": [],
        },
        "displacement_km_conus_linear_cost": {
            "total": round(float(dvals.sum())),
            "mean": round(float(dvals.mean()), 1),
            "median": round(float(np.median(dvals)), 1),
            "p90": round(float(np.percentile(dvals, 90)), 1),
            "max": round(float(dvals.max()), 1),
            "max_geoid": max(disp, key=disp.get),
            "max_state_cd": f"{by_geoid[max(disp, key=disp.get)]['state']}-{by_geoid[max(disp, key=disp.get)]['cd']}",
            "n_over_1000km": int((dvals > 1000).sum()),
            "n_over_500km": int((dvals > 500).sum()),
            "worst_10": [[g, round(d, 1)] for g, d in worst],
            "worst_states_by_mean": [[s_, round(m, 1), n] for s_, m, n in state_mean],
        },
        "adjacency": {
            "definition": "true = district polygons touch-or-intersect (incl. point touches), as in the states verify code; grid = 4-neighbour (orthogonal) cells",
            "true_adjacencies_all_435": len(true_adj),
            "true_adjacencies_conus_432": len(conus_true),
            "true_adjacencies_shared_border_only_conus": len(conus_true_border),
            "true_adjacency_same_state": same_true,
            "grid_4neighbour_pairs_all_435": len(adj4),
            "preserved_4neighbour": len(kept4),
            "preserved_4neighbour_pct_of_conus_true": round(100 * len(kept4) / len(conus_true), 1),
            "lost_4neighbour": len(conus_true - adj4),
            "false_4neighbour": len(adj4 - true_adj),
            "preserved_8neighbour_incl_diagonal": len(kept8),
            "preserved_8neighbour_pct": round(100 * len(kept8) / len(conus_true), 1),
            "preserved_shared_border_only_4neighbour": len(conus_true_border & adj4),
            "preserved_shared_border_only_pct": round(100 * len(conus_true_border & adj4) / len(conus_true_border), 1),
            "hi_inset_adjacency_preserved": tuple(sorted(("1501", "1502"))) in adj4,
        },
        "state_grouping": {
            "metric_definition": "same_state_share = share of 4-neighbour grid pairs whose two districts are in the same state; contiguity = a state's tiles form one 4-connected component",
            "grid_4neighbour_pairs_same_state": same_grid,
            "grid_4neighbour_pairs_same_state_pct": round(100 * same_grid / len(adj4), 1),
            "true_adjacencies_same_state_pct": round(100 * same_true / len(true_adj), 1),
            "states_single_tile_or_single_component": single,
            "states_fragmented": frag,
            "n_states_total": 50,
        },
        "ordering_preserved_conus": {
            "east_west": [ew_ok, ew_tot, round(ew_ok / ew_tot, 4)],
            "north_south": [ns_ok, ns_tot, round(ns_ok / ns_tot, 4)],
        },
        "sensitivity_squared_cost_same_grid": {
            "objective": "minimise sum of SQUARED distances instead of sum of distances",
            "total_displacement_km": round(float(dsq.sum())),
            "mean_km": round(float(dsq.mean()), 1),
            "median_km": round(float(np.median(dsq)), 1),
            "p90_km": round(float(np.percentile(dsq, 90)), 1),
            "max_km": round(float(dsq.max()), 1),
            "max_geoid": max(disp_sq, key=disp_sq.get),
            "preserved_4neighbour": len(true_adj & adj4_sq),
            "preserved_4neighbour_pct_of_conus_true": round(100 * len(true_adj & adj4_sq) / len(conus_true), 1),
            "false_4neighbour": len(adj4_sq - true_adj),
            "file": "tilegrid_districts_squared.csv",
        },
        "published_grid_source": {
            "used": None,
            "found_not_used": "Daily Kos congressional-district hexmap DKOS_CD_Hexmap_v1.1 (one hex per district), via Pitch Interactive tilegrams (https://raw.githubusercontent.com/PitchInteractiveInc/tilegrams/master/us-congressional-districts-2018.html) and tilegramsR (https://bhaskarvk.github.io/tilegramsR/). Hexagonal, not a square grid, and 2018 vintage (pre-2020 redistricting), so it cannot supply CD119 square-grid coordinates. This layout was computed from scratch from CD119 geometry.",
        },
    }
    with open(f"{OUT}/tilegrid_verification.json", "w") as f:
        json.dump(ver, f, indent=1)
    print(json.dumps({k: ver[k] for k in
                      ("completeness_from_csv", "displacement_km_conus_linear_cost",
                       "adjacency", "state_grouping")}, indent=1))
    print("wrote tilegrid_verification.json")


if __name__ == "__main__":
    main()
