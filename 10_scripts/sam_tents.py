"""Phase 14: SAM-assisted digitising of tent blocks (what the GeoAI / Geo-SAM plugins do), scored against the classical layers.

Image: Sentinel-2 2025-02-16 natural colour (2-98 % display copy), 2 x 2 km tiles (200 x 200 px) where the change-based
tent blocks cover >= 20 % of the tile. Prompts imitate an operator: 5 clicks inside tent blocks and 5 outside, placed at
random (fixed seed) on eroded masks. SAM ViT-B (Meta, sam_vit_b_01ec64.pth) runs on CPU in sam_worker.py.
Scores per tile: IoU of the SAM mask with (a) the change-based tent blocks (Phase 10) and (b) the Random Forest
'fused + temporal + change rule' tent class (Phase 13); time per tile. Neither reference is ground truth.
Outputs: 07_analysis/ai/sam_tents_T1.tif + .gpkg, 09_docs/sam_tents_scores.csv, sam_tents.png
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, shapes
from scipy import ndimage as ndi
from shapely.geometry import shape

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "07_analysis" / "ai"
OUT.mkdir(parents=True, exist_ok=True)
CKPT = r"D:\conda_envs\sareo\sam_models\sam_vit_b_01ec64.pth"
TILE = 200
rng = np.random.default_rng(3)

with rasterio.open(ROOT / "03_enhanced" / "S2" / "S2_20250216_natural_p2-98.tif") as s:
    rgb = s.read().transpose(1, 2, 0)
    prof, tf, shp = s.profile, s.transform, (s.height, s.width)
tb = gpd.read_file(ROOT / "06_vectors" / "kumbh_features.gpkg", layer="tent_blocks")
ref_rule = geometry_mask(tb.geometry, out_shape=shp, transform=tf, invert=True)
with rasterio.open(ROOT / "07_analysis" / "classification" / "RF_Fused_plus_temporal_plus_change_rule_T1.tif") as s:
    ref_rf = s.read(1) == 2

tiles, pack = [], {}
for r0 in range(0, shp[0] - TILE + 1, TILE):
    for c0 in range(0, shp[1] - TILE + 1, TILE):
        m = ref_rule[r0:r0 + TILE, c0:c0 + TILE]
        if m.mean() < 0.2:
            continue
        inside = np.argwhere(ndi.binary_erosion(m, iterations=4))
        outside = np.argwhere(ndi.binary_erosion(~m, iterations=4))
        if len(inside) < 5 or len(outside) < 5:
            continue
        p_in = inside[rng.choice(len(inside), 5, replace=False)][:, ::-1]   # (row, col) -> (x, y)
        p_out = outside[rng.choice(len(outside), 5, replace=False)][:, ::-1]
        i = len(tiles)
        pack[f"img_{i}"] = np.ascontiguousarray(rgb[r0:r0 + TILE, c0:c0 + TILE])
        pack[f"pts_{i}"] = np.vstack([p_in, p_out])
        pack[f"lab_{i}"] = np.array([1] * 5 + [0] * 5)
        tiles.append((r0, c0))
print(f"{len(tiles)} tiles of 2 x 2 km with >= 20 % tent blocks")

with tempfile.TemporaryDirectory() as tmp:
    np.savez(Path(tmp) / "tiles.npz", **pack)
    res = subprocess.run([sys.executable, "-I", str(ROOT / "10_scripts" / "sam_worker.py"), str(Path(tmp) / "tiles.npz"), CKPT,
                          str(Path(tmp) / "out.npz")], capture_output=True, text=True)
    if res.returncode:
        sys.exit(res.stderr[-2000:])
    print(res.stdout.strip())
    out = dict(np.load(Path(tmp) / "out.npz"))

sam_full = np.zeros(shp, bool)
rows = []
iou = lambda a, b: (a & b).sum() / max((a | b).sum(), 1)
for i, (r0, c0) in enumerate(tiles):
    m = out[f"mask_{i}"].astype(bool)
    sam_full[r0:r0 + TILE, c0:c0 + TILE] = m
    a, b = ref_rule[r0:r0 + TILE, c0:c0 + TILE], ref_rf[r0:r0 + TILE, c0:c0 + TILE]
    rows.append({"tile": i, "row0": r0, "col0": c0, "tent_fraction_rule": round(a.mean(), 3), "sam_fraction": round(m.mean(), 3),
                 "IoU_vs_rule": round(iou(m, a), 3), "IoU_vs_RF": round(iou(m, b), 3), "IoU_rule_vs_RF": round(iou(a, b), 3),
                 "sam_score": round(float(out[f"score_{i}"]), 3), "seconds": round(float(out["seconds"][i]), 1)})
df = pd.DataFrame(rows)
df.to_csv(ROOT / "09_docs" / "sam_tents_scores.csv", index=False)
p = prof.copy(); p.update(count=1, dtype="uint8", nodata=0, photometric=None)
p.pop("photometric", None)
with rasterio.open(OUT / "sam_tents_T1.tif", "w", **p) as d:
    d.write(sam_full.astype("uint8"), 1)
polys = [shape(g) for g, v in shapes(sam_full.astype("uint8"), mask=sam_full, transform=tf) if v == 1]
gpd.GeoDataFrame(geometry=polys, crs=prof["crs"]).assign(
    **{"class": "tent_block", "method": "SAM ViT-B, 5+5 point prompts per 2 km tile", "confidence": "medium"}
).to_file(OUT / "sam_tents_T1.gpkg", driver="GPKG")
print(df.to_string(index=False))
print(f"mean IoU vs rule {df.IoU_vs_rule.mean():.3f} | vs RF {df.IoU_vs_RF.mean():.3f} | rule vs RF {df.IoU_rule_vs_RF.mean():.3f} | "
      f"{df.seconds.mean():.1f} s per 4 km2 tile = {df.seconds.mean() / 4:.1f} s/km2 on CPU, 10 clicks per tile")

show = df.sort_values("tent_fraction_rule", ascending=False).head(4)
fig, axes = plt.subplots(2, len(show), figsize=(4.2 * len(show), 8.4))
for j, (_, r) in enumerate(show.iterrows()):
    r0, c0 = int(r.row0), int(r.col0)
    img = rgb[r0:r0 + TILE, c0:c0 + TILE]
    axes[0, j].imshow(img); axes[0, j].contour(ref_rule[r0:r0 + TILE, c0:c0 + TILE], [0.5], colors="yellow", linewidths=1)
    pts = pack[f"pts_{int(r.tile)}"]; lab = pack[f"lab_{int(r.tile)}"]
    axes[0, j].scatter(pts[lab == 1, 0], pts[lab == 1, 1], c="lime", s=25, marker="+"); axes[0, j].scatter(pts[lab == 0, 0], pts[lab == 0, 1], c="red", s=25, marker="x")
    axes[0, j].set_title(f"tile {int(r.tile)}: clicks + rule outline (yellow)", fontsize=9)
    axes[1, j].imshow(img); axes[1, j].imshow(np.ma.masked_equal(sam_full[r0:r0 + TILE, c0:c0 + TILE].astype(int), 0), cmap="autumn", alpha=0.45)
    axes[1, j].set_title(f"SAM mask, IoU vs rule {r.IoU_vs_rule:.2f}", fontsize=9)
    for ax in axes[:, j]:
        ax.axis("off")
fig.suptitle("SAM ViT-B point-prompted tent-block segmentation on Sentinel-2 T1 (2 x 2 km tiles)", fontsize=12)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "sam_tents.png", dpi=70)
