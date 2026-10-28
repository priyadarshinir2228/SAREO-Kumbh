"""Make 20 m true-colour previews of the AOI for every candidate Sentinel-2 date (reads only the AOI window
from the open Earth Search COGs on AWS; no login, no full-tile download). Output: 09_docs/s2_previews_<epoch>.png"""
import csv
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
XMIN, YMIN, XMAX, YMAX = 582400, 2807200, 596600, 2819600  # AOI, EPSG:32644 (tile 44RNP is also UTM 44N)
STAC = "https://earth-search.aws.element84.com/v1/search"

with (ROOT / "09_docs" / "scene_candidates.csv").open() as f:
    s2 = [r for r in csv.DictReader(f) if r["product_type"] == "S2MSI2A" and float(r["cloud_percent"]) < 5]


def visual_href(date):
    body = {
        "collections": ["sentinel-2-l2a"],
        "query": {"mgrs:utm_zone": {"eq": 44}, "mgrs:latitude_band": {"eq": "R"}, "mgrs:grid_square": {"eq": "NP"}},
        "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z",
        "limit": 5,
    }
    req = urllib.request.Request(STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    feats = json.load(urllib.request.urlopen(req, timeout=60))["features"]
    return feats[0]["assets"]["visual"]["href"] if feats else None


by_epoch = defaultdict(list)
for r in sorted(s2, key=lambda r: r["date"]):
    href = visual_href(r["date"])
    if not href:
        print("no COG for", r["date"])
        continue
    with rasterio.open(href) as src:
        win = from_bounds(XMIN, YMIN, XMAX, YMAX, src.transform)
        h, w = int(round((YMAX - YMIN) / 20)), int(round((XMAX - XMIN) / 20))
        rgb = src.read([1, 2, 3], window=win, out_shape=(3, h, w)).transpose(1, 2, 0)
    by_epoch[r["epoch"]].append((r["date"], r["cloud_percent"], rgb))
    print("read", r["epoch"], r["date"])

for epoch, imgs in by_epoch.items():
    n = len(imgs)
    cols = min(n, 4)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.9 * rows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, (date, cc, rgb) in zip(axes.flat, imgs):
        lo, hi = np.percentile(rgb, (2, 98))
        ax.imshow(np.clip((rgb.astype(float) - lo) / (hi - lo + 1e-6), 0, 1))
        ax.set_title(f"{epoch}  {date}  (tile cloud {cc}%)", fontsize=10)
    fig.suptitle(f"Sentinel-2 L2A true colour, AOI 14.2 x 12.4 km, 20 m - epoch {epoch}", fontsize=12)
    fig.tight_layout()
    out = ROOT / "09_docs" / f"s2_previews_{epoch}.png"
    fig.savefig(out, dpi=90)
    plt.close(fig)
    print("saved", out)
