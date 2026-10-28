"""Phase 8 (brief item 6): georeferencing demonstration with GCPs, three transforms and RMSE on independent check points.

1. Make an UNREFERENCED image (stand-in for a scanned sector map): 6 x 6 km crop of the T1 natural-colour composite,
   rotated 4 deg, rescaled to 8.5 m/px and given a mild non-linear (quadratic) warp, saved with no georeferencing.
2. Find tie points automatically: SIFT features + ratio test + RANSAC (affine) between it and the georeferenced S2 image.
3. Pick 15 well-spread GCPs and 10 separate independent CHECK points.
4. Fit polynomial order 1, polynomial order 2 and thin plate spline (pixel -> map); report RMSE on GCPs and check points.
5. Write the georeferenced result (polynomial 2, GDAL warp, nearest neighbour), a QGIS Georeferencer .points file and a
   residual-vector figure.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from osgeo import gdal, osr
from rasterio.windows import from_bounds
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import map_coordinates
from skimage.color import rgb2gray
from skimage.feature import SIFT, match_descriptors
from skimage.measure import ransac
from skimage.transform import AffineTransform

gdal.UseExceptions()
ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "04_coreg" / "georef_demo"
OUT.mkdir(parents=True, exist_ok=True)
WIN = (587000, 2811000, 593000, 2817000)  # 6 x 6 km around the Sangam
rng = np.random.default_rng(42)

with rasterio.open(ROOT / "03_enhanced" / "S2" / "S2_20250216_natural_p2-98.tif") as src:
    win = from_bounds(*WIN, src.transform)
    ref = src.read(window=win).transpose(1, 2, 0)            # 600 x 600 x 3, 10 m
    ref_tf = src.window_transform(win)

# ---------- 1. synthetic "scanned map": rotate 4 deg, 8.5 m/px, quadratic warp ----------
H = W = 720
ang = np.deg2rad(4)
scale = 8.5 / 10.0
yy, xx = np.mgrid[0:H, 0:W].astype(float)
u, v = (xx - W / 2) / W, (yy - H / 2) / H                   # -0.5..0.5
xr = (np.cos(ang) * (xx - W / 2) - np.sin(ang) * (yy - H / 2)) * scale + 300 + 6 * (u ** 2 - v * u)
yr = (np.sin(ang) * (xx - W / 2) + np.cos(ang) * (yy - H / 2)) * scale + 300 + 6 * (v ** 2 + 0.5 * u * v)
scan = np.stack([map_coordinates(ref[..., k].astype(float), [yr, xr], order=1, cval=255) for k in range(3)], -1).astype("uint8")
scan_path = OUT / "unreferenced_sector_map.tif"
gdal.GetDriverByName("GTiff").Create(str(scan_path), W, H, 3, gdal.GDT_Byte)  # placeholder to get a plain file
ds = gdal.Open(str(scan_path), gdal.GA_Update)
for k in range(3):
    ds.GetRasterBand(k + 1).WriteArray(scan[..., k])
ds = None  # no geotransform, no CRS: truly unreferenced


def true_map(col, row):
    """Ground truth for this synthetic image: pixel (col,row) of the scan -> map X,Y (only possible because we made it)."""
    uu, vv = (col - W / 2) / W, (row - H / 2) / H
    c = (np.cos(ang) * (col - W / 2) - np.sin(ang) * (row - H / 2)) * scale + 300 + 6 * (uu ** 2 - vv * uu)
    r = (np.sin(ang) * (col - W / 2) + np.cos(ang) * (row - H / 2)) * scale + 300 + 6 * (vv ** 2 + 0.5 * uu * vv)
    return ref_tf * (c + 0.5, r + 0.5)


# ---------- 2. automatic tie points ----------
sift_s, sift_r = SIFT(), SIFT()
sift_s.detect_and_extract(rgb2gray(scan))
sift_r.detect_and_extract(rgb2gray(ref))
m = match_descriptors(sift_s.descriptors, sift_r.descriptors, max_ratio=0.7, cross_check=True)
src_pts = sift_s.keypoints[m[:, 0]][:, ::-1]               # (col, row) in the scan
dst_px = sift_r.keypoints[m[:, 1]][:, ::-1]                # (col, row) in the reference
_, inl = ransac((src_pts, dst_px), AffineTransform, min_samples=3, residual_threshold=2.0, max_trials=2000)
src_pts, dst_px = src_pts[inl], dst_px[inl]
X, Y = ref_tf * (dst_px[:, 0] + 0.5, dst_px[:, 1] + 0.5)
dst_map = np.column_stack([X, Y])
print(f"SIFT matches {len(m)}, RANSAC inliers {inl.sum()}")

# ---------- 3. 15 well-spread GCPs (one per 4x4 grid cell where possible) + 10 check points ----------
cell = (src_pts // (W / 4)).astype(int)
cell_id = cell[:, 1] * 4 + cell[:, 0]
order = rng.permutation(len(src_pts))
gcp_idx, used = [], set()
for i in order:
    if cell_id[i] not in used and len(gcp_idx) < 15:
        gcp_idx.append(i); used.add(cell_id[i])
rest = [i for i in order if i not in gcp_idx]
chk_idx = rest[:10]
G, C = np.array(gcp_idx), np.array(chk_idx)


def design(p, order):
    c, r = p[:, 0] / W, p[:, 1] / H
    cols = [np.ones_like(c), c, r]
    if order == 2:
        cols += [c * c, c * r, r * r]
    return np.column_stack(cols)


def fit(method):
    if method.startswith("poly"):
        o = int(method[-1])
        coef, *_ = np.linalg.lstsq(design(src_pts[G], o), dst_map[G], rcond=None)
        return lambda p: design(p, o) @ coef
    rbf = RBFInterpolator(src_pts[G], dst_map[G], kernel="thin_plate_spline")
    return rbf


rows = []
grid = np.column_stack([g.ravel() for g in np.mgrid[20:W - 20:20, 20:H - 20:20]])
truth_grid = np.column_stack(true_map(grid[:, 0], grid[:, 1]))
for method, label in (("poly1", "Polynomial 1 (affine)"), ("poly2", "Polynomial 2"), ("tps", "Thin plate spline")):
    f = fit(method)
    res_g = f(src_pts[G]) - dst_map[G]
    res_c = f(src_pts[C]) - dst_map[C]
    true_err = f(grid.astype(float)) - truth_grid
    rmse = lambda r: float(np.sqrt((r ** 2).sum(1).mean()))
    rows.append({"transform": label, "n_gcp": len(G), "rmse_gcp_m": rmse(res_g), "rmse_gcp_px": rmse(res_g) / 10,
                 "n_check": len(C), "rmse_check_m": rmse(res_c), "rmse_check_px": rmse(res_c) / 10,
                 "rmse_true_grid_m": rmse(true_err), "max_true_err_m": float(np.sqrt((true_err ** 2).sum(1)).max())})
    if method == "poly2":
        best_res_g, best_res_c = res_g, res_c
df = pd.DataFrame(rows).round(2)
df.to_csv(ROOT / "09_docs" / "georef_rmse.csv", index=False)
print(df.to_string(index=False))

# ---------- 4. georeferenced output (polynomial 2) with GDAL, and the QGIS .points file ----------
srs = osr.SpatialReference(); srs.ImportFromEPSG(32644)
gcps = [gdal.GCP(float(dst_map[i, 0]), float(dst_map[i, 1]), 0, float(src_pts[i, 0]), float(src_pts[i, 1])) for i in G]
tmp = gdal.Translate("/vsimem/gcp.tif", str(scan_path), GCPs=gcps, outputSRS=srs.ExportToWkt())
gdal.Warp(str(OUT / "sector_map_georef_poly2.tif"), tmp, polynomialOrder=2, resampleAlg="near", dstSRS="EPSG:32644",
          xRes=10, yRes=10, targetAlignedPixels=True, dstNodata=0, creationOptions=["COMPRESS=DEFLATE"])
with open(OUT / "unreferenced_sector_map.tif.points", "w") as f:
    f.write('#CRS: PROJCRS["WGS 84 / UTM zone 44N",ID["EPSG",32644]]\n')
    f.write("mapX,mapY,sourceX,sourceY,enable,dX,dY,residual\n")
    for k, i in enumerate(G):
        dx, dy = best_res_g[k]
        f.write(f"{dst_map[i, 0]:.2f},{dst_map[i, 1]:.2f},{src_pts[i, 0]:.2f},{-src_pts[i, 1]:.2f},1,{dx:.2f},{dy:.2f},{np.hypot(dx, dy):.2f}\n")
pd.DataFrame({"type": ["GCP"] * len(G) + ["check"] * len(C),
              "src_col": np.r_[src_pts[G, 0], src_pts[C, 0]], "src_row": np.r_[src_pts[G, 1], src_pts[C, 1]],
              "map_X": np.r_[dst_map[G, 0], dst_map[C, 0]], "map_Y": np.r_[dst_map[G, 1], dst_map[C, 1]],
              "res_E_m_poly2": np.r_[best_res_g[:, 0], best_res_c[:, 0]], "res_N_m_poly2": np.r_[best_res_g[:, 1], best_res_c[:, 1]]}
             ).round(2).to_csv(ROOT / "09_docs" / "georef_points.csv", index=False)

# ---------- 5. figure: scan with GCPs, reference with points, residual vectors ----------
fig, ax = plt.subplots(1, 3, figsize=(18, 6.3))
ax[0].imshow(scan); ax[0].scatter(*src_pts[G].T, c="yellow", s=30, label="GCP"); ax[0].scatter(*src_pts[C].T, c="cyan", marker="s", s=30, label="check")
ax[0].set_title("Unreferenced 'scanned' sector map (pixel space)"); ax[0].legend()
ax[1].imshow(ref, extent=(WIN[0], WIN[2], WIN[1], WIN[3])); ax[1].scatter(*dst_map[G].T, c="yellow", s=30); ax[1].scatter(*dst_map[C].T, c="cyan", marker="s", s=30)
ax[1].set_title("Reference: Sentinel-2 T1, EPSG:32644"); ax[1].ticklabel_format(style="plain"); ax[1].tick_params(labelsize=7)
ax[2].quiver(*dst_map[G].T, *best_res_g.T, color="orange", angles="xy", scale_units="xy", scale=0.01, label="GCP residual")
ax[2].quiver(*dst_map[C].T, *best_res_c.T, color="blue", angles="xy", scale_units="xy", scale=0.01, label="check residual")
ax[2].set_xlim(WIN[0], WIN[2]); ax[2].set_ylim(WIN[1], WIN[3]); ax[2].set_aspect("equal"); ax[2].legend(loc="lower right")
ax[2].set_title("Polynomial 2 residual vectors (exaggerated x100)"); ax[2].ticklabel_format(style="plain"); ax[2].tick_params(labelsize=7)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "georef_demo.png", dpi=70)
print("saved georef outputs")
