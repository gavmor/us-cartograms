#!/usr/bin/env python3
"""Compute Demers (squares) and tile-grid layouts for the 50 US states,
population-weighted (2020 Census CD119 P1, resident).

Demers method: HONEST LABEL — iterative overlap-removal (FRC-style baseline).
This is NOT the Nickel et al. TOP-W-St linear program. There is no LP solver
here: squares start at their Albers centroids, side = c*sqrt(population), and
overlaps are resolved by iterative pairwise separation along the axis of
least penetration, with a weak anchor pull toward the starting position in
phase 1. H/V separation constraints in the Nickel sense are NOT enforced as
hard constraints; ordering preservation is measured afterwards and reported.

Projection: state centroids (lon/lat, EPSG:4269, from states.csv) are projected
to EPSG:5070 (NAD83 / Conus Albers, metres) with pyproj, then fitted to a
960x600 view. Alaska and Hawaii are NOT at their raw EPSG:5070 positions
(they would sit thousands of km from the mainland and blow up the view);
they are placed as standard Albers-USA-style insets (documented below),
exactly as d3's albersUsa does. Their displacement figures are therefore
reported in view units only, not km.

Tile grid: amCharts US tile-map grid (12 cols x 9 rows), positions read
directly from https://www.amcharts.com/demos/tile-map/ (accessed 2026-11-08).
DC is dropped (51st entry there); the 50 states are kept. Integer grid
columns/rows are used; amCharts' even-row +0.5 stagger (for circles) is NOT
applied — a hex rendering should offset even rows by half a cell.
"""
import csv
import json
import math
import sys

import numpy as np
from pyproj import Transformer

WORKDIR = "/home/hatch/workspace/cartogram-census"
VIEW_W, VIEW_H = 960.0, 600.0
GAP = 2.0            # target minimum gap between squares, view units
TOTAL_AREA_FRAC = 0.32   # sum of square areas as a fraction of view area

# 50 state abbreviations (DC/PR/Island Areas excluded)
FIFTY = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY",
}

# amCharts tile-map grid (x = grid_col 0..11, y = grid_row 0..8, row 0 at top).
# Read from https://www.amcharts.com/demos/tile-map/ 2026-11-08. DC (10,4) omitted.
TILEGRID = {
    "AL": (7, 6), "AK": (0, 0), "AZ": (3, 5), "AR": (6, 5), "CA": (2, 5),
    "CO": (3, 4), "CT": (11, 3), "DE": (9, 4), "FL": (8, 8), "GA": (8, 7),
    "HI": (0, 8), "ID": (2, 3), "IL": (6, 3), "IN": (7, 3), "IA": (5, 3),
    "KS": (5, 5), "KY": (6, 4), "LA": (5, 6), "ME": (11, 0), "MD": (8, 4),
    "MA": (10, 2), "MI": (7, 2), "MN": (4, 2), "MS": (6, 6), "MO": (5, 4),
    "MT": (2, 2), "NE": (4, 4), "NV": (2, 4), "NH": (11, 1), "NJ": (10, 3),
    "NM": (3, 6), "NY": (9, 2), "NC": (9, 5), "ND": (3, 2), "OH": (8, 3),
    "OK": (4, 6), "OR": (1, 4), "PA": (9, 3), "RI": (11, 2), "SC": (8, 6),
    "SD": (4, 3), "TN": (7, 5), "TX": (4, 7), "UT": (4, 5), "VT": (10, 1),
    "VA": (8, 5), "WA": (1, 2), "WV": (7, 4), "WI": (5, 2), "WY": (3, 3),
}


