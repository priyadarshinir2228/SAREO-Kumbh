"""Crop a SNAP terrain-corrected Sentinel-1 GeoTIFF to the exact AOI grid, name bands, set NoData (NaN).

Usage: python finalize_s1.py <snap_output.tif> <final.tif>
The SNAP graph aligns pixels to the 10 m grid (alignToStandardGrid, origin 0,0), so this is a pure crop
(no resampling). Band order from the graph is VH, VV (selectedPolarisations=VH,VV).
"""
import sys

import numpy as np
import rasterio
from rasterio.windows import from_bounds

AOI = (582400, 2807200, 596600, 2821000)  # EPSG:32644, multiples of 10 m
src_path, dst_path = sys.argv[1], sys.argv[2]

with rasterio.open(src_path) as src:
    t = src.transform
    off_x, off_y = t.c % 10, t.f % 10
    if min(off_x, 10 - off_x) > 0.01 or min(off_y, 10 - off_y) > 0.01:
        sys.exit(f"grid not aligned to 10 m (origin offset {off_x:.2f}, {off_y:.2f}); check alignToStandardGrid")
    win = from_bounds(*AOI, transform=t).round_offsets().round_lengths()
    data = src.read(window=win, boundless=True, fill_value=0).astype("float32")
    profile = src.profile.copy()
    profile.update(
        driver="GTiff", height=data.shape[1], width=data.shape[2], transform=src.window_transform(win),
        dtype="float32", nodata=np.nan, compress="deflate", predictor=3, tiled=True, blockxsize=256, blockysize=256,
        BIGTIFF="IF_SAFER",
    )
    profile.pop("photometric", None)

data[(data == 0) | ~np.isfinite(data)] = np.nan
with rasterio.open(dst_path, "w", **profile) as dst:
    dst.write(data)
    for i, name in enumerate(["Sigma0_VH", "Sigma0_VV"][: data.shape[0]], 1):
        dst.set_band_description(i, name)
    dst.update_tags(SOURCE=src_path.split("\\")[-1], PROCESSING="SNAP 14 S1_preproc graph; cropped to AOI_Kumbh")
nan_pct = 100 * np.isnan(data).mean()
print(f"  final {dst_path.split(chr(92))[-1]}: {data.shape[2]}x{data.shape[1]} px, NoData {nan_pct:.2f}%")
