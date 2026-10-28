"""Phase 9 figure: 3 x 3 km at the Sangam on T1 - originals, the feature-stack composite, four pixel-level fusions,
the multi-temporal SAR RGB, and B04 histograms. Output: 09_docs/fusion_panel.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
F = ROOT / "05_fused"
ZOOM = (588500, 2812500, 591500, 2815500)


def rd(path, bands):
    with rasterio.open(path) as s:
        return s.read(bands, window=from_bounds(*ZOOM, s.transform)).astype("float64")


def st(a, lo=None, hi=None):
    lo = np.nanpercentile(a, 2) if lo is None else lo
    hi = np.nanpercentile(a, 98) if hi is None else hi
    return np.clip((a - lo) / (hi - lo), 0, 1)


stack = rd(F / "fused_stack_T1_20250216.tif", list(range(1, 12)))  # VV VH diff B02 B03 B04 B08 B11 B12 NDVI MNDWI
nat = np.dstack([st(stack[5]), st(stack[4]), st(stack[3])])
tiles = [
    ("S2 natural colour (original)", nat),
    ("S1 VV dB, Lee 7x7 (original)", st(stack[0], -25, 0)),
    ("Feature stack: R=VV  G=NDVI  B=MNDWI", np.dstack([st(stack[0], -25, 0), st(stack[9], -0.2, 0.8), st(stack[10], -0.6, 0.4)])),
]
for name, file in (("PCA", "fusion_PCA_T1_20250216.tif"), ("IHS", "fusion_IHS_T1_20250216.tif"),
                   ("Brovey", "fusion_Brovey_T1_20250216.tif"), ("HPF injection", "fusion_HPF_T1_20250216.tif")):
    bands = [3, 2, 1] if name in ("PCA", "HPF injection") else [1, 2, 3]  # PCA/HPF store B02..B12; IHS/Brovey store B04 B03 B02
    a = rd(F / file, bands)
    tiles.append((f"{name} fusion (natural colour)", np.dstack([st(a[0]), st(a[1]), st(a[2])])))
mt = rd(F / "mtRGB_VV_R-T1_G-T0_B-T2_display.tif", [1, 2, 3]).transpose(1, 2, 0) / 255
tiles.append(("Multi-temporal SAR: R=T1 G=T0 B=T2 (red = new at T1)", mt))

fig, axes = plt.subplots(3, 3, figsize=(15, 15.5))
for ax, (title, img) in zip(axes.flat, tiles):
    ax.imshow(img, cmap="gray" if img.ndim == 2 else None)
    ax.set_title(title, fontsize=10); ax.axis("off")
ax = axes.flat[-1]
b04 = stack[5][np.isfinite(stack[5])]
ax.hist(b04, bins=120, range=(0, 0.5), histtype="step", lw=2, color="k", label="original B04")
for name, file, band in (("PCA", "fusion_PCA_T1_20250216.tif", 3), ("IHS", "fusion_IHS_T1_20250216.tif", 1),
                         ("Brovey", "fusion_Brovey_T1_20250216.tif", 1), ("HPF", "fusion_HPF_T1_20250216.tif", 3)):
    a = rd(F / file, [band])[0]
    ax.hist(a[np.isfinite(a)], bins=120, range=(0, 0.5), histtype="step", lw=1.2, label=name)
ax.set_title("B04 reflectance histogram, zoom area", fontsize=10); ax.legend(fontsize=8); ax.set_xlabel("reflectance")
fig.suptitle("SAR-EO fusion, T1 2025-02-16 (same-day Sentinel-1A + Sentinel-2B), 3 x 3 km at the Sangam", fontsize=13)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "fusion_panel.png", dpi=70)
print("saved fusion_panel.png")
