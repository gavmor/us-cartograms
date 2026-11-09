#!/usr/bin/env python3
"""Compute the Demers (squares) layout for the 435 voting US congressional
districts (119th Congress, 2020 Census CD119 P1 populations).

Demers method: HONEST LABEL — iterative overlap-removal (FRC-style baseline).
This is NOT the Nickel et al. TOP-W-St linear program. There is no LP solver
here: squares start at their Albers centroids, side = c*sqrt(population), and
overlaps are resolved by iterative pairwise separation along the axis of
least penetration, with a weak anchor pull toward the starting position in
phase 1 only. H/V separation constraints in the Nickel sense are NOT
enforced as hard constraints; ordering preservation is measured afterwards
and reported. Adapted from ../compute_layouts.py (states solver), same
960x600 view, GAP=2, TOTAL_AREA_FRAC=0.32, same two-phase schedule.

Differences vs the states solver, forced by scale (435 regions vs 50):
- Overlap *detection* is vectorised with numpy broadcasting (435x435
  pairwise matrix per iteration, ~94k pairs); only the overlapping pairs
  found are pushed, sequentially (Gauss-Seidel, exactly as the states
  solver's inner loop). A naive O(n^2) Python pair loop per iteration
  is NOT used.
- Centroids are geometric centroids computed here from cd119_5m.geojson
  with shapely (lon/lat, EPSG:4269), projected to EPSG:5070 — not read
  from districts.csv. The CSV centroids are cross-checked, not used.
- Alaska (0200, at-large) and Hawaii (1501, 1502) are Albers-USA-style
  insets exactly as the states solver did (AK bottom-left, HI below
  CONUS). HI has two districts, so it gets two adjacent inset centres.
  Their displacement figures are reported in view units only, not km.

Projection: EPSG:4269 -> EPSG:5070 (NAD83 / Conus Albers, metres) via
pyproj, fitted to a 960x600 view (CONUS into x 70-890, y 40-560;
y flipped: north = top). Verification is recomputed from the WRITTEN
CSV (rounded values), not from solver memory.
"""
import csv
import json
import math
import time

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape

WORKDIR = "/home/hatch/workspace/cartogram-census"
OUTDIR = f"{WORKDIR}/districts"
VIEW_W, VIEW_H = 960.0, 600.0
GAP = 2.0            # target minimum gap between squares, view units
TOTAL_AREA_FRAC = 0.32   # sum of square areas as a fraction of view area

INSET_GEOIDS = {"0200", "1501", "1502"}   # AK at-large, HI-01, HI-02


