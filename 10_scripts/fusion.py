"""Phase 9 (brief item 11): SAR-EO fusion without loss of resolution or attributes, plus quality checks.

All inputs already share one 10 m EPSG:32644 grid (Phase 8), so nothing is resampled.
  1. Lossless stacks (T0, T1, T2): VV_dB VH_dB VVminusVH_dB (Lee 7x7) + B02 B03 B04 B08 B11 B12 + NDVI MNDWI
     Float32, DEFLATE (lossless), every band named and tagged with its source file.
  2. Pixel-level fusion on T1 (2025-02-16, same-day S1 + S2):
       PCA    : PCA on standardised B02 B03 B04 B08 B11 B12; PC1 <- SAR VV dB matched to PC1 mean/std; inverse PCA
       IHS    : fast additive IHS on natural colour; F_k = B_k + (S' - I), I = mean(B04,B03,B02), S' = VV matched to I
       Brovey : F_k = B_k * S'' / I with S'' = linear sigma0 VV matched to I mean/std (ratio method)
  3. Multi-temporal SAR RGB: R = VV T1, G = VV T0, B = VV T2 (lossless VRT + 8-bit display copy, -25..0 dB)
Quality: exact-equality test of every stack band against its source; per-band correlation, ERGAS, SAM and spatial
correlation coefficient (sCC, high-pass vs SAR) for each fusion. Outputs in 05_fused and 09_docs/fusion_quality.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from osgeo import gdal
from scipy.ndimage import laplace

gdal.UseExceptions()
ROOT = Path(r"D:\SAREO-Kumbh")
S1, S2, S2E, OUT = ROOT / "02_preproc" / "S1", ROOT / "02_preproc" / "S2", ROOT / "03_enhanced" / "S2", ROOT / "05_fused"
OUT.mkdir(exist_ok=True)
PAIRS = [("T0", "20241112", "20241113"), ("T1", "20250216", "20250216"), ("T2", "20250417", "20250417")]
S2_ORDER = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
OPT = ["B02", "B03", "B04", "B08", "B11", "B12"]


def read(path, band=1):
    with rasterio.open(path) as s:
        return s.read(band).astype("float32"), s.profile


def write(path, arrays, names, profile, tags=None):
    p = profile.copy()
    p.update(driver="GTiff", count=len(arrays), dtype="float32", nodata=np.nan, compress="deflate", predictor=3,
             tiled=True, blockxsize=256, blockysize=256)
    p.pop("photometric", None)
    with rasterio.open(path, "w", **p) as d:
        for i, (a, n) in enumerate(zip(arrays, names), 1):
            d.write(a.astype("float32"), i)
            d.set_band_description(i, n)
        if tags:
            d.update_tags(**tags)


def match(src, ref):
    """Linear match of src to ref mean and standard deviation (valid pixels only)."""
    m = np.isfinite(src) & np.isfinite(ref)
    return (src - np.nanmean(src[m])) / np.nanstd(src[m]) * np.nanstd(ref[m]) + np.nanmean(ref[m])


# ---------- 1. lossless stacks ----------
sources = {}
for ep, d1, d2 in PAIRS:
    s1_path = S1 / f"S1A_{d1}_Sig0_lee7_dB.tif"
    s2_path = S2 / f"S2_{d2}_L2A_refl10m.tif"
    vh, prof = read(s1_path, 1)
    vv, _ = read(s1_path, 2)
    opt = {b: read(s2_path, S2_ORDER.index(b) + 1)[0] for b in OPT}
    ndvi, _ = read(S2E / f"S2_{d2}_NDVI.tif")
    mndwi, _ = read(S2E / f"S2_{d2}_MNDWI.tif")
    names = ["VV_dB", "VH_dB", "VVminusVH_dB"] + OPT + ["NDVI", "MNDWI"]
    arrays = [vv, vh, vv - vh] + [opt[b] for b in OPT] + [ndvi, mndwi]
    out = OUT / f"fused_stack_{ep}_{d2}.tif"
    write(out, arrays, names, prof, tags={"S1_SOURCE": s1_path.name, "S2_SOURCE": s2_path.name,
                                         "NOTE": "lossless layer stack, common 10 m grid, no resampling"})
    sources[ep] = (out, dict(zip(names, arrays)))
    print("stack", ep, out.name, len(names), "bands")

# ---------- 2. pixel-level fusion on T1 ----------
_, t1 = sources["T1"]
prof = read(S1 / "S1A_20250216_Sig0_lee7_dB.tif")[1]
valid = np.all([np.isfinite(t1[b]) for b in OPT + ["VV_dB"]], axis=0)
vv_db, vv_lin = t1["VV_dB"], 10 ** (t1["VV_dB"] / 10)

# PCA
X = np.stack([t1[b][valid] for b in OPT], 1).astype("float64")
mu, sd = X.mean(0), X.std(0)
Z = (X - mu) / sd
eigval, eigvec = np.linalg.eigh(np.cov(Z, rowvar=False))
order = eigval.argsort()[::-1]
eigval, eigvec = eigval[order], eigvec[:, order]
pcs = Z @ eigvec
if np.corrcoef(pcs[:, 0], vv_db[valid])[0, 1] < 0:  # PC sign is arbitrary; align PC1 with SAR so detail is added, not inverted
    eigvec[:, 0] *= -1; pcs[:, 0] *= -1
pc1 = pcs[:, 0]
pcs[:, 0] = (vv_db[valid] - vv_db[valid].mean()) / vv_db[valid].std() * pc1.std() + pc1.mean()
Xf = (pcs @ eigvec.T) * sd + mu
pca = {b: np.full(valid.shape, np.nan, "float32") for b in OPT}
for k, b in enumerate(OPT):
    pca[b][valid] = Xf[:, k]
write(OUT / "fusion_PCA_T1_20250216.tif", [pca[b] for b in OPT], [f"{b}_PCAfused" for b in OPT], prof,
      tags={"METHOD": "PCA substitution of PC1 by SAR VV dB", "PC_VARIANCE_PCT": ",".join(f"{100 * v / eigval.sum():.1f}" for v in eigval)})

# IHS (fast additive) and Brovey on natural colour
R, G, B = t1["B04"], t1["B03"], t1["B02"]
I = (R + G + B) / 3
s_ihs = match(vv_db, I)
s_brv = match(vv_lin, I)
ihs = {b: t1[b] + (s_ihs - I) for b in ("B04", "B03", "B02")}
brv = {b: t1[b] * s_brv / np.where(I > 0, I, np.nan) for b in ("B04", "B03", "B02")}
write(OUT / "fusion_IHS_T1_20250216.tif", [ihs[b] for b in ("B04", "B03", "B02")], ["B04_IHS", "B03_IHS", "B02_IHS"], prof,
      tags={"METHOD": "fast additive IHS, intensity replaced by SAR VV dB matched to I"})
write(OUT / "fusion_Brovey_T1_20250216.tif", [brv[b] for b in ("B04", "B03", "B02")], ["B04_Brovey", "B03_Brovey", "B02_Brovey"], prof,
      tags={"METHOD": "Brovey ratio with linear SAR VV matched to I"})

# High-pass filter (HPF) injection: add only SAR fine detail, scaled per band, keeping the optical spectrum
from scipy.ndimage import uniform_filter
s_filled = np.nan_to_num(vv_db, nan=np.nanmedian(vv_db))
hp = s_filled - uniform_filter(s_filled, 5)
HPF_WEIGHT = 0.5
hpf = {b: t1[b] + HPF_WEIGHT * np.nanstd(t1[b]) / np.std(hp[valid]) * hp for b in OPT}
write(OUT / "fusion_HPF_T1_20250216.tif", [hpf[b] for b in OPT], [f"{b}_HPF" for b in OPT], prof,
      tags={"METHOD": f"high-pass (5x5) SAR VV dB detail injected with weight {HPF_WEIGHT} x std(band)/std(HP)"})

# ---------- 3. multi-temporal SAR RGB ----------
mt_src = [str(S1 / f"S1A_{d}_Sig0_lee7_dB.tif") for d in ("20250216", "20241112", "20250417")]
vrt = gdal.BuildVRT(str(OUT / "mtRGB_VV_R-T1_G-T0_B-T2.vrt"), mt_src, separate=True, bandList=[2])
vrt = None
mt = np.stack([read(p, 2)[0] for p in mt_src])
byte = np.where(np.isfinite(mt), np.clip((mt + 25) / 25, 0, 1) * 254 + 1, 0).astype("uint8")
p8 = prof.copy(); p8.update(count=3, dtype="uint8", nodata=0, compress="deflate", photometric="RGB")
with rasterio.open(OUT / "mtRGB_VV_R-T1_G-T0_B-T2_display.tif", "w", **p8) as d:
    d.write(byte)

# ---------- 4. quality checks ----------
rows = []
# 4a lossless: every stack band equals its source exactly
for ep, (path, arrs) in sources.items():
    with rasterio.open(path) as s:
        same_grid = s.transform == prof["transform"] and (s.height, s.width) == (prof["height"], prof["width"])
        back = {s.descriptions[i]: s.read(i + 1) for i in range(s.count)}
    exact = all(np.array_equal(back[n], arrs[n].astype("float32"), equal_nan=True) for n in arrs)
    rows.append({"product": path.name, "check": "lossless round-trip", "result": f"all {len(arrs)} bands bit-identical: {exact}; same grid: {same_grid}; dtype float32; DEFLATE"})


def quality(name, fused, bands):
    m = valid & np.all([np.isfinite(fused[b]) for b in bands], axis=0)
    ref = np.stack([t1[b][m] for b in bands], 1).astype("float64")
    fus = np.stack([fused[b][m] for b in bands], 1).astype("float64")
    cc = [np.corrcoef(ref[:, k], fus[:, k])[0, 1] for k in range(len(bands))]
    rmse = np.sqrt(((fus - ref) ** 2).mean(0))
    ergas = 100 * np.sqrt(np.mean((rmse / ref.mean(0)) ** 2))
    cosang = (ref * fus).sum(1) / (np.linalg.norm(ref, axis=1) * np.linalg.norm(fus, axis=1))
    sam = np.degrees(np.arccos(np.clip(cosang, -1, 1))).mean()
    hp_sar = laplace(np.nan_to_num(vv_db))[m]
    scc = np.mean([np.corrcoef(laplace(np.nan_to_num(fused[b]))[m], hp_sar)[0, 1] for b in bands])
    scc0 = np.mean([np.corrcoef(laplace(np.nan_to_num(t1[b]))[m], hp_sar)[0, 1] for b in bands])
    rows.append({"product": name, "check": "spectral + spatial quality vs original S2",
                 "result": f"CC per band {', '.join(f'{b} {c:.3f}' for b, c in zip(bands, cc))}; mean CC {np.mean(cc):.3f}; "
                           f"ERGAS {ergas:.2f}; SAM {sam:.2f} deg; sCC with SAR {scc:.3f} (original S2 {scc0:.3f})",
                 "mean_CC": round(float(np.mean(cc)), 3), "ERGAS": round(float(ergas), 2), "SAM_deg": round(float(sam), 2),
                 "sCC_SAR": round(float(scc), 3), "sCC_SAR_original": round(float(scc0), 3)})


quality("fusion_PCA_T1_20250216.tif", pca, OPT)
quality("fusion_IHS_T1_20250216.tif", ihs, ["B04", "B03", "B02"])
quality("fusion_Brovey_T1_20250216.tif", brv, ["B04", "B03", "B02"])
quality("fusion_HPF_T1_20250216.tif", hpf, OPT)
rows.append({"product": "PCA eigen-analysis", "check": "variance explained by PC1..PC6 (%)",
             "result": ", ".join(f"{100 * v / eigval.sum():.1f}" for v in eigval)})
df = pd.DataFrame(rows)
df.to_csv(ROOT / "09_docs" / "fusion_quality.csv", index=False)
for r in rows:
    print(f"- {r['product']}: {r['result']}")
