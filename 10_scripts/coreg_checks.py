"""Phase 8 (brief item 6): geometric accuracy and co-registration checks on the common 10 m AOI grid.

A. Absolute accuracy vs an independent reference (OpenStreetMap road/rail bridges over water):
   for each image, find the sub-pixel shift (dx, dy) that maximises the mean value sampled on the bridge pixels
   (bridges are bright over dark water in SAR VV and in Sentinel-2 B08). Search +-3 px in 0.25 px steps.
B. Relative S1 date-to-date: phase correlation (upsample 20) of Lee 7x7 VV dB vs T1, whole AOI and static city only.
C. Relative S1 to S2 (cross-sensor): phase correlation of same-day water masks (S1 VV < -18 dB vs S2 MNDWI > 0).
Shifts are reported in metres: +E = image is east of the reference, +N = image is north of the reference.
Output: 09_docs/coreg_checks.csv
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from scipy.ndimage import map_coordinates
from skimage.registration import phase_cross_correlation

ROOT = Path(r"D:\SAREO-Kumbh")
S1 = ROOT / "02_preproc" / "S1"
S2 = ROOT / "02_preproc" / "S2"
S2E = ROOT / "03_enhanced" / "S2"
S1_DATES = [("T0", "20241112"), ("T1a", "20250123"), ("T1b", "20250204"), ("T1", "20250216"), ("T2", "20250417")]
S2_DATES = [("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")]
PX = 10.0
rows = []

ref_ds = rasterio.open(S1 / "S1A_20250216_Sig0_lee7_dB.tif")
transform, shape = ref_ds.transform, ref_ds.shape

# ---------- A. absolute, against OSM bridges over water ----------
osm = ROOT / "06_vectors" / "osm.gpkg"
br = gpd.read_file(osm, layer="bridges")
br = br[br["highway"].notna() | br["bridge"].isin(["yes", "viaduct"])]
water = gpd.read_file(osm, layer="water_areas")
over_water = gpd.overlay(gpd.GeoDataFrame(geometry=br.buffer(5)), gpd.GeoDataFrame(geometry=water.geometry), how="intersection")
bmask = geometry_mask(over_water.geometry, out_shape=shape, transform=transform, invert=True)
rr, cc = np.nonzero(bmask)
print(f"bridge-over-water pixels: {bmask.sum()}")


def best_shift(img):
    img = np.nan_to_num(img, nan=np.nanmedian(img))
    steps = np.arange(-3, 3.01, 0.25)
    score = np.array([[map_coordinates(img, [rr + dy, cc + dx], order=1).mean() for dx in steps] for dy in steps])
    iy, ix = np.unravel_index(score.argmax(), score.shape)
    peak_gain = score.max() - score[len(steps) // 2, len(steps) // 2]
    return steps[ix], steps[iy], peak_gain


for ep, d in S1_DATES:
    with rasterio.open(S1 / f"S1A_{d}_Sig0_lee7_dB.tif") as s:
        dx, dy, gain = best_shift(s.read(2))
    rows.append({"check": "A absolute vs OSM bridges", "image": f"S1 VV {ep} {d}", "reference": "OSM bridges",
                 "shift_E_m": dx * PX, "shift_N_m": -dy * PX, "shift_px": np.hypot(dx, dy), "note": f"gain at peak {gain:.2f} dB"})
for ep, d in S2_DATES:
    with rasterio.open(S2 / f"S2_{d}_L2A_refl10m.tif") as s:
        dx, dy, gain = best_shift(s.read(7))  # B08
    rows.append({"check": "A absolute vs OSM bridges", "image": f"S2 B08 {ep} {d}", "reference": "OSM bridges",
                 "shift_E_m": dx * PX, "shift_N_m": -dy * PX, "shift_px": np.hypot(dx, dy), "note": f"gain at peak {gain:.4f} refl"})

# ---------- B. S1 date-to-date ----------
def load_db(d):
    with rasterio.open(S1 / f"S1A_{d}_Sig0_lee7_dB.tif") as s:
        a = s.read(2)
    return np.nan_to_num(a, nan=np.nanmedian(a))


ref = load_db("20250216")
city = (slice(0, shape[0]), slice(0, 450))  # western strip = Prayagraj city, structures do not change
for ep, d in S1_DATES:
    if d == "20250216":
        continue
    mov = load_db(d)
    for region, sl in (("whole AOI", (slice(None), slice(None))), ("static city strip", city)):
        shift, err, _ = phase_cross_correlation(ref[sl], mov[sl], upsample_factor=20)
        dy, dx = -shift  # phase_cross_correlation returns the shift that registers mov onto ref
        rows.append({"check": f"B S1 date-to-date ({region})", "image": f"S1 VV {ep} {d}", "reference": "S1 VV T1 20250216",
                     "shift_E_m": dx * PX, "shift_N_m": -dy * PX, "shift_px": np.hypot(dx, dy), "note": f"phase-corr error {err:.3f}"})

# ---------- C. S1 to S2, same-day water masks ----------
for ep, d in (("T1", "20250216"), ("T2", "20250417")):
    with rasterio.open(S1 / f"S1A_{d}_Sig0_lee7_dB.tif") as s:
        w1 = (np.nan_to_num(s.read(2), nan=0) < -18).astype(float)
    with rasterio.open(S2E / f"S2_{d}_MNDWI.tif") as s:
        w2 = (np.nan_to_num(s.read(1), nan=-1) > 0).astype(float)
    shift, err, _ = phase_cross_correlation(w2, w1, upsample_factor=10)
    dy, dx = -shift
    iou = (w1.astype(bool) & w2.astype(bool)).sum() / (w1.astype(bool) | w2.astype(bool)).sum()
    rows.append({"check": "C S1 to S2 (same-day water masks)", "image": f"S1 water {ep} {d}", "reference": f"S2 water {ep} {d}",
                 "shift_E_m": dx * PX, "shift_N_m": -dy * PX, "shift_px": np.hypot(dx, dy),
                 "note": f"IoU at zero shift {iou:.3f}; water S1 {100 * w1.mean():.1f}% S2 {100 * w2.mean():.1f}%"})

df = pd.DataFrame(rows)
df[["shift_E_m", "shift_N_m", "shift_px"]] = df[["shift_E_m", "shift_N_m", "shift_px"]].round(2)
df.to_csv(ROOT / "09_docs" / "coreg_checks.csv", index=False)
print(df.to_string(index=False))
