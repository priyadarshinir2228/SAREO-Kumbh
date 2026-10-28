"""Brief 2.2: SAR image characteristics panel from the unfiltered sigma0 (dB) rasters.

Row 1: VV for T0 / T1 / T2 (same stretch) + VV histograms.  Row 2: VH for T0 / T1 / T2 + VH histograms.
Row 3: 4 x 4 km zoom on the Sangam at T1 (VV, VH, VV-VH ratio) + speckle profile across uniform sand.
Output: 09_docs/s1_characteristics.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
S1 = ROOT / "02_preproc" / "S1"
EPOCHS = [("T0", "20241112"), ("T1", "20250216"), ("T2", "20250417")]
ZOOM = (588000, 2811500, 592000, 2815500)  # 4 x 4 km around the confluence
STRETCH = {"VV": (-25, 0), "VH": (-30, -8)}


def read(date, band, bounds=None):
    with rasterio.open(S1 / f"S1A_{date}_Sig0_nofilter_dB.tif") as src:
        i = 1 if band == "VH" else 2
        if bounds is None:
            return src.read(i), src.bounds
        return src.read(i, window=from_bounds(*bounds, src.transform)), bounds


fig = plt.figure(figsize=(18, 14))
gs = fig.add_gridspec(3, 4, width_ratios=[1, 1, 1, 0.9])
for r, band in enumerate(["VV", "VH"]):
    lo, hi = STRETCH[band]
    axh = fig.add_subplot(gs[r, 3])
    for c, (ep, date) in enumerate(EPOCHS):
        a, b = read(date, band)
        ax = fig.add_subplot(gs[r, c])
        ax.imshow(a, cmap="gray", vmin=lo, vmax=hi, extent=(b.left, b.right, b.bottom, b.top))
        ax.set_title(f"{band} {ep} {date[:4]}-{date[4:6]}-{date[6:]}  (median {np.nanmedian(a):.1f} dB)", fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
        if ep == "T1":
            ax.add_patch(plt.Rectangle((ZOOM[0], ZOOM[1]), ZOOM[2] - ZOOM[0], ZOOM[3] - ZOOM[1], fill=False, ec="red", lw=1.5))
        axh.hist(a[np.isfinite(a)].ravel(), bins=120, range=(lo - 10, hi + 8), histtype="step", lw=1.4, label=ep)
    axh.set_title(f"{band} histogram (dB)", fontsize=10); axh.legend(); axh.set_xlabel("sigma0 (dB)")

vv, _ = read("20250216", "VV", ZOOM)
vh, _ = read("20250216", "VH", ZOOM)
for c, (img, title, lim, cmap) in enumerate([
    (vv, "T1 zoom VV: tent blocks, pontoon bridges, river", STRETCH["VV"], "gray"),
    (vh, "T1 zoom VH", STRETCH["VH"], "gray"),
    (vv - vh, "T1 zoom VV-VH (dB): low = volume (vegetation)", (0, 15), "viridis"),
]):
    ax = fig.add_subplot(gs[2, c])
    im = ax.imshow(img, cmap=cmap, vmin=lim[0], vmax=lim[1], extent=(ZOOM[0], ZOOM[2], ZOOM[1], ZOOM[3]))
    ax.set_title(title, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.02)

# speckle: VV profile along a row through T0 dry sand (should be uniform) shows multiplicative noise
t0, b0 = read("20241112", "VV", ZOOM)
row = t0[t0.shape[0] // 2]
ax = fig.add_subplot(gs[2, 3])
ax.plot(np.arange(row.size) * 10 / 1000, row, lw=0.7)
ax.set_title("Speckle: T0 VV profile across zoom centre", fontsize=10)
ax.set_xlabel("distance (km)"); ax.set_ylabel("sigma0 VV (dB)")

fig.suptitle("Sentinel-1A IW GRD, relative orbit 92 descending - sigma0 terrain-corrected, unfiltered (AOI_Kumbh)", fontsize=13)
fig.tight_layout()
out = ROOT / "09_docs" / "s1_characteristics.png"
fig.savefig(out, dpi=80)
print("saved", out)
