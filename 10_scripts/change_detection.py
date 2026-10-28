"""Phase 13a: SAR log-ratio change detection and the tent-city area over time.

Log-ratio in dB (speckle is multiplicative, so the ratio - a difference in dB - is the right operator):
  LR_build = VV_T1 - VV_T0  (2025-02-16 vs 2024-11-12),   LR_clear = VV_T2 - VV_T1  (2025-04-17 vs 2025-02-16)
Thresholds: Otsu (between-class variance maximum) on LR inside the floodplain envelope, compared with a fixed +-3 dB.
Tent-city area for every SAR date d (2024-11-12, 2025-01-23, 2025-02-04, 2025-02-16, 2025-04-17):
  mask_d = VV_d - VV_T0 >= threshold  AND not water at d  AND NDVI_T0 < 0.3  AND inside the floodplain; cleaned
  (opening, 0.5 ha minimum). Lee 7x7 sigma0 dB, same orbit, same grid.
Outputs: 07_analysis/change/*.tif, 09_docs/change_area_timeseries.csv, change_maps.png, change_area_timeseries.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu

ROOT = Path(r"D:\SAREO-Kumbh")
S1 = ROOT / "02_preproc" / "S1"
OUT = ROOT / "07_analysis" / "change"
OUT.mkdir(parents=True, exist_ok=True)
DATES = ["20241112", "20250123", "20250204", "20250216", "20250417"]


def vv(d):
    with rasterio.open(S1 / f"S1A_{d}_Sig0_lee7_dB.tif") as s:
        return s.read(2).astype("float64"), s.profile


VV = {d: vv(d)[0] for d in DATES}
prof = vv(DATES[0])[1]
with rasterio.open(ROOT / "05_fused" / "fused_stack_T0_20241113.tif") as s:
    ndvi_t0 = s.read(10)
water_any = np.zeros_like(ndvi_t0, bool)
for ep, d in (("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")):
    with rasterio.open(ROOT / "05_fused" / f"fused_stack_{ep}_{d}.tif") as s:
        water_any |= (np.nan_to_num(s.read(11), nan=-1) > 0)
floodplain = ndi.binary_dilation(water_any, iterations=150)  # 1.5 km envelope around all river channels
valid = np.isfinite(VV[DATES[0]]) & np.isfinite(VV["20250216"]) & np.isfinite(VV["20250417"])

lr_build = VV["20250216"] - VV["20241112"]
lr_clear = VV["20250417"] - VV["20250216"]
sel = valid & floodplain
t_build = threshold_otsu(lr_build[sel])
t_clear = threshold_otsu(lr_clear[sel])
print(f"Otsu threshold LR_build (T1-T0): {t_build:+.2f} dB   LR_clear (T2-T1): {t_clear:+.2f} dB   (fixed rule: +3 / -2 dB)")


def write(name, arr, dtype="float32", nodata=np.nan):
    p = prof.copy(); p.update(count=1, dtype=dtype, nodata=nodata, compress="deflate")
    if dtype == "float32":
        p["predictor"] = 3
    with rasterio.open(OUT / name, "w", **p) as d:
        d.write(arr.astype(dtype), 1)


def clean(m):
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    return np.isin(lab, np.nonzero(sizes >= 50)[0] + 1)  # >= 0.5 ha


write("LR_VV_T1-T0_dB.tif", np.where(valid, lr_build, np.nan))
write("LR_VV_T2-T1_dB.tif", np.where(valid, lr_clear, np.nan))
appear = clean(valid & (lr_build >= 3))
vanish = clean(valid & (lr_clear <= -2))
temporary = appear & vanish  # appeared for the Mela and gone afterwards
change_class = np.zeros(appear.shape, "uint8")
change_class[appear & ~vanish] = 1   # appeared and stayed (new permanent change or still standing at T2)
change_class[vanish & ~appear] = 2   # disappeared only
change_class[temporary] = 3          # appeared then disappeared = temporary structures
write("change_class_T0-T1-T2.tif", change_class, "uint8", 0)

# ---- tent-city area per SAR date (relative to the T0 baseline) ----
rows = []
for d in DATES:
    for thr, lab in ((3.0, "fixed +3 dB"), (t_build, f"Otsu {t_build:+.1f} dB")):
        m = clean(valid & floodplain & (VV[d] - VV["20241112"] >= thr) & (ndvi_t0 < 0.3) & ~water_any)
        rows.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "threshold": lab, "tent_city_km2": round(m.sum() * 100 / 1e6, 2)})
ts = pd.DataFrame(rows)
ts.to_csv(ROOT / "09_docs" / "change_area_timeseries.csv", index=False)
print(ts.pivot(index="date", columns="threshold", values="tent_city_km2").to_string())
area = {k: round(v.sum() * 100 / 1e6, 2) for k, v in (("appeared (T1-T0 >= +3)", appear), ("vanished (T2-T1 <= -2)", vanish),
                                                      ("temporary (both)", temporary))}
print("change classes km2:", area)
pd.DataFrame([{"class": k, "km2": v} for k, v in area.items()] +
             [{"class": "otsu_build_dB", "km2": round(t_build, 2)}, {"class": "otsu_clear_dB", "km2": round(t_clear, 2)}]
             ).to_csv(ROOT / "09_docs" / "change_class_areas.csv", index=False)

# ---- figures ----
fig, ax = plt.subplots(1, 3, figsize=(18, 6.4))
for a, img, title in ((ax[0], lr_build, "Log-ratio VV T1 - T0 (dB): red = new scatterers"),
                      (ax[1], lr_clear, "Log-ratio VV T2 - T1 (dB): blue = removed")):
    im = a.imshow(np.where(valid, img, np.nan), cmap="RdBu_r", vmin=-10, vmax=10); a.set_title(title); a.axis("off")
    plt.colorbar(im, ax=a, fraction=0.046, pad=0.02)
cmap = matplotlib.colors.ListedColormap(["#f2f2f2", "#ff9800", "#1e88e5", "#d50000"])
ax[2].imshow(change_class, cmap=cmap, vmin=0, vmax=3, interpolation="nearest"); ax[2].axis("off")
ax[2].set_title("Change classes (0.5 ha minimum)")
ax[2].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.colors[1:]],
             labels=["appeared, still present T2", "disappeared only", "temporary: appeared then gone"], loc="lower left", fontsize=8)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "change_maps.png", dpi=60); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.8))
for lab, g in ts.groupby("threshold"):
    ax.plot(pd.to_datetime(g["date"]), g["tent_city_km2"], "-o", label=lab)
for day, txt in (("2025-01-13", "Mela opens"), ("2025-02-26", "Mela closes")):
    ax.axvline(pd.Timestamp(day), color="grey", ls="--", lw=1); ax.text(pd.Timestamp(day), ax.get_ylim()[1] * 0.95, " " + txt, fontsize=8)
ax.set_ylabel("tent-city area (km²)"); ax.set_title("Tent-city area from Sentinel-1 (change vs 2024-11-12 baseline)")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "change_area_timeseries.png", dpi=80)