def load_states():
    rows = []
    with open(f"{WORKDIR}/states.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["state"] in FIFTY:
                rows.append(r)
    assert len(rows) == 50, f"expected 50 states, got {len(rows)}"
    return rows


def main():
    rows = load_states()
    pops = {r["state"]: int(r["population"]) for r in rows}
    names = {r["state"]: r["name"] for r in rows}
    total_pop = sum(pops.values())
    assert total_pop == 330759736, total_pop

    # ---- project centroids to EPSG:5070 (km) ----
    tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
    proj = {}
    for r in rows:
        x_m, y_m = tr.transform(float(r["centroid_lon"]), float(r["centroid_lat"]))
        proj[r["state"]] = (x_m / 1000.0, y_m / 1000.0)

    conus = [a for a in FIFTY if a not in ("AK", "HI")]
    xs = [proj[a][0] for a in conus]
    ys = [proj[a][1] for a in conus]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    # Fit CONUS into x in [70, 890], y in [40, 560] (y flipped: north = top).
    # Leave the bottom strip (y > 560) for the AK/HI insets.
    scale = min((890 - 70) / (xmax - xmin), (560 - 40) / (ymax - ymin))
    km_per_unit = 1.0 / scale
    x0_view = 70.0
    y0_view = 40.0

    def to_view(a):
        px, py = proj[a]
        return (x0_view + (px - xmin) * scale,
                y0_view + (ymax - py) * scale)  # flip y

    init = {a: to_view(a) for a in conus}
    # Insets, Albers-USA style (d3 albersUsa puts AK bottom-left, HI below CA).
    init["AK"] = (130.0, 515.0)
    init["HI"] = (290.0, 545.0)

    # ---- square sizes: side = c * sqrt(pop), sum of areas = frac * view ----
    c = math.sqrt(TOTAL_AREA_FRAC * VIEW_W * VIEW_H / total_pop)
    side = {a: c * math.sqrt(pops[a]) for a in FIFTY}
    print(f"scale: {scale:.5f} view-units/km, km_per_unit={km_per_unit:.3f}")
    print(f"c={c:.6f}; CA side={side['CA']:.1f}, TX={side['TX']:.1f}, "
          f"WY={side['WY']:.1f}, VT={side['VT']:.1f}; "
          f"total square area={sum(s * s for s in side.values()):,.0f} "
          f"({sum(s * s for s in side.values()) / (VIEW_W * VIEW_H):.1%} of view)")

    abbrs = sorted(FIFTY)
    idx = {a: i for i, a in enumerate(abbrs)}
    x = np.array([init[a][0] for a in abbrs], dtype=float)
    y = np.array([init[a][1] for a in abbrs], dtype=float)
    s = np.array([side[a] for a in abbrs], dtype=float)
    x_init, y_init = x.copy(), y.copy()

    def overlaps(x, y, gap):
        """Return list of (i, j, ox, oy) for pairs overlapping by more than gap."""
        out = []
        for i in range(len(abbrs)):
            for j in range(i + 1, len(abbrs)):
                dx = abs(x[i] - x[j])
                dy = abs(y[i] - y[j])
                ox = (s[i] + s[j]) / 2 + gap - dx
                oy = (s[i] + s[j]) / 2 + gap - dy
                if ox > 0 and oy > 0:
                    out.append((i, j, ox, oy))
        return out

    def step(x, y, anchor):
        ov = overlaps(x, y, GAP)
        for (i, j, ox, oy) in ov:
            if ox < oy:  # push apart horizontally (least penetration)
                push = ox / 2 + 0.01
                d = 1.0 if x[i] >= x[j] else -1.0
                x[i] += d * push
                x[j] -= d * push
            else:
                push = oy / 2 + 0.01
                d = 1.0 if y[i] >= y[j] else -1.0
                y[i] += d * push
                y[j] -= d * push
        if anchor:
            x += anchor * (x_init - x)
            y += anchor * (y_init - y)
        # keep squares inside the view
        x[:] = np.clip(x, s / 2, VIEW_W - s / 2)
        y[:] = np.clip(y, s / 2, VIEW_H - s / 2)
        return len(ov)

    # Phase 1: repulsion + weak anchor (keeps the overall shape / ordering).
    n_ov = None
    for it in range(3000):
        n_ov = step(x, y, anchor=0.002)
        if n_ov == 0:
            print(f"phase 1 converged at iter {it}")
            break
    print(f"after phase 1: {n_ov} overlapping pairs (gap={GAP})")
    # Phase 2: repulsion only, until zero overlap (with the target gap).
    for it in range(20000):
        n_ov = step(x, y, anchor=0.0)
        if n_ov == 0:
            print(f"phase 2 converged at iter {it}")
            break
    print(f"after phase 2: {n_ov} overlapping pairs (gap={GAP})")

    # ---- verification ----
    ov0 = overlaps(x, y, 0.0)   # true geometric overlap
    ovg = overlaps(x, y, GAP)   # gap violations
    max_ov_area = 0.0
    max_ov_pair = None
    for (i, j, ox, oy) in ov0:
        area = ox * oy
        if area > max_ov_area:
            max_ov_area, max_ov_pair = area, (abbrs[i], abbrs[j])
    disp_u = np.hypot(x - x_init, y - y_init)
    conus_idx = [idx[a] for a in conus]
    disp_km = disp_u[conus_idx] * km_per_unit
    # Ordering preservation vs initial positions (all pairs).
    ew_ok = ew_tot = ns_ok = ns_tot = 0
    for i in range(len(abbrs)):
        for j in range(i + 1, len(abbrs)):
            if abs(x_init[i] - x_init[j]) > 1e-9:
                ew_tot += 1
                if (x[i] - x[j]) * (x_init[i] - x_init[j]) > 0:
                    ew_ok += 1
            if abs(y_init[i] - y_init[j]) > 1e-9:
                ns_tot += 1
                if (y[i] - y[j]) * (y_init[i] - y_init[j]) > 0:
                    ns_ok += 1
    # Area error by construction: side^2 / pop is constant; only CSV rounding.
    areas = s ** 2
    ratio = areas / np.array([pops[a] for a in abbrs], dtype=float)
    cart_err = float((ratio.max() - ratio.min()) / ratio.mean())

    print(f"FINAL: true overlaps (gap 0): {len(ov0)}, max overlap area "
          f"{max_ov_area:.3f} sq units {max_ov_pair}")
    print(f"FINAL: gap violations (gap {GAP}): {len(ovg)}")
    print(f"displacement CONUS (km): mean {disp_km.mean():.0f}, median "
          f"{np.median(disp_km):.0f}, max {disp_km.max():.0f} "
          f"({abbrs[conus_idx[int(np.argmax(disp_km))]]})")
    print(f"displacement AK/HI (view units): AK {disp_u[idx['AK']]:.1f}, "
          f"HI {disp_u[idx['HI']]:.1f} (insets — km not meaningful)")
    print(f"ordering preserved: E-W {ew_ok}/{ew_tot} = {ew_ok/ew_tot:.1%}, "
          f"N-S {ns_ok}/{ns_tot} = {ns_ok/ns_tot:.1%}")
    print(f"cartographic error by construction: {cart_err:.2e} "
          f"(side^2 exactly proportional to population)")
    biggest = sorted(zip(disp_km, [abbrs[i] for i in conus_idx]),
                     reverse=True)[:8]
    print("largest CONUS displacements (km):",
          ", ".join(f"{a} {d:.0f}" for d, a in biggest))

    # ---- write demers_states.csv ----
    with open(f"{WORKDIR}/demers_states.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "abbr", "name", "population", "side_units",
                    "side_km", "x", "y", "centroid_x", "centroid_y",
                    "displacement_units", "displacement_km", "inset"])
        for i, a in enumerate(abbrs):
            inset = a in ("AK", "HI")
            w.writerow([
                a, a, names[a], pops[a],
                f"{s[i]:.2f}",
                f"{s[i] * km_per_unit:.1f}" if not inset else "",
                f"{x[i]:.2f}", f"{y[i]:.2f}",
                f"{x_init[i]:.2f}", f"{y_init[i]:.2f}",
                f"{disp_u[i]:.2f}",
                f"{disp_u[i] * km_per_unit:.1f}" if not inset else "",
                "TRUE" if inset else "FALSE",
            ])

    # ---- write tilegrid_states.csv ----
    assert set(TILEGRID) == FIFTY, "tile grid must cover exactly the 50 states"
    cells = list(TILEGRID.values())
    assert len(set(cells)) == 50, "tile grid has duplicate cells"
    with open(f"{WORKDIR}/tilegrid_states.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "abbr", "name", "population",
                    "grid_col", "grid_row"])
        for a in sorted(FIFTY):
            col, row = TILEGRID[a]
            w.writerow([a, a, names[a], pops[a], col, row])
    print("tile grid: 50 states, 50 unique cells, "
          f"cols 0..{max(c for c, _ in cells)}, rows 0..{max(r for _, r in cells)}")

    # Save verification numbers for the README.
    verif = {
        "view": [VIEW_W, VIEW_H],
        "gap_units": GAP,
        "total_area_fraction": TOTAL_AREA_FRAC,
        "km_per_unit": round(km_per_unit, 4),
        "scale_view_units_per_km": round(scale, 5),
        "side_c": round(c, 6),
        "side_min_max": [round(float(s.min()), 2), round(float(s.max()), 2)],
        "true_overlaps_gap0": len(ov0),
        "max_overlap_area_sq_units": round(max_ov_area, 3),
        "max_overlap_pair": list(max_ov_pair) if max_ov_pair else None,
        "gap_violations": len(ovg),
        "displacement_km_conus": {
            "mean": round(float(disp_km.mean()), 1),
            "median": round(float(np.median(disp_km)), 1),
            "max": round(float(disp_km.max()), 1),
            "max_state": abbrs[conus_idx[int(np.argmax(disp_km))]],
        },
        "displacement_units_ak": round(float(disp_u[idx["AK"]]), 1),
        "displacement_units_hi": round(float(disp_u[idx["HI"]]), 1),
        "ordering_ew_preserved": [ew_ok, ew_tot, round(ew_ok / ew_tot, 4)],
        "ordering_ns_preserved": [ns_ok, ns_tot, round(ns_ok / ns_tot, 4)],
        "cartographic_error_by_construction": cart_err,
        "tilegrid": {"n_states": 50, "unique_cells": 50,
                     "cols": [0, 11], "rows": [0, 8]},
    }
    with open(f"{WORKDIR}/layouts_verification.json", "w") as f:
        json.dump(verif, f, indent=1)
    print("wrote demers_states.csv, tilegrid_states.csv, "
          "layouts_verification.json")


if __name__ == "__main__":
    main()
