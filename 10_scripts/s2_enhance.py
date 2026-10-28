"""Phase 7 (brief 3.2): composites, spectral indices and enhancement comparison from the 10 m reflectance stacks.

Outputs (03_enhanced/S2):
  S2_<date>_<comp>.vrt           natural (B04 B03 B02), fcc (B08 B04 B03), swir (B12 B8A B04) - virtual, lossless
  S2_<date>_<comp>_p2-98.tif     8-bit display copy, 2-98 % linear stretch per band (for maps; never for analysis)
  S2_<date>_NDVI.tif / _MNDWI.tif / _NDBI.tif   Float32 indices
Figures (09_docs): s2_composites.png, s2_indices.png, s2_enhancement_panel.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from osgeo import gdal
from skimage import exposure

ROOT = Path(r"D:\SAREO-Kumbh")
SRC = ROOT / "02_preproc" / "S2"
OUT = ROOT / "03_enhanced" / "S2"
OUT.mkdir(parents=True, exist_ok=True)
DATES = [("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")]
ORDER = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
COMPOSITES = {"natural": ("B04", "B03", "B02"), "fcc": ("B08", "B04", "B03"), "swir": ("B12", "B8A", "B04")}
INDICES = {"NDVI": ("B08", "B04"), "MNDWI": ("B03", "B11"), "NDBI": ("B11", "B08")}  # (a - b) / (a + b)
gdal.UseExceptions()


def stretch(a, lo_p=2, hi_p=98):
    lo, hi = np.nanpercentile(a, (lo_p, hi_p))
    return np.clip((a - lo) / (hi - lo), 0, 1)


stacks = {}
for ep, date in DATES:
    src_path = SRC / f"S2_{date}_L2A_refl10m.tif"
    with rasterio.open(src_path) as src:
        bands = {name: src.read(i + 1) for i, name in enumerate(ORDER)}
        profile = src.profile
    stacks[ep] = bands
    for comp, (r, g, b) in COMPOSITES.items():
        idx = [ORDER.index(x) + 1 for x in (r, g, b)]
        vrt = OUT / f"S2_{date}_{comp}.vrt"
        gdal.Translate(str(vrt), str(src_path), format="VRT", bandList=idx)
        rgb = np.stack([stretch(bands[x]) for x in (r, g, b)])
        byte = np.where(np.isnan(rgb), 0, np.round(rgb * 254) + 1).astype("uint8")  # 0 reserved for NoData
        p8 = profile.copy()
        p8.update(count=3, dtype="uint8", nodata=0, predictor=2, photometric="RGB")
        with rasterio.open(OUT / f"S2_{date}_{comp}_p2-98.tif", "w", **p8) as dst:
            dst.write(byte)
    for name, (a, b) in INDICES.items():
        va, vb = bands[a], bands[b]
        idx = np.where((va + vb) != 0, (va - vb) / (va + vb), np.nan).astype("float32")
        pi = profile.copy()
        pi.update(count=1, dtype="float32", nodata=np.nan, predictor=3)
        with rasterio.open(OUT / f"S2_{date}_{name}.tif", "w", **pi) as dst:
            dst.write(idx, 1)
            dst.set_band_description(1, f"{name} = ({a} - {b}) / ({a} + {b})")
        bands[name] = idx
    print(ep, date, " ".join(f"{n} median {np.nanmedian(bands[n]):+.3f}" for n in INDICES))

# ---- composites panel: rows = epochs, cols = composites ----
fig, axes = plt.subplots(3, 3, figsize=(15, 14.5))
for i, (ep, date) in enumerate(DATES):
    for j, (comp, (r, g, b)) in enumerate(COMPOSITES.items()):
        rgb = np.stack([stretch(stacks[ep][x]) for x in (r, g, b)], axis=-1)
        axes[i, j].imshow(np.nan_to_num(rgb))
        axes[i, j].set_title(f"{ep} {date[:4]}-{date[4:6]}-{date[6:]}  {comp} ({r}-{g}-{b})", fontsize=10)
        axes[i, j].axis("off")
fig.suptitle("Sentinel-2 L2A composites, 2-98 % stretch per band (AOI 14.2 x 13.8 km)", fontsize=13)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "s2_composites.png", dpi=70); plt.close(fig)

# ---- indices panel ----
fig, axes = plt.subplots(3, 3, figsize=(15, 14.5))
lims = {"NDVI": (-0.2, 0.8, "RdYlGn"), "MNDWI": (-0.6, 0.6, "RdBu"), "NDBI": (-0.4, 0.3, "PuOr_r")}
for i, (ep, date) in enumerate(DATES):
    for j, name in enumerate(INDICES):
        lo, hi, cmap = lims[name]
        im = axes[i, j].imshow(stacks[ep][name], cmap=cmap, vmin=lo, vmax=hi)
        axes[i, j].set_title(f"{ep} {name} (median {np.nanmedian(stacks[ep][name]):+.2f})", fontsize=10)
        axes[i, j].axis("off")
        plt.colorbar(im, ax=axes[i, j], fraction=0.046, pad=0.02)
fig.suptitle("Spectral indices: NDVI (vegetation), MNDWI (water), NDBI (built-up / tents)", fontsize=13)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "s2_indices.png", dpi=70); plt.close(fig)

# ---- enhancement panel on T1 natural colour (brief 3.2): same image, 6 display transforms + histograms ----
rgb = np.stack([stacks["T1"][x] for x in ("B04", "B03", "B02")], axis=-1)
valid = np.isfinite(rgb).all(-1)
mm = np.nanmin(rgb), np.nanmax(rgb)
versions = {
    "No stretch (0-1 reflectance)": np.clip(rgb, 0, 1),
    f"Min-max linear ({mm[0]:.2f}-{mm[1]:.2f})": (rgb - mm[0]) / (mm[1] - mm[0]),
    "2-98 % linear (per band)": np.stack([stretch(rgb[..., k]) for k in range(3)], -1),
    "Histogram equalisation": np.stack([exposure.equalize_hist(np.nan_to_num(rgb[..., k]), mask=valid) for k in range(3)], -1),
    "2-98 % + gamma 0.7 (brighter)": np.stack([stretch(rgb[..., k]) for k in range(3)], -1) ** 0.7,
    "2-98 % + gamma 1.4 (darker)": np.stack([stretch(rgb[..., k]) for k in range(3)], -1) ** 1.4,
}
zoom = (slice(560, 960), slice(560, 960))  # 4 x 4 km around the confluence
fig, axes = plt.subplots(3, 6, figsize=(24, 12.5), gridspec_kw={"height_ratios": [1, 1, 0.55]})
for j, (title, img) in enumerate(versions.items()):
    img = np.clip(np.nan_to_num(img), 0, 1)
    axes[0, j].imshow(img); axes[0, j].set_title(title, fontsize=10); axes[0, j].axis("off")
    axes[1, j].imshow(img[zoom]); axes[1, j].set_title("4 x 4 km zoom (Sangam)", fontsize=9); axes[1, j].axis("off")
    for k, c in enumerate("rgb"):
        axes[2, j].hist(img[..., k][valid].ravel(), bins=100, range=(0, 1), histtype="step", color=c, lw=1)
    axes[2, j].set_yticks([]); axes[2, j].set_xlabel("display value")
fig.suptitle("Enhancement of the same T1 (2025-02-16) natural-colour image - display transforms only, reflectance unchanged", fontsize=14)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "s2_enhancement_panel.png", dpi=65); plt.close(fig)
print("figures saved")
