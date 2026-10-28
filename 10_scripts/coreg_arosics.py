"""Phase 8: AROSICS co-registration statistics (Scheffler et al. 2017).

  1. S2 B08 T0 -> T1 and T2 -> T1  (same sensor)          global COREG + local COREG_LOCAL grid (500 m)
  2. S1 VV dB (Lee 7x7) T1 -> S2 B08 T1 (cross-sensor)    local grid; AROSICS is designed for optical, so this is a
     plausibility test - only windows that pass its reliability filters count
Nothing is resampled here: only shifts and their statistics are measured (09_docs/coreg_arosics.csv, coreg_tiepoints_*.gpkg).
"""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from arosics import COREG, COREG_LOCAL

ROOT = Path(r"D:\SAREO-Kumbh")
S1 = ROOT / "02_preproc" / "S1"
S2 = ROOT / "02_preproc" / "S2"
TMP = Path(tempfile.mkdtemp())


def single_band(src_path, band, name, to_db=False):
    """AROSICS wants a plain single-band raster without NaN."""
    with rasterio.open(src_path) as s:
        a = s.read(band).astype("float32")
        p = s.profile
    a = np.where(np.isfinite(a), a, np.nanmedian(a))
    p.update(count=1, nodata=None, compress="deflate")
    out = TMP / f"{name}.tif"
    with rasterio.open(out, "w", **p) as d:
        d.write(a, 1)
    return str(out)


ref_s2 = single_band(S2 / "S2_20250216_L2A_refl10m.tif", 7, "s2_T1_B08")
pairs = [
    ("S2 B08 T0 20241113 -> S2 B08 T1", single_band(S2 / "S2_20241113_L2A_refl10m.tif", 7, "s2_T0_B08"), ref_s2),
    ("S2 B08 T2 20250417 -> S2 B08 T1", single_band(S2 / "S2_20250417_L2A_refl10m.tif", 7, "s2_T2_B08"), ref_s2),
    ("S1 VV T1 20250216 -> S2 B08 T1", single_band(S1 / "S1A_20250216_Sig0_lee7_dB.tif", 2, "s1_T1_VV"), ref_s2),
]
rows = []
for label, tgt, ref in pairs:
    row = {"pair": label}
    if label.startswith("S2"):
        g = COREG(ref, tgt, ws=(512, 512), max_shift=10, q=True, nodata=(None, None))
        g.calculate_spatial_shifts()
        row.update(global_shift_E_m=round(g.x_shift_map, 2), global_shift_N_m=round(g.y_shift_map, 2),
                   global_reliability_pct=round(g.shift_reliability, 1), global_ssim_improved=g.ssim_improved)
    loc = COREG_LOCAL(ref, tgt, grid_res=50, window_size=(128, 128), max_shift=10, q=True, nodata=(None, None),
                      tieP_filter_level=3, min_reliability=60)
    tp = loc.CoRegPoints_table
    good = tp[tp["OUTLIER"] == False] if "OUTLIER" in tp else tp  # noqa: E712
    good = good[np.isfinite(good["X_SHIFT_M"]) & (good["X_SHIFT_M"] != -9999)]
    shift = np.hypot(good["X_SHIFT_M"], good["Y_SHIFT_M"])
    row.update(tiepoints_total=len(tp), tiepoints_valid=len(good),
               median_shift_E_m=round(good["X_SHIFT_M"].median(), 2), median_shift_N_m=round(good["Y_SHIFT_M"].median(), 2),
               rmse_m=round(float(np.sqrt((shift ** 2).mean())), 2) if len(good) else np.nan,
               p90_abs_shift_m=round(float(np.percentile(shift, 90)), 2) if len(good) else np.nan)
    tag = label.split(" ->")[0].replace(" ", "_")
    if len(good):
        loc.tiepoint_grid.to_PointShapefile(path_out=str(TMP / f"{tag}.shp"))
        import geopandas as gpd
        gpd.read_file(TMP / f"{tag}.shp").to_file(ROOT / "06_vectors" / "coreg_tiepoints.gpkg", layer=tag, driver="GPKG")
    rows.append(row)
    print(row)

pd.DataFrame(rows).to_csv(ROOT / "09_docs" / "coreg_arosics.csv", index=False)
