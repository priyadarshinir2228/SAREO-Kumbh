"""Phase 14: real cloud-mask comparison on cloudy monsoon scenes (the project dates T0-T2 were cloud-free).

Scenes (Earth Search / AWS COGs, AOI window only, 10 m): S2B 2025-08-15 (AOI cloud 43 % by SCL, same day as the T3
Sentinel-1 scene) and S2B 2025-09-24 (22 %). Reflectance = (DN + offset) / 10000, offset -1000 unless Earth Search has
already applied it. OmniCloudMask runs in a separate process (ocm_worker.py, OpenMP conflict with GDAL).
Compared: SCL masked {3 shadow, 8/9 cloud, 10 cirrus} vs OmniCloudMask {1 thick, 2 thin, 3 shadow}, overall and per
category (cloud vs shadow), agreement %, Cohen's kappa. Visual panel for interpretation.
Outputs: 02_preproc/S2/S2_<date>_monsoon_*.tif, 09_docs/cloudmask_monsoon_comparison.csv, cloudmask_monsoon.png
"""
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "02_preproc" / "S2"
AOI = (582400, 2807200, 596600, 2821000)
H, W = 1380, 1420
DATES = ["2025-08-15", "2025-09-24"]


def item(date):
    body = {"collections": ["sentinel-2-l2a"], "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z", "limit": 2,
            "query": {"mgrs:utm_zone": {"eq": 44}, "mgrs:latitude_band": {"eq": "R"}, "mgrs:grid_square": {"eq": "NP"}}}
    req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["features"][0]


def read(href, nearest=False):
    with rasterio.open(href) as s:
        return s.read(1, window=from_bounds(*AOI, s.transform), out_shape=(H, W),
                      resampling=Resampling.nearest if nearest else Resampling.bilinear).astype("float32")


rows, panels = [], []
for date in DATES:
    it = item(date)
    offset = 0 if it["properties"].get("earthsearch:boa_offset_applied") else -1000
    bands = {k: (read(it["assets"][k]["href"]) + offset) / 10000 for k in ("red", "green", "blue", "nir")}
    scl = read(it["assets"]["scl"]["href"], nearest=True).astype("uint8")
    arr = np.stack([bands["red"], bands["green"], bands["nir"]]).astype("float32")
    with tempfile.TemporaryDirectory() as tmp:
        np.save(Path(tmp) / "in.npy", arr)
        r = subprocess.run([sys.executable, "-I", str(ROOT / "10_scripts" / "ocm_worker.py"), str(Path(tmp) / "in.npy"),
                            str(Path(tmp) / "out.npy"), r"D:\conda_envs\sareo\omnicloudmask_models"], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr[-1500:])
        sec = float(r.stdout.strip().splitlines()[-1])
        ocm = np.load(Path(tmp) / "out.npy")
    prof = dict(driver="GTiff", width=W, height=H, count=1, crs="EPSG:32644", transform=from_origin(AOI[0], AOI[3], 10, 10),
                compress="deflate", dtype="uint8")
    tag = date.replace("-", "")
    for name, a in (("SCL", scl), ("omnicloud", ocm)):
        with rasterio.open(OUT / f"S2_{tag}_monsoon_{name}10m.tif", "w", **prof) as d:
            d.write(a.astype("uint8"), 1)
    s_cloud, s_shadow = np.isin(scl, [8, 9, 10]), scl == 3
    o_cloud, o_shadow = np.isin(ocm, [1, 2]), ocm == 3
    for label, a, b in (("any mask", s_cloud | s_shadow, o_cloud | o_shadow), ("cloud only", s_cloud, o_cloud),
                        ("shadow only", s_shadow, o_shadow)):
        po = (a == b).mean()
        pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
        rows.append({"date": date, "category": label, "SCL_pct": round(100 * a.mean(), 1), "OCM_pct": round(100 * b.mean(), 1),
                     "agreement_pct": round(100 * po, 1), "kappa": round((po - pe) / (1 - pe), 3),
                     "SCL_only_pct": round(100 * (a & ~b).mean(), 1), "OCM_only_pct": round(100 * (b & ~a).mean(), 1),
                     "OCM_runtime_s": round(sec)})
    rows.append({"date": date, "category": "OCM thin cloud", "OCM_pct": round(100 * (ocm == 2).mean(), 1)})
    rgb = np.clip(np.dstack([bands["red"], bands["green"], bands["blue"]]) / 0.35, 0, 1)
    panels.append((date, rgb, scl, ocm))
    print(pd.DataFrame([r for r in rows if r["date"] == date]).to_string(index=False))

pd.DataFrame(rows).to_csv(ROOT / "09_docs" / "cloudmask_monsoon_comparison.csv", index=False)
fig, axes = plt.subplots(len(panels), 3, figsize=(16, 5.4 * len(panels)))
for i, (date, rgb, scl, ocm) in enumerate(panels):
    axes[i, 0].imshow(rgb); axes[i, 0].set_title(f"S2 {date} natural colour")
    sc = np.zeros(scl.shape, "uint8"); sc[np.isin(scl, [8, 9, 10])] = 1; sc[scl == 3] = 3
    cm = matplotlib.colors.ListedColormap(["#ffffff00", "#e53935", "#ff9800", "#283593"])
    for ax, m, t in ((axes[i, 1], sc, "SCL: red = cloud (8/9/10), blue = shadow (3)"),
                     (axes[i, 2], ocm, "OmniCloudMask: red thick, orange thin, blue shadow")):
        ax.imshow(rgb, alpha=0.6); ax.imshow(np.ma.masked_equal(m, 0), cmap=cm, vmin=0, vmax=3, alpha=0.65, interpolation="nearest")
        ax.set_title(t)
    for ax in axes[i]:
        ax.axis("off")
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "cloudmask_monsoon.png", dpi=55)
