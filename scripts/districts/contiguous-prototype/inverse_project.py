"""Inverse-project the go-cart-wasm districts output from EPSG:5070 back
to lon/lat.

Input:  contiguous_districts_2020_gocart_5070.geojson (EPSG:5070, metres)
Output: contiguous_districts_2020_gocart.geojson (EPSG:4269 lon/lat,
        same datum as the source CBF files)

NOTE on AK/HI: the input placed Alaska at-large (scaled 0.35) and
Hawaii's 2 districts as insets below CONUS in EPSG:5070 space. Inverse
projection carries those inset positions into lon/lat, so AK/HI in the
output are NOT at their true geographic coordinates — they sit below
CONUS in lon/lat too. Render this file with an identity/fit projection
in Vega-Lite, NOT Albers USA (which would apply its own inset transform
on top). The script prints the resulting AK/HI centroid lon/lat so the
placement is on the record.
"""
import json
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

BASE = "/home/hatch/workspace/cartogram-census/districts"
SRC = f"{BASE}/contiguous_districts_2020_gocart_5070.geojson"
OUT = f"{BASE}/contiguous_districts_2020_gocart.geojson"

tr = Transformer.from_crs("EPSG:5070", "EPSG:4269", always_xy=True)

with open(SRC) as f:
    data = json.load(f)

out_feats = []
for feat in data["features"]:
    g = shp_transform(lambda x, y, z=None: tr.transform(x, y), shape(feat["geometry"]))
    out_feats.append({
        "type": "Feature",
        "properties": feat["properties"],
        "geometry": mapping(g),
    })

out = {"type": "FeatureCollection", "features": out_feats}
with open(OUT, "w") as f:
    json.dump(out, f)

print(f"wrote {OUT}: {len(out_feats)} features")
xs, ys = [], []
for feat in out_feats:
    b = shape(feat["geometry"]).bounds
    xs += [b[0], b[2]]; ys += [b[1], b[3]]
    p = feat["properties"]
    if p["state"] in ("AK", "HI") or (p["state"], p["cd"]) in (("CA", "01"), ("ME", "01"), ("FL", "01")):
        c = shape(feat["geometry"]).centroid
        print(f"  {p['state']}-{p['cd']} ({p['geoid']}) centroid lon/lat: {c.x:.3f}, {c.y:.3f}")
print(f"lon/lat bbox: lon {min(xs):.3f}..{max(xs):.3f}  lat {min(ys):.3f}..{max(ys):.3f}")
