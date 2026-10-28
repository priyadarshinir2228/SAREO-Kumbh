"""Phase 10 figure: extracted feature layers over the T1 natural-colour image (full AOI and a 4 x 4 km zoom).
Output: 09_docs/features_overview.png"""
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(r"D:\SAREO-Kumbh")
GPKG = ROOT / "06_vectors" / "kumbh_features.gpkg"
SRC = GPKG if GPKG.exists() else ROOT / "06_vectors" / "extracted_raw.gpkg"
AOI = (582400, 2807200, 596600, 2821000)
ZOOM = (588000, 2811500, 592000, 2815500)
with rasterio.open(ROOT / "03_enhanced" / "S2" / "S2_20250216_natural_p2-98.tif") as s:
    rgb = s.read().transpose(1, 2, 0)
WATER = "river_T1" if SRC == GPKG else "water_T1"  # name in the final database vs the raw extraction
STYLE = [("veg_fields", "#2e7d32", 0.25, None), ("sand_bars", "#f9a825", 0.35, None), (WATER, "#1565c0", 0.45, None),
         ("tent_blocks", "#d50000", 0.45, None), ("pontoon_bridges", "#ffea00", 1, 2.2)]
fig, axes = plt.subplots(1, 2, figsize=(18, 9))
for ax, ext, title in ((axes[0], AOI, "Full AOI"), (axes[1], ZOOM, "4 x 4 km at the Sangam")):
    ax.imshow(rgb, extent=(AOI[0], AOI[2], AOI[1], AOI[3]))
    for layer, colour, alpha, lw in STYLE:
        g = gpd.read_file(SRC, layer=layer)
        if lw:
            g.plot(ax=ax, color=colour, linewidth=lw)
        else:
            g.plot(ax=ax, facecolor=colour, edgecolor=colour, alpha=alpha, linewidth=0.4)
    ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3]); ax.set_title(title); ax.set_xticks([]); ax.set_yticks([])
handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=max(a, 0.6)) for _, c, a, _ in STYLE]
axes[1].legend(handles, ["vegetated fields (T1)", "sand bars (T2)", "water (T1)", "tent blocks (T1)", "bridges (T1)"], loc="lower right")
fig.suptitle(f"Rule-based feature layers over Sentinel-2 natural colour, 2025-02-16  ({SRC.name})", fontsize=13)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "features_overview.png", dpi=65)
print("saved features_overview.png from", SRC.name)
