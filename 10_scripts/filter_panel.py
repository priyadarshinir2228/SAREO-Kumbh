"""Phase 6 visual comparison (brief item 10): 3 x 3 km zoom on the Sangam pontoon bridges, VV dB, one tile per filter
family, plus a VV profile across the bridges. Output: 09_docs/filter_panel.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
FDIR = ROOT / "03_enhanced" / "S1_filters"
ZOOM = (588500, 2812500, 591500, 2815500)
TILES = [("none", "Unfiltered"), ("boxcar5", "Boxcar 5x5"), ("median5", "Median 5x5"), ("lee5", "Lee 5x5"),
         ("frost5", "Frost 5x5"), ("gammamap5", "Gamma-MAP 5x5"), ("kuan5", "Kuan 5x5 (OTB)"), ("refinedlee", "Refined Lee"),
         ("leesigma7", "Lee Sigma 7x7"), ("idan", "IDAN"), ("mulog", "MuLoG"), ("mtquegan", "Multi-temporal (3 dates)"),
         ("sar2sar", "SAR2SAR (deep learning)")]


def vv_db(tag):
    with rasterio.open(FDIR / f"T1_{tag}_lin.tif") as src:
        a = src.read(2, window=from_bounds(*ZOOM, src.transform))
    return 10 * np.log10(np.clip(a, 1e-5, None))


fig, axes = plt.subplots(4, 4, figsize=(16, 16.5))
profile_row = None
for ax, (tag, title) in zip(axes.flat, TILES):
    if not (FDIR / f"T1_{tag}_lin.tif").exists():
        ax.set_title(f"{title}: missing"); ax.axis("off"); continue
    img = vv_db(tag)
    profile_row = img.shape[0] // 2 if profile_row is None else profile_row
    ax.imshow(img, cmap="gray", vmin=-25, vmax=0)
    ax.axhline(profile_row, color="red", lw=0.6, alpha=0.6)
    ax.set_title(title, fontsize=11); ax.set_xticks([]); ax.set_yticks([])

axp = axes.flat[len(TILES)]
for tag, label in [("none", "unfiltered"), ("lee5", "Lee 5x5"), ("refinedlee", "Refined Lee"), ("mtquegan", "multi-temporal"), ("sar2sar", "SAR2SAR")]:
    if (FDIR / f"T1_{tag}_lin.tif").exists():
        axp.plot(np.arange(300) * 0.01, vv_db(tag)[profile_row], lw=0.9 if tag == "none" else 1.4, label=label,
                 alpha=0.5 if tag == "none" else 1)
axp.set_title("VV profile along red line (E-W, 3 km)", fontsize=11)
axp.set_xlabel("km"); axp.set_ylabel("sigma0 VV (dB)"); axp.legend(fontsize=8)
for ax in axes.flat[len(TILES) + 1:]:
    ax.axis("off")
fig.suptitle("Speckle filters on Sentinel-1A VV, 2025-02-16 (T1) - 3 x 3 km at the Sangam, -25..0 dB", fontsize=14)
fig.tight_layout()
fig.savefig(ROOT / "09_docs" / "filter_panel.png", dpi=75)
print("saved filter_panel.png")
