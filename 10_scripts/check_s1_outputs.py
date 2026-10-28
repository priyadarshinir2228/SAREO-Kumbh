"""Phase 5 checks on preprocessed Sentinel-1 rasters in 02_preproc/S1 (brief 2.1 / 2.2).

For each *_dB.tif: CRS, pixel size, grid origin, AOI coverage, NoData share, per-band dB statistics.
Alignment test: backscatter on OSM bridges (should be bright) vs inside OSM water areas (should be dark),
and the same on a copy shifted by 1-3 pixels (alignment is good if the unshifted contrast is the largest).
Writes 09_docs/s1_output_check.csv.
"""
import csv
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask

ROOT = Path(r"D:\SAREO-Kumbh")
AOI = (582400, 2807200, 596600, 2821000)
osm = ROOT / "06_vectors" / "osm.gpkg"
bridges = gpd.read_file(osm, layer="bridges")
bridges = bridges[bridges["highway"].notna()].buffer(6)  # road bridges as thin polygons
water = gpd.read_file(osm, layer="water_areas").buffer(-60)  # stay well inside the water
water = water[~water.is_empty]

rows = []
for tif in sorted((ROOT / "02_preproc" / "S1").glob("*_dB.tif")):
    with rasterio.open(tif) as src:
        t = src.transform
        b = src.bounds
        info = {
            "file": tif.name,
            "crs": src.crs.to_string(),
            "pixel_m": f"{t.a:.2f} x {-t.e:.2f}",
            "size_px": f"{src.width} x {src.height}",
            "origin_mod10": f"{b.left % 10:.2f}, {b.top % 10:.2f}",
            "covers_aoi": b.left <= AOI[0] + 10 and b.bottom <= AOI[1] + 10 and b.right >= AOI[2] - 10 and b.top >= AOI[3] - 10,
            "bands": "|".join(src.descriptions[i] or f"band{i+1}" for i in range(src.count)),
        }
        bmask = geometry_mask(bridges, out_shape=src.shape, transform=t, invert=True)
        wmask = geometry_mask(water, out_shape=src.shape, transform=t, invert=True)
        for i in range(src.count):
            a = src.read(i + 1).astype("float64")
            nod = ~np.isfinite(a) | (a == 0) | (a == src.nodata if src.nodata is not None else False)
            v = a[~nod]
            name = (src.descriptions[i] or f"b{i+1}").replace("Sigma0_", "")
            info[f"{name}_nodata_pct"] = round(100 * nod.mean(), 2)
            info[f"{name}_p2_median_p98_dB"] = "{:.1f} / {:.1f} / {:.1f}".format(*np.percentile(v, [2, 50, 98]))
            # alignment: bridge minus water contrast, at offsets of 0..3 px in x
            contrasts = []
            for dx in range(0, 4):
                sh = np.roll(a, dx, axis=1)
                contrasts.append(np.nanmedian(sh[bmask & ~nod]) - np.nanmedian(sh[wmask & ~nod]))
            info[f"{name}_bridge_minus_water_dB"] = round(contrasts[0], 1)
            info[f"{name}_contrast_shift1_3px"] = "/".join(f"{c:.1f}" for c in contrasts[1:])
    rows.append(info)
    print(info)

if rows:
    out = ROOT / "09_docs" / "s1_output_check.csv"
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("saved", out)
