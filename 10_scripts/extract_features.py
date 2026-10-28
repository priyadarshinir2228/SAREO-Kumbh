"""Phase 10: rule-based feature extraction from the lossless SAR + EO stacks (first draft of the feature database;
refine by hand in QGIS where needed - every feature carries method + confidence so edits stay traceable).

Rules (Lee 7x7 sigma0 dB, S2 reflectance/indices; thresholds documented in 09_docs/10_Vector_Database.md):
  water (per epoch)      : MNDWI > 0  OR  (VV < -18 dB AND MNDWI > -0.25); T0 uses S1 2024-11-12 + S2 2024-11-13
  tent_block (T1)        : VV_T1 - VV_T0 >= +3 dB (new strong scatterers) AND VV_T2 - VV_T1 <= -2 dB (gone afterwards)
                           AND not water at T1 AND NDVI_T0 < 0.3 (was bare floodplain, not crops)
  pontoon_bridge (T1)    : VV_T1 > -6 dB inside the T0/T1 channel, elongated (L/W >= 4, >= 80 m), at least 40 % of the
                           line over T1 water -> centre line; presence at T0 / T2 stored as attributes
  sand_bar (T2)          : not water, NDVI_T2 < 0.15, MNDWI_T2 < 0, VV_T2 < -14 dB, inside the floodplain envelope
  veg_field (T1)         : NDVI_T1 > 0.45
Cleaning: binary opening/closing, minimum area per class, polygonise, simplify 10 m, clip to AOI.
Output: 06_vectors/extracted_raw.gpkg (one layer per class)
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from scipy import ndimage as ndi
from shapely.geometry import LineString, shape

ROOT = Path(r"D:\SAREO-Kumbh")
F = ROOT / "05_fused"
OUT = ROOT / "06_vectors" / "extracted_raw.gpkg"
EPOCHS = {"T0": "20241113", "T1": "20250216", "T2": "20250417"}
S1DATE = {"T0": "2024-11-12", "T1": "2025-02-16", "T2": "2025-04-17"}

st = {}
for ep, d in EPOCHS.items():
    with rasterio.open(F / f"fused_stack_{ep}_{d}.tif") as s:
        st[ep] = {s.descriptions[i]: s.read(i + 1) for i in range(s.count)}
        transform, crs = s.transform, s.crs
vv = {ep: np.nan_to_num(st[ep]["VV_dB"], nan=-30) for ep in st}
ndvi = {ep: np.nan_to_num(st[ep]["NDVI"], nan=0) for ep in st}
mndwi = {ep: np.nan_to_num(st[ep]["MNDWI"], nan=-1) for ep in st}


def clean(mask, open_px=1, close_px=2, min_ha=0.5):
    m = ndi.binary_opening(mask, iterations=open_px) if open_px else mask
    m = ndi.binary_closing(m, iterations=close_px) if close_px else m
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, np.nonzero(sizes * 100 / 1e4 >= min_ha)[0] + 1)
    return ndi.binary_fill_holes(keep) if min_ha >= 1 else keep


def polygons(mask, attrs):
    geoms = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=transform) if v == 1]
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)
    gdf["geometry"] = gdf.simplify(10, preserve_topology=True).buffer(0)
    for k, v in attrs.items():
        gdf[k] = v
    return gdf


layers = {}
water = {}
for ep in st:
    # Narrow channels crossed by dense pontoon bridges stay above -18 dB in Lee 7x7 SAR, so clear optical water
    # (MNDWI > 0) is accepted on its own and SAR adds dark water that MNDWI misses
    water[ep] = clean((mndwi[ep] > 0) | ((vv[ep] < -18) & (mndwi[ep] > -0.25)), 1, 2, 1.0)
    layers[f"water_{ep}"] = polygons(water[ep], {"class": "water", "sub_class": "river channel", "epoch": ep,
                                                 "date": S1DATE[ep], "sensor": "S1A + S2", "confidence": "high",
                                                 "method": "rule: MNDWI > 0 or (VV < -18 dB and MNDWI > -0.25)"})

floodplain = ndi.binary_dilation(water["T0"] | water["T1"] | water["T2"], iterations=150)  # 1.5 km envelope
tents = (vv["T1"] - vv["T0"] >= 3) & (vv["T2"] - vv["T1"] <= -2) & ~water["T1"] & (ndvi["T0"] < 0.3) & floodplain
tents = clean(tents, 1, 3, 1.0)
layers["tent_blocks"] = polygons(tents, {"class": "tent_block", "sub_class": "tent sector (block level)", "epoch": "T1",
                                         "date": "2025-02-16", "sensor": "S1A (T0/T1/T2) + S2", "confidence": "medium",
                                         "method": "rule: dVV(T1-T0) >= +3 dB, dVV(T2-T1) <= -2 dB, NDVI_T0 < 0.3, not water"})

# Pontoon bridges: dense bridges break up the T1 water mask, and some bridges already stood at T0 / still stood at T2,
# so search inside the widest channel (T0 or T1 water, eroded 1 px to cut links to the banks) and record presence
# at T0 / T2 as attributes instead of filtering on it.
channel = ndi.binary_erosion(ndi.binary_closing(water["T0"] | water["T1"], iterations=3), iterations=1)
channel_t1 = ndi.binary_closing(water["T1"], iterations=3)  # T1 channel with the gaps under bridges closed
# (tried: unfiltered VV with line-max filter -> speckle blobs fail the elongation test, 3 bridges; Lee 7x7 kept, 5 bridges)
bridge_px = (vv["T1"] > -6) & channel
lab, n = ndi.label(bridge_px)
lines, present = [], []
for i in range(1, n + 1):
    rr, cc = np.nonzero(lab == i)
    if len(rr) < 8:
        continue
    xy = np.column_stack([cc, rr]).astype(float)
    centre = xy.mean(0)
    _, sv, vt = np.linalg.svd(xy - centre, full_matrices=False)
    proj = (xy - centre) @ vt[0]
    length, width = proj.max() - proj.min() + 1, 2 * sv[1] / np.sqrt(len(rr)) + 1
    if length / width < 4:
        continue
    if length * 10 < 80:  # shorter than 80 m: boats, buoys, bank fragments
        continue
    ends = [centre + vt[0] * proj.min(), centre + vt[0] * proj.max()]
    t = np.linspace(0, 1, 50)
    samp = np.outer(1 - t, ends[0]) + np.outer(t, ends[1])  # (col, row) along the line
    sc = np.clip(np.round(samp[:, 0]).astype(int), 0, channel_t1.shape[1] - 1)
    sr = np.clip(np.round(samp[:, 1]).astype(int), 0, channel_t1.shape[0] - 1)
    if channel_t1[sr, sc].mean() < 0.4:  # T0 floodplain that was dry land at T1: tent rows, not bridges
        continue
    lines.append(LineString([transform * (p[0] + 0.5, p[1] + 0.5) for p in ends]))
    present.append({ep: bool(np.median(vv[ep][rr, cc]) > -9) for ep in ("T0", "T2")})
br = gpd.GeoDataFrame(geometry=lines, crs=crs)
for k, v in {"class": "pontoon_bridge", "sub_class": "temporary floating bridge", "epoch": "T1", "date": "2025-02-16",
             "sensor": "S1A", "confidence": "medium",
             "method": "rule: VV_T1 > -6 dB inside T0/T1 channel; L/W >= 4, >= 80 m, >= 40 % over T1 water -> centre line"}.items():
    br[k] = v
br["present_T0"] = [p["T0"] for p in present]
br["present_T2"] = [p["T2"] for p in present]
br.loc[br.present_T0 & br.present_T2, "sub_class"] = "bridge present at all three dates (likely permanent or long-standing)"
layers["pontoon_bridges"] = br

sand = (~water["T2"]) & (ndvi["T2"] < 0.15) & (mndwi["T2"] < 0) & (vv["T2"] < -14) & floodplain
layers["sand_bars"] = polygons(clean(sand, 1, 2, 2.0), {"class": "sand_bar", "sub_class": "exposed floodplain sand",
                                                       "epoch": "T2", "date": "2025-04-17", "sensor": "S1A + S2",
                                                       "confidence": "medium",
                                                       "method": "rule: NDVI < 0.15, MNDWI < 0, VV < -14 dB, floodplain"})
veg = ndvi["T1"] > 0.45
layers["veg_fields"] = polygons(clean(veg, 1, 1, 1.0), {"class": "veg_field", "sub_class": "crops / trees", "epoch": "T1",
                                                       "date": "2025-02-16", "sensor": "S2", "confidence": "high",
                                                       "method": "rule: NDVI > 0.45"})

if OUT.exists():
    OUT.unlink()
for name, gdf in layers.items():
    gdf = gdf[~gdf.is_empty].reset_index(drop=True)
    gdf.to_file(OUT, layer=name, driver="GPKG")
    extra = f", total {gdf.area.sum() / 1e6:.2f} km2" if gdf.geom_type.iloc[0].endswith("Polygon") else f", total {gdf.length.sum() / 1000:.1f} km"
    print(f"{name:16s} {len(gdf):5d} features{extra}")
