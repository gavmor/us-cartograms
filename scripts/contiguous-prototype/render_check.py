"""Render a quick visual sanity check of the lon/lat cartogram as SVG -> PNG.

Linear lon/lat -> canvas mapping (y flipped, north up). Fill colour is a
5-step log-population scale; white strokes. Output: gocart_check.png.
This is a shape/orientation check only — not a publication render.
"""
import json, math
from shapely.geometry import shape

PATH = "/home/hatch/workspace/cartogram-census/contiguous_states_2020_gocart.geojson"
W, H = 960, 620

with open(PATH) as f:
    data = json.load(f)

geoms = [(ft["properties"], shape(ft["geometry"])) for ft in data["features"]]
xs, ys = [], []
for _, g in geoms:
    b = g.bounds
    xs += [b[0], b[2]]; ys += [b[1], b[3]]
xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
sx = W / (xmax - xmin); sy = H / (ymax - ymin); s = min(sx, sy)

def pt(x, y):
    return ((x - xmin) * s, H - (y - ymin) * s)

PALETTE = ["#f1eef6", "#bdc9e1", "#74a9cf", "#2b8cbe", "#045a8d"]
def color(pop):
    i = min(4, max(0, int((math.log10(pop) - 5.7) / 0.35)))
    return PALETTE[i]

def poly_coords(coords):
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in (pt(x, y) for x, y in coords))

parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="white"/>']
for props, g in geoms:
    fill = color(props["population"])
    polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
    for poly in polys:
        parts.append(f'<polygon points="{poly_coords(poly.exterior.coords)}" '
                     f'fill="{fill}" stroke="white" stroke-width="0.8"/>')
        for hole in poly.interiors:
            parts.append(f'<polygon points="{poly_coords(hole.coords)}" '
                         f'fill="white" stroke="none"/>')
parts.append("</svg>")
svg = "".join(parts)
open("/home/hatch/workspace/cartogram-census/contiguous-prototype/gocart_check.svg", "w").write(svg)
print("wrote gocart_check.svg")
