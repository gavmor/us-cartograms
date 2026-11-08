"""Reproject the 50 US states to EPSG:5070 for the go-cart-wasm prototype.

Same method as ../build_contiguous.py (which built the input for the C
go_cart run), reproduced here so this prototype's input is independently
generated and checkable:
- EPSG:4269 lon/lat (2024 CBF 1:5m) -> EPSG:5070 NAD83/Conus Albers (metres,
  equal-area, required by go-cart: geographic coordinates give erroneous
  results per the go-cart-wasm README).
- AK/HI decision (option a): 48 CONUS states keep true EPSG:5070
  positions; Alaska is scaled 0.35 about its centroid and moved to a
  bottom-left inset, Hawaii moved to an inset below CONUS (Albers-USA
  style, as d3's albersUsa does, and as the Demers layout did).
  Rationale: in true EPSG:5070 Alaska sits ~1,500 km NW of CONUS and
  Hawaii ~3,800 km SW; including them would stretch the flow grid over
  huge empty ocean, wasting grid resolution on CONUS. Alaska is ~15% of
  US land area but 0.22% of population, so it must shrink drastically
  under density equalisation anyway. The insets are therefore NOT in
  true geographic position — disclosed in README.md; the lon/lat output
  must be rendered with an identity/fit projection, not Albers USA.
"""
import csv, json
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform
from shapely.affinity import scale, translate
from pyproj import Transformer

SRC = "/home/hatch/workspace/cartogram-census/states_5m.geojson"
CSV = "/home/hatch/workspace/cartogram-census/states.csv"
OUT = "/home/hatch/workspace/cartogram-census/contiguous-prototype/states50_5070.geojson"

STATES50 = set("""AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS
MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY""".split())

pop = {}
with open(CSV) as f:
    for row in csv.DictReader(f):
        if row["state"] in STATES50:
            pop[row["state"]] = int(row["population"])
assert len(pop) == 50, len(pop)

tr = Transformer.from_crs("EPSG:4269", "EPSG:5070", always_xy=True)
def project(geom):
    return shp_transform(lambda x, y, z=None: tr.transform(x, y), geom)

feats = []
with open(SRC) as f:
    data = json.load(f)
conus = []
for feat in data["features"]:
    abbr = feat["properties"]["STUSPS"]
    if abbr not in STATES50:
        continue
    g = project(shape(feat["geometry"]))
    conus.append((abbr, feat["properties"]["NAME"], g))

xs, ys = [], []
for abbr, name, g in conus:
    if abbr in ("AK", "HI"):
        continue
    b = g.bounds
    xs += [b[0], b[2]]; ys += [b[1], b[3]]
xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
print(f"CONUS bbox x {xmin:.0f}..{xmax:.0f}  y {ymin:.0f}..{ymax:.0f}")

out_feats = []
for abbr, name, g in conus:
    if abbr == "AK":
        c = g.centroid
        g = scale(g, xfact=0.35, yfact=0.35, origin=c)
        c2 = g.centroid
        g = translate(g, xoff=(xmin + 350000) - c2.x, yoff=(ymin - 550000) - c2.y)
    elif abbr == "HI":
        c = g.centroid
        g = translate(g, xoff=(xmin + 1500000) - c.x, yoff=(ymin - 550000) - c.y)
    out_feats.append({
        "type": "Feature",
        "properties": {"STUSPS": abbr, "NAME": name, "population": pop[abbr]},
        "geometry": mapping(g),
    })

out = {"type": "FeatureCollection", "features": out_feats}
with open(OUT, "w") as f:
    json.dump(out, f)
print(f"wrote {OUT}: {len(out_feats)} features")