def load_districts():
    rows = []
    with open(f"{WORKDIR}/districts.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["is_delegate"] == "0":
                rows.append(r)
    assert len(rows) == 435, f"expected 435 voting districts, got {len(rows)}"
    rows.sort(key=lambda r: r["geoid"])
    return rows


def main():
    rows = load_districts()
    geoids = [r["geoid"] for r in rows]
    idx = {g: i for i, g in enumerate(geoids)}
    pops = np.array([int(r["population"]) for r in rows], dtype=float)
    total_pop = int(pops.sum())
    assert total_pop == 330759736, total_pop
    print(f"voting districts: {len(rows)}, total pop {total_pop:,}")
    print(f"pop min {int(pops.min())} ({rows[int(np.argmin(pops))]['geoid']}), "
          f"max {int(pops.max())} ({rows[int(np.argmax(pops))]['geoid']}), "
          f"mean {pops.mean():.0f}, median {np.median(pops):.0f}, "
          f"ratio {pops.max()/pops.min():.2f}x")

    # ---- geometric centroids from the geojson (shapely, lon/lat) ----
    with open(f"{WORKDIR}/cd119_5m.geojson") as f:
        gj = json.load(f)
    geom = {ft["properties"]["GEOID"]: shape(ft["geometry"])
            for ft in gj["features"]}
    assert all(g in geom for g in geoids), "missing geometries"
    tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)

    lonlat_cent = {}
    csv_cent = {}
    for r in rows:
        c = geom[r["geoid"]].centroid
        lonlat_cent[r["geoid"]] = (c.x, c.y)
        csv_cent[r["geoid"]] = (float(r["centroid_lon"]),
                                float(r["centroid_lat"]))
    # Cross-check vs districts.csv centroids (km, after projection).
    diffs = []
    for r in rows:
        x1, y1 = tr.transform(*lonlat_cent[r["geoid"]])
        x2, y2 = tr.transform(*csv_cent[r["geoid"]])
        diffs.append(math.hypot(x1 - x2, y1 - y2) / 1000.0)
    diffs = np.array(diffs)
    worst = int(np.argmax(diffs))
    print(f"centroid cross-check (geojson shapely centroid vs districts.csv): "
          f"max {diffs.max():.2f} km ({rows[worst]['geoid']} "
          f"{rows[worst]['state']}-{rows[worst]['cd']}), "
          f"mean {diffs.mean():.2f}, median {np.median(diffs):.2f}, "
          f"n>1km {int((diffs > 1).sum())}, n>5km {int((diffs > 5).sum())}")
    conus_mask = np.array([g not in INSET_GEOIDS for g in geoids])
    print(f"centroid cross-check, CONUS only (432): max "
          f"{diffs[conus_mask].max():.2f} km "
          f"({rows[int(np.argmax(np.where(conus_mask, diffs, -1)))]['geoid']}), "
          f"mean {diffs[conus_mask].mean():.2f}, "
          f"median {np.median(diffs[conus_mask]):.2f}")

    # ---- project centroids to EPSG:5070 (km) and fit CONUS to the view ----
    proj = {}
    for r in rows:
        x_m, y_m = tr.transform(*lonlat_cent[r["geoid"]])
        proj[r["geoid"]] = (x_m / 1000.0, y_m / 1000.0)
    conus = [g for g in geoids if g not in INSET_GEOIDS]
    xs = [proj[g][0] for g in conus]
    ys = [proj[g][1] for g in conus]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    scale = min((890 - 70) / (xmax - xmin), (560 - 40) / (ymax - ymin))
    km_per_unit = 1.0 / scale
    x0_view, y0_view = 70.0, 40.0

    def to_view(g):
        px, py = proj[g]
        return (x0_view + (px - xmin) * scale,
                y0_view + (ymax - py) * scale)  # flip y

    init = {g: to_view(g) for g in conus}
    # Insets, Albers-USA style (d3 albersUsa: AK bottom-left, HI below CA).
    # States solver used AK (130,515), HI (290,545); HI has two districts
    # here, so they sit side by side centred on 290.
    init["0200"] = (130.0, 515.0)   # AK at-large
    init["1501"] = (268.0, 545.0)   # HI-01
    init["1502"] = (293.0, 545.0)   # HI-02

    # ---- square sizes: side = c * sqrt(pop), sum of areas = frac * view ----
    c = math.sqrt(TOTAL_AREA_FRAC * VIEW_W * VIEW_H / total_pop)
    side = c * np.sqrt(pops)
    print(f"scale: {scale:.5f} view-units/km, km_per_unit={km_per_unit:.3f}")
    print(f"c={c:.6f}; side min {side.min():.2f} units "
          f"({side.min()*km_per_unit:.1f} km, {rows[int(np.argmin(side))]['geoid']}), "
          f"max {side.max():.2f} units "
          f"({side.max()*km_per_unit:.1f} km, {rows[int(np.argmax(side))]['geoid']}); "
          f"side ratio {side.max()/side.min():.3f}x, "
          f"area ratio {(side.max()/side.min())**2:.3f}x "
          f"(= pop ratio {pops.max()/pops.min():.3f}x by construction); "
          f"total square area={float((side**2).sum()):,.0f} "
          f"({float((side**2).sum())/(VIEW_W*VIEW_H):.1%} of view)")

    x = np.array([init[g][0] for g in geoids], dtype=float)
    y = np.array([init[g][1] for g in geoids], dtype=float)
    s = side.copy()
    x_init, y_init = x.copy(), y.copy()

    def find_overlaps(x, y, gap):
        """Vectorised detection: indices of pairs overlapping by > gap.
        Returns (i, j, ox, oy) arrays, upper triangle only."""
        dx = np.abs(x[:, None] - x[None, :])
        dy = np.abs(y[:, None] - y[None, :])
        half = (s[:, None] + s[None, :]) / 2.0 + gap
        ox = half - dx
        oy = half - dy
        mask = np.triu(ox > 0, k=1) & np.triu(oy > 0, k=1)
        ii, jj = np.where(mask)
        return ii, jj, ox[ii, jj], oy[ii, jj]

    def step(x, y, anchor):
        ii, jj, ox, oy = find_overlaps(x, y, GAP)
        for k in range(len(ii)):
            i, j = ii[k], jj[k]
            if ox[k] < oy[k]:  # push apart horizontally (least penetration)
                push = ox[k] / 2 + 0.01
                d = 1.0 if x[i] >= x[j] else -1.0
                x[i] += d * push
                x[j] -= d * push
            else:
                push = oy[k] / 2 + 0.01
                d = 1.0 if y[i] >= y[j] else -1.0
                y[i] += d * push
                y[j] -= d * push
        if anchor:
            x += anchor * (x_init - x)
            y += anchor * (y_init - y)
        x[:] = np.clip(x, s / 2, VIEW_W - s / 2)
        y[:] = np.clip(y, s / 2, VIEW_H - s / 2)
        return len(ii)

    n0 = len(find_overlaps(x, y, GAP)[0])
    n0_true = len(find_overlaps(x, y, 0.0)[0])
    print(f"initial overlaps: {n0} pairs at gap={GAP} "
          f"({n0_true} true geometric overlaps at gap 0)")

    # Phase 1: repulsion + weak anchor.
    hist1 = []
    t0 = time.time()
    n_ov = None
    phase1_iters = 3000
    for it in range(phase1_iters):
        n_ov = step(x, y, anchor=0.002)
        if it % 100 == 0 or n_ov == 0:
            hist1.append((it, n_ov))
        if n_ov == 0:
            print(f"phase 1 converged at iter {it}")
            break
    t1 = time.time()
    p1_iters = it + 1
    p1_final = n_ov
    print(f"after phase 1: {n_ov} overlapping pairs (gap={GAP}), "
          f"{p1_iters} iterations, {t1-t0:.1f}s")
    # Phase 2: repulsion only.
    hist2 = []
    t2 = time.time()
    phase2_iters = 20000
    for it in range(phase2_iters):
        n_ov = step(x, y, anchor=0.0)
        if it % 100 == 0 or n_ov == 0:
            hist2.append((it, n_ov))
        if n_ov == 0:
            print(f"phase 2 converged at iter {it}")
            break
    t3 = time.time()
    p2_iters = it + 1
    p2_final = n_ov
    print(f"after phase 2: {n_ov} overlapping pairs (gap={GAP}), "
          f"{p2_iters} iterations, {t3-t2:.1f}s")
    converged = (n_ov == 0)

    # ---- write CSV ----
    # 4dp for positions/sides/displacements: with 435 squares, hundreds of
    # pairs sit within 0.02 of the gap boundary, and 2dp rounding flipped
    # 118 of them into marginal (<=0.01 unit) gap violations in the written
    # file even though the solver had converged to zero overlaps in float.
    # 4dp keeps the rounding error (<=0.00015 units on any gap) far below
    # that. side_km / displacement_km stay at 1dp (informational only).
    disp_u = np.hypot(x - x_init, y - y_init)
    with open(f"{OUTDIR}/demers_districts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geoid", "state", "cd", "name", "population",
                    "side_units", "side_km", "x", "y", "centroid_x",
                    "centroid_y", "displacement_units", "displacement_km",
                    "inset"])
        for i, r in enumerate(rows):
            inset = r["geoid"] in INSET_GEOIDS
            w.writerow([
                r["geoid"], r["state"], r["cd"], r["name"], int(pops[i]),
                f"{s[i]:.4f}",
                f"{s[i]*km_per_unit:.1f}" if not inset else "",
                f"{x[i]:.4f}", f"{y[i]:.4f}",
                f"{x_init[i]:.4f}", f"{y_init[i]:.4f}",
                f"{disp_u[i]:.4f}",
                f"{disp_u[i]*km_per_unit:.1f}" if not inset else "",
                "TRUE" if inset else "FALSE",
            ])
    print("wrote demers_districts.csv")

    # ---- verification FROM THE WRITTEN CSV (re-read, rounded values) ----
    with open(f"{OUTDIR}/demers_districts.csv", newline="") as f:
        vr = list(csv.DictReader(f))
    assert len(vr) == 435
    vx = np.array([float(r["x"]) for r in vr])
    vy = np.array([float(r["y"]) for r in vr])
    vs = np.array([float(r["side_units"]) for r in vr])
    vcx = np.array([float(r["centroid_x"]) for r in vr])
    vcy = np.array([float(r["centroid_y"]) for r in vr])
    vpop = np.array([int(r["population"]) for r in vr], dtype=float)
    vinset = np.array([r["inset"] == "TRUE" for r in vr])

    def overlaps_from(vx, vy, vs, gap):
        dx = np.abs(vx[:, None] - vx[None, :])
        dy = np.abs(vy[:, None] - vy[None, :])
        half = (vs[:, None] + vs[None, :]) / 2.0 + gap
        ox = half - dx
        oy = half - dy
        mask = np.triu(ox > 0, k=1) & np.triu(oy > 0, k=1)
        ii, jj = np.where(mask)
        return ii, jj, ox[ii, jj], oy[ii, jj]

    ii0, jj0, ox0, oy0 = overlaps_from(vx, vy, vs, 0.0)
    iig, jjg, oxg, oyg = overlaps_from(vx, vy, vs, GAP)
    max_ov_area, max_ov_pair = 0.0, None
    for k in range(len(ii0)):
        area = float(ox0[k] * oy0[k])
        if area > max_ov_area:
            max_ov_area, max_ov_pair = area, (vr[ii0[k]]["geoid"],
                                              vr[jj0[k]]["geoid"])
    vdisp_u = np.hypot(vx - vcx, vy - vcy)
    conus_i = np.where(~vinset)[0]
    vdisp_km = vdisp_u[conus_i] * km_per_unit
    # Ordering preservation vs initial centroids (all pairs), vectorised.
    dxi = vcx[:, None] - vcx[None, :]
    dxf = vx[:, None] - vx[None, :]
    dyi = vcy[:, None] - vcy[None, :]
    dyf = vy[:, None] - vy[None, :]
    triu = np.triu(np.ones((435, 435), dtype=bool), k=1)
    ew_tot = int((triu & (np.abs(dxi) > 1e-9)).sum())
    ew_ok = int((triu & (np.abs(dxi) > 1e-9) & (dxf * dxi > 0)).sum())
    ns_tot = int((triu & (np.abs(dyi) > 1e-9)).sum())
    ns_ok = int((triu & (np.abs(dyi) > 1e-9) & (dyf * dyi > 0)).sum())
    # Cartographic error: by construction (unrounded) and from written CSV.
    ratio = (s ** 2) / pops
    cart_err = float((ratio.max() - ratio.min()) / ratio.mean())
    ratio_csv = (vs ** 2) / vpop
    cart_err_csv = float((ratio_csv.max() - ratio_csv.min())
                         / ratio_csv.mean())
    kmax = int(conus_i[int(np.argmax(vdisp_km))])
    biggest = sorted(zip(vdisp_km, [vr[i]["geoid"] for i in conus_i]),
                     reverse=True)[:10]
    print(f"VERIFY (from written CSV): true overlaps (gap 0): {len(ii0)}, "
          f"max overlap area {max_ov_area:.3f} sq units {max_ov_pair}")
    print(f"VERIFY: gap violations (gap {GAP}): {len(iig)}")
    if len(iig):
        worst_g = int(np.argmax(oxg * oyg))
        print(f"  worst gap violation: {vr[iig[worst_g]]['geoid']} vs "
              f"{vr[jjg[worst_g]]['geoid']}, ox={oxg[worst_g]:.3f}, "
              f"oy={oyg[worst_g]:.3f}")
    print(f"VERIFY: displacement CONUS (km): mean {vdisp_km.mean():.1f}, "
          f"median {np.median(vdisp_km):.1f}, max {vdisp_km.max():.1f} "
          f"({vr[kmax]['geoid']} {vr[kmax]['state']}-{vr[kmax]['cd']})")
    print(f"VERIFY: displacement insets (view units): "
          + ", ".join(f"{vr[i]['geoid']} {vdisp_u[i]:.1f}"
                      for i in np.where(vinset)[0]))
    print(f"VERIFY: ordering preserved: E-W {ew_ok}/{ew_tot} "
          f"= {ew_ok/ew_tot:.1%}, N-S {ns_ok}/{ns_tot} = {ns_ok/ns_tot:.1%}")
    print(f"VERIFY: cartographic error by construction {cart_err:.2e}, "
          f"from written CSV {cart_err_csv:.2e}")
    print("largest CONUS displacements (km):",
          ", ".join(f"{g} {d:.0f}" for d, g in biggest))

    verif = {
        "view": [VIEW_W, VIEW_H],
        "gap_units": GAP,
        "total_area_fraction": TOTAL_AREA_FRAC,
        "n_districts": 435,
        "excluded_delegates": ["1198", "6098", "6698", "6998", "7298", "7898"],
        "population": {
            "sum": total_pop,
            "min": int(pops.min()),
            "min_geoid": rows[int(np.argmin(pops))]["geoid"],
            "max": int(pops.max()),
            "max_geoid": rows[int(np.argmax(pops))]["geoid"],
            "mean": round(float(pops.mean()), 1),
            "median": round(float(np.median(pops)), 1),
            "sd": round(float(pops.std(ddof=1)), 1),
            "ratio_max_min": round(float(pops.max() / pops.min()), 3),
        },
        "centroid_crosscheck_geojson_vs_csv_km": {
            "max": round(float(diffs.max()), 2),
            "max_geoid": rows[worst]["geoid"],
            "mean": round(float(diffs.mean()), 2),
            "median": round(float(np.median(diffs)), 2),
            "n_gt_1km": int((diffs > 1).sum()),
            "n_gt_5km": int((diffs > 5).sum()),
            "conus_max": round(float(diffs[conus_mask].max()), 2),
            "conus_max_geoid": rows[int(np.argmax(
                np.where(conus_mask, diffs, -1)))]["geoid"],
            "conus_mean": round(float(diffs[conus_mask].mean()), 2),
            "conus_median": round(float(np.median(diffs[conus_mask])), 2),
        },
        "km_per_unit": round(km_per_unit, 4),
        "scale_view_units_per_km": round(scale, 5),
        "side_c": round(c, 6),
        "side_units": {
            "min": round(float(side.min()), 2),
            "min_geoid": rows[int(np.argmin(side))]["geoid"],
            "max": round(float(side.max()), 2),
            "max_geoid": rows[int(np.argmax(side))]["geoid"],
            "min_km": round(float(side.min() * km_per_unit), 1),
            "max_km": round(float(side.max() * km_per_unit), 1),
            "ratio": round(float(side.max() / side.min()), 3),
            "area_ratio_max_min": round(float((side.max() / side.min()) ** 2), 3),
        },
        "insets": {
            "0200": {"label": "AK at-large", "centroid_view": [130.0, 515.0]},
            "1501": {"label": "HI-01", "centroid_view": [268.0, 545.0]},
            "1502": {"label": "HI-02", "centroid_view": [293.0, 545.0]},
        },
        "initial_overlaps_gap2": int(n0),
        "initial_true_overlaps_gap0": int(n0_true),
        "converged": bool(converged),
        "phase1": {"iterations_run": int(p1_iters),
                   "final_overlaps": int(p1_final),
                   "seconds": round(t1 - t0, 1),
                   "history_every_100": [[int(a), int(b)] for a, b in hist1]},
        "phase2": {"iterations_run": int(p2_iters),
                   "final_overlaps": int(p2_final),
                   "seconds": round(t3 - t2, 1),
                   "history_every_100": [[int(a), int(b)] for a, b in hist2]},
        "true_overlaps_gap0": int(len(ii0)),
        "max_overlap_area_sq_units": round(max_ov_area, 3),
        "max_overlap_pair": list(max_ov_pair) if max_ov_pair else None,
        "gap_violations": int(len(iig)),
        "displacement_km_conus": {
            "mean": round(float(vdisp_km.mean()), 1),
            "median": round(float(np.median(vdisp_km)), 1),
            "max": round(float(vdisp_km.max()), 1),
            "max_geoid": vr[kmax]["geoid"],
            "max_state_cd": f"{vr[kmax]['state']}-{vr[kmax]['cd']}",
        },
        "largest_displacements_km": [
            {"geoid": g, "km": round(float(d), 1)} for d, g in biggest],
        "displacement_units_insets": {
            vr[i]["geoid"]: round(float(vdisp_u[i]), 1)
            for i in np.where(vinset)[0]},
        "ordering_ew_preserved": [ew_ok, ew_tot, round(ew_ok / ew_tot, 4)],
        "ordering_ns_preserved": [ns_ok, ns_tot, round(ns_ok / ns_tot, 4)],
        "cartographic_error_by_construction": cart_err,
        "cartographic_error_from_written_csv": cart_err_csv,
        "method": ("iterative overlap-removal (FRC-style baseline), "
                   "NOT Nickel et al. TOP-W-St LP"),
    }
    with open(f"{OUTDIR}/demers_verification.json", "w") as f:
        json.dump(verif, f, indent=1)
    print("wrote demers_verification.json")


if __name__ == "__main__":
    main()
