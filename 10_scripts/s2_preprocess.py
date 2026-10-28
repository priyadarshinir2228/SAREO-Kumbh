"""Phase 7 (brief 3.1): Sentinel-2 L2A -> 10 m surface-reflectance stack on the AOI grid, with cloud/shadow mask.

Per date (T0 2024-11-13, T1 2025-02-16, T2 2025-04-17), reading straight from the zip (/vsizip/, no unpacking):
  * reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION  (offset and quantification read from MTD_MSIL2A.xml)
  * 10 m bands (B02 B03 B04 B08) read as is; 20 m bands (B05 B06 B07 B8A B11 B12) resampled to 10 m, bilinear;
    SCL resampled with nearest neighbour (categorical)
  * mask: invalid where DN = 0 or SCL in {0 no data, 1 saturated, 3 cloud shadow, 8 cloud medium, 9 cloud high, 10 cirrus}
  * clip = exact AOI window (tile 44RNP is UTM 44N, origin on the 20 m grid, so no reprojection is needed)
Outputs (02_preproc/S2): S2_<date>_L2A_refl10m.tif (10 bands Float32, NaN = masked), S2_<date>_SCL10m.tif, S2_<date>_mask10m.tif
"""
import re
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

ROOT = Path(r"D:\SAREO-Kumbh")
AOI = (582400, 2807200, 596600, 2821000)
W, H = (AOI[2] - AOI[0]) // 10, (AOI[3] - AOI[1]) // 10
BANDS = [("B02", 10), ("B03", 10), ("B04", 10), ("B05", 20), ("B06", 20), ("B07", 20), ("B08", 10), ("B8A", 20), ("B11", 20), ("B12", 20)]
MASK_SCL = [0, 1, 3, 8, 9, 10]
OUT = ROOT / "02_preproc" / "S2"
OUT.mkdir(parents=True, exist_ok=True)


def read_window(path, res, resampling):
    with rasterio.open(path) as src:
        win = from_bounds(*AOI, transform=src.transform)
        data = src.read(1, window=win, out_shape=(H, W), resampling=resampling)
        if res == 10:
            transform = src.window_transform(win)
        else:
            transform = rasterio.transform.from_origin(AOI[0], AOI[3], 10, 10)
        return data, transform, src.crs


for z in sorted((ROOT / "01_raw" / "S2").glob("S2*_MSIL2A_*.zip")):
    date = z.name[11:19]
    names = zipfile.ZipFile(z).namelist()
    mtd = zipfile.ZipFile(z).read(next(n for n in names if n.endswith("MTD_MSIL2A.xml"))).decode()
    quant = float(re.search(r"<BOA_QUANTIFICATION_VALUE[^>]*>(\d+)<", mtd).group(1))
    offsets = {int(b): float(v) for b, v in re.findall(r'BOA_ADD_OFFSET band_id="(\d+)">(-?\d+)<', mtd)}
    band_ids = {"B01": 0, "B02": 1, "B03": 2, "B04": 3, "B05": 4, "B06": 5, "B07": 6, "B08": 7, "B8A": 8, "B09": 9, "B10": 10, "B11": 11, "B12": 12}

    def member(band, res):
        return "/vsizip/" + str(z).replace("\\", "/") + "/" + next(n for n in names if n.endswith(f"_{band}_{res}m.jp2"))

    scl, transform, crs = read_window(member("SCL", 20), 20, Resampling.nearest)
    stack, dn_zero = [], np.zeros((H, W), bool)
    for band, res in BANDS:
        dn, t, _ = read_window(member(band, res), res, Resampling.bilinear)
        assert t.c == AOI[0] and t.f == AOI[3] and dn.shape == (H, W), f"{band} not on AOI grid"
        dn_zero |= dn == 0
        stack.append((dn.astype("float32") + offsets[band_ids[band]]) / quant)
    stack = np.stack(stack)
    masked = dn_zero | np.isin(scl, MASK_SCL)
    stack[:, masked] = np.nan

    profile = dict(driver="GTiff", width=W, height=H, crs=crs, transform=transform, compress="deflate", tiled=True,
                   blockxsize=256, blockysize=256)
    with rasterio.open(OUT / f"S2_{date}_L2A_refl10m.tif", "w", count=len(BANDS), dtype="float32", nodata=np.nan,
                       predictor=3, **profile) as dst:
        dst.write(stack)
        for i, (band, _) in enumerate(BANDS, 1):
            dst.set_band_description(i, band)
        dst.update_tags(SOURCE=z.name, REFLECTANCE=f"(DN + {offsets[band_ids['B04']]:.0f}) / {quant:.0f}",
                        MASKED_SCL=",".join(map(str, MASK_SCL)), RESAMPLING_20M="bilinear")
    with rasterio.open(OUT / f"S2_{date}_SCL10m.tif", "w", count=1, dtype="uint8", nodata=0, **profile) as dst:
        dst.write(scl.astype("uint8"), 1)
        dst.set_band_description(1, "SCL")
    with rasterio.open(OUT / f"S2_{date}_mask10m.tif", "w", count=1, dtype="uint8", nodata=255, **profile) as dst:
        dst.write((~masked).astype("uint8"), 1)
        dst.set_band_description(1, "1=clear 0=masked")

    counts = {c: int((scl == c).sum()) for c in np.unique(scl)}
    print(f"{date}: masked {100 * masked.mean():.3f}%  SCL classes {counts}")
    print(f"   median reflectance B02..B12: " + " ".join(f"{np.nanmedian(b):.3f}" for b in stack))
