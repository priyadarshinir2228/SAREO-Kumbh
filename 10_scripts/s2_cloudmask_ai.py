"""Phase 7 AI comparison: OmniCloudMask (RSE 2025) vs the Sentinel-2 SCL mask on the AOI, per date.

OmniCloudMask classes: 0 clear, 1 thick cloud, 2 thin cloud, 3 cloud shadow.  SCL 'masked' = {3, 8, 9, 10}.
Writes 02_preproc/S2/S2_<date>_omnicloud10m.tif and 09_docs/cloudmask_comparison.csv + cloudmask_comparison.png
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio

ROOT = Path(r"D:\SAREO-Kumbh")
S2 = ROOT / "02_preproc" / "S2"
MODEL_DIR = Path(r"D:\conda_envs\sareo\omnicloudmask_models")
DATES = [("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")]
rows, panels = [], []
for ep, date in DATES:
    with rasterio.open(S2 / f"S2_{date}_L2A_refl10m.tif") as src:
        red, green, nir = src.read(3), src.read(2), src.read(7)  # B04, B03, B08
        profile = src.profile
    arr = np.nan_to_num(np.stack([red, green, nir]), nan=0.0).astype("float32")
    with tempfile.TemporaryDirectory() as tmp:  # model runs in a separate process (OpenMP conflict, see ocm_worker.py)
        np.save(Path(tmp) / "in.npy", arr)
        res = subprocess.run([sys.executable, "-I", str(ROOT / "10_scripts" / "ocm_worker.py"), str(Path(tmp) / "in.npy"),
                              str(Path(tmp) / "out.npy"), str(MODEL_DIR)], capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(res.stderr[-2000:])
        sec = float(res.stdout.strip().splitlines()[-1])
        ocm = np.load(Path(tmp) / "out.npy")
    with rasterio.open(S2 / f"S2_{date}_SCL10m.tif") as src:
        scl = src.read(1)
    scl_mask = np.isin(scl, [3, 8, 9, 10])
    ocm_mask = ocm > 0
    valid = scl > 0
    agree = (scl_mask == ocm_mask)[valid].mean()
    po = agree
    pe = scl_mask[valid].mean() * ocm_mask[valid].mean() + (1 - scl_mask[valid].mean()) * (1 - ocm_mask[valid].mean())
    kappa = (po - pe) / (1 - pe) if pe < 1 else np.nan
    p = profile.copy()
    p.update(count=1, dtype="uint8", nodata=255, predictor=1)
    with rasterio.open(S2 / f"S2_{date}_omnicloud10m.tif", "w", **p) as dst:
        dst.write(ocm, 1)
        dst.set_band_description(1, "OmniCloudMask 0 clear 1 thick 2 thin 3 shadow")
    rows.append({"epoch": ep, "date": date, "runtime_s": round(sec), "scl_masked_pct": round(100 * scl_mask[valid].mean(), 3),
                 "ocm_thick_pct": round(100 * (ocm == 1)[valid].mean(), 3), "ocm_thin_pct": round(100 * (ocm == 2)[valid].mean(), 3),
                 "ocm_shadow_pct": round(100 * (ocm == 3)[valid].mean(), 3), "ocm_masked_pct": round(100 * ocm_mask[valid].mean(), 3),
                 "agreement_pct": round(100 * agree, 3), "kappa": round(kappa, 3)})
    panels.append((ep, date, red, green, scl_mask, ocm))
    print(rows[-1])

df = pd.DataFrame(rows)
df.to_csv(ROOT / "09_docs" / "cloudmask_comparison.csv", index=False)

fig, axes = plt.subplots(len(panels), 3, figsize=(13, 4.3 * len(panels)))
for i, (ep, date, red, green, scl_mask, ocm) in enumerate(panels):
    axes[i, 0].imshow(np.clip(np.nan_to_num(red) / 0.3, 0, 1), cmap="gray"); axes[i, 0].set_title(f"{ep} {date} red band")
    axes[i, 1].imshow(scl_mask, cmap="Reds", vmin=0, vmax=1); axes[i, 1].set_title(f"SCL masked {scl_mask.mean() * 100:.3f}%")
    im = axes[i, 2].imshow(np.ma.masked_equal(ocm, 0), cmap="viridis", vmin=1, vmax=3)
    axes[i, 2].set_title(f"OmniCloudMask (1 thick, 2 thin, 3 shadow) {100 * (ocm > 0).mean():.3f}%")
    for ax in axes[i]:
        ax.axis("off")
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "cloudmask_comparison.png", dpi=60)
print(df.to_string(index=False))
