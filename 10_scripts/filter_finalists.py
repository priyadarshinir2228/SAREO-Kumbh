"""Phase 6: 1.5 x 1.5 km close-up of the top-scoring filters (tent blocks + pontoon bridges), VV dB, plus a
residual-ratio check (original / filtered): a good filter leaves residuals that look like pure speckle with no
structure. Output: 09_docs/filter_finalists.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
FDIR = ROOT / "03_enhanced" / "S1_filters"
ZOOM = (589300, 2813200, 590800, 2814700)
FINAL = [("none", "Unfiltered"), ("lee7", "Lee 7x7"), ("gammamap7", "Gamma-MAP 7x7"), ("frost7", "Frost 7x7"),
         ("sar2sar", "SAR2SAR"), ("mtquegan", "Multi-temporal")]


def vv(tag):
    with rasterio.open(FDIR / f"T1_{tag}_lin.tif") as src:
        return src.read(2, window=from_bounds(*ZOOM, src.transform)).astype("float64")


o = vv("none")
fig, axes = plt.subplots(2, len(FINAL), figsize=(3.3 * len(FINAL), 7))
for j, (tag, title) in enumerate(FINAL):
    f = vv(tag)
    axes[0, j].imshow(10 * np.log10(np.clip(f, 1e-5, None)), cmap="gray", vmin=-25, vmax=0)
    axes[0, j].set_title(title, fontsize=10)
    ratio = np.divide(o, f, out=np.ones_like(o), where=f > 0)
    axes[1, j].imshow(ratio, cmap="gray", vmin=0, vmax=3)
    axes[1, j].set_title("ratio original/filtered" if tag != "none" else "(ratio = 1)", fontsize=9)
    for ax in axes[:, j]:
        ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("Finalists, 1.5 x 1.5 km: VV dB (top) and ratio image (bottom; visible structure = detail removed)", fontsize=12)
fig.tight_layout()
fig.savefig(ROOT / "09_docs" / "filter_finalists.png", dpi=80)

# structure left in the ratio image: correlation of ratio with the 3-date reference (0 = pure noise)
ref = np.mean([rasterio.open(ROOT / "02_preproc" / "S1" / f"S1A_{d}_Sig0_nofilter_lin.tif").read(2) for d in ("20250123", "20250204", "20250216")], axis=0)
full_o = rasterio.open(FDIR / "T1_none_lin.tif").read(2).astype("float64")
for tag, title in FINAL[1:]:
    full_f = rasterio.open(FDIR / f"T1_{tag}_lin.tif").read(2).astype("float64")
    m = (full_f > 0) & (full_o > 0) & np.isfinite(ref) & (ref > 0)
    r = np.log(full_o[m] / full_f[m])
    print(f"{title:15s} ratio mean {np.exp(r).mean():.3f}  corr(log ratio, log ref) {np.corrcoef(r, np.log(ref[m]))[0, 1]:+.3f}")
