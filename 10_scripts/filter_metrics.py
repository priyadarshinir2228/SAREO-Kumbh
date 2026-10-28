"""Phase 6 metrics for every T1_<tag>_lin.tif in 03_enhanced/S1_filters (brief 2.3 and item 10).

Sample areas are chosen objectively from a 3-date T1 average (Phase 5 rasters), not from any filter output:
  homogeneous  : 21x21 px blocks with the lowest coefficient of variation (25 land + 10 water blocks)
  edges        : top 5% Sobel gradient of the smoothed 3-date log average
  point targets: 3x3 local maxima brighter than 0 dB VV in the 3-date average (bridges, metal, buildings)
Metrics (per band, linear sigma0, 'none' = unfiltered reference after the same terrain correction):
  ENL = mu^2/sigma^2 (median over land blocks; also water)   MR = mu_f/mu_o   SSI = (s_f/m_f)/(s_o/m_o)
  SMPI = (1+|mu_o-mu_f|) * s_f/s_o   EPI = sum|grad F| / sum|grad O| on edge pixels (amplitude)
  PTP = median(F/O) on point targets (1 = point targets kept)
Outputs: 09_docs/filter_metrics.csv, 09_docs/filter_comparison.md, 06_vectors/filter_samples.gpkg
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import maximum_filter, sobel, uniform_filter
from shapely.geometry import box

ROOT = Path(r"D:\SAREO-Kumbh")
FDIR = ROOT / "03_enhanced" / "S1_filters"
BLOCK = 21
FAMILY = {
    "none": "Unfiltered", "boxcar": "Boxcar (mean)", "median": "Median", "lee": "Lee", "frost": "Frost",
    "gammamap": "Gamma-MAP", "refinedlee": "Refined Lee (7x7 edge-aligned)", "leesigma": "Lee Sigma",
    "idan": "IDAN (adaptive neighbourhood 50)", "mulog": "MuLoG", "kuan": "Kuan (OTB)",
    "mtquegan": "Multi-temporal Quegan (3 dates, 5x5)", "sar2sar": "SAR2SAR (deep learning)",
}

# ---------- reference and sample areas ----------
ref_srcs = [rasterio.open(ROOT / "02_preproc" / "S1" / f"S1A_{d}_Sig0_nofilter_lin.tif") for d in ("20250123", "20250204", "20250216")]
transform, crs = ref_srcs[0].transform, ref_srcs[0].crs
ref = {b: np.nanmean([s.read(b) for s in ref_srcs], axis=0) for b in (1, 2)}  # 1=VH 2=VV
vv_ref = ref[2]
H, W = vv_ref.shape

blocks = []
for r in range(0, H - BLOCK, BLOCK):
    for c in range(0, W - BLOCK, BLOCK):
        a = vv_ref[r:r + BLOCK, c:c + BLOCK]
        if np.isnan(a).any() or (a <= 0).any():
            continue
        blocks.append((r, c, a.std() / a.mean(), 10 * np.log10(a.mean())))
blocks = pd.DataFrame(blocks, columns=["r", "c", "cv", "db"])
land = blocks[blocks.db > -18].nsmallest(25, "cv").assign(kind="homogeneous_land")
water = blocks[blocks.db <= -18].nsmallest(10, "cv").assign(kind="homogeneous_water")
samples = pd.concat([land, water])

log_ref = uniform_filter(10 * np.log10(np.clip(np.nan_to_num(vv_ref, nan=1e-4), 1e-4, None)), 3)
grad = np.hypot(sobel(log_ref, 0), sobel(log_ref, 1))
valid = np.isfinite(vv_ref) & (vv_ref > 0)
edge_mask = valid & (grad >= np.percentile(grad[valid], 95))
edge_mask[:2, :] = edge_mask[-2:, :] = edge_mask[:, :2] = edge_mask[:, -2:] = False
pt_mask = valid & (vv_ref > 1.0) & (vv_ref == maximum_filter(np.nan_to_num(vv_ref), 3))

px = transform.a  # 10 m
polys = [box(transform.c + c * px, transform.f - (r + BLOCK) * px, transform.c + (c + BLOCK) * px, transform.f - r * px)
         for r, c in zip(samples.r, samples.c)]
gpd.GeoDataFrame(samples[["kind", "cv", "db"]].reset_index(drop=True), geometry=polys, crs=crs).to_file(
    ROOT / "06_vectors" / "filter_samples.gpkg", layer="homogeneous_blocks", driver="GPKG")
print(f"samples: {len(land)} land blocks, {len(water)} water blocks, {edge_mask.sum()} edge px, {pt_mask.sum()} point targets")


def grad_sum(img, mask):
    a = np.sqrt(np.clip(np.nan_to_num(img), 0, None))  # amplitude
    gx = np.abs(np.diff(a, axis=1, append=a[:, -1:]))
    gy = np.abs(np.diff(a, axis=0, append=a[-1:, :]))
    return (gx + gy)[mask].sum()


def block_stats(img, df):
    out = []
    for r, c in zip(df.r, df.c):
        a = img[r:r + BLOCK, c:c + BLOCK]
        out.append((np.nanmean(a), np.nanstd(a)))
    return np.array(out)


# ---------- metrics ----------
orig = rasterio.open(FDIR / "T1_none_lin.tif")
O = {b: orig.read(b).astype("float64") for b in (1, 2)}
timing = {}
for f in ("snap_filter_timing_run1_enl1.csv", "snap_filter_timing.csv"):  # later run overrides re-run filters
    if (FDIR / f).exists():
        t = pd.read_csv(FDIR / f)
        timing.update(dict(zip(t.tag, t.seconds)))
if (FDIR / "extra_filter_timing.csv").exists():
    for line in (FDIR / "extra_filter_timing.csv").read_text().split():
        tag, sec = line.split(",")
        timing[tag] = int(sec)

rows = []
for tif in sorted(FDIR.glob("T1_*_lin.tif")):
    tag = tif.name[3:-8]
    key = max((k for k in FAMILY if tag.startswith(k)), key=len, default=tag)  # longest prefix: leesigma before lee
    fam = FAMILY.get(key, tag)
    size = tag[len(key):] if tag[len(key):].isdigit() else ""
    with rasterio.open(tif) as src:
        assert src.transform == orig.transform and src.shape == orig.shape, f"{tag} not on the common grid"
        F = {b: src.read(b).astype("float64") for b in (1, 2)}
    row = {"tag": tag, "method": fam, "window": f"{size}x{size}" if size else "-", "runtime_s": timing.get(tag, np.nan)}
    for b, bn in ((2, "VV"), (1, "VH")):
        so, sf = block_stats(O[b], land), block_stats(F[b], land)
        wf = block_stats(F[b], water)
        row[f"{bn}_ENL"] = np.median(sf[:, 0] ** 2 / sf[:, 1] ** 2)
        row[f"{bn}_ENL_water"] = np.median(wf[:, 0] ** 2 / wf[:, 1] ** 2)
        row[f"{bn}_MR"] = np.median(sf[:, 0] / so[:, 0])
        row[f"{bn}_SSI"] = np.median((sf[:, 1] / sf[:, 0]) / (so[:, 1] / so[:, 0]))
        row[f"{bn}_SMPI"] = np.median((1 + np.abs(so[:, 0] - sf[:, 0])) * sf[:, 1] / so[:, 1])
        row[f"{bn}_EPI"] = grad_sum(F[b], edge_mask) / grad_sum(O[b], edge_mask)
        m = pt_mask & np.isfinite(F[b]) & (O[b] > 0)
        row[f"{bn}_PTP"] = np.median(F[b][m] / O[b][m])
    rows.append(row)

df = pd.DataFrame(rows)
filt = df[df.tag != "none"].copy()
# rank-based overall score on VV (lower = better): smoothing, edges, point targets, radiometric bias
filt["rank_ENL"] = filt.VV_ENL.rank(ascending=False)
filt["rank_EPI"] = filt.VV_EPI.rank(ascending=False)
filt["rank_PTP"] = (filt.VV_PTP - 1).abs().rank()
filt["rank_MR"] = (filt.VV_MR - 1).abs().rank()
filt["score"] = filt[["rank_ENL", "rank_EPI", "rank_PTP", "rank_MR"]].sum(axis=1)
df = df.merge(filt[["tag", "score"]], on="tag", how="left").sort_values(["score", "tag"], na_position="first")
df.round(3).to_csv(ROOT / "09_docs" / "filter_metrics.csv", index=False)

cols = ["method", "window", "VV_ENL", "VV_ENL_water", "VV_SSI", "VV_MR", "VV_SMPI", "VV_EPI", "VV_PTP", "VH_ENL", "VH_EPI", "runtime_s", "score"]
md = ["| Rank | " + " | ".join(cols) + " |", "|" + " --- |" * (len(cols) + 1)]
for i, (_, r) in enumerate(df.iterrows()):
    vals = []
    for c in cols:
        v = r[c]
        vals.append(f"{v:.2f}" if isinstance(v, float) and np.isfinite(v) else ("-" if isinstance(v, float) else str(v)))
    md.append(f"| {'-' if r.tag == 'none' else i} | " + " | ".join(vals) + " |")
(ROOT / "09_docs" / "filter_comparison.md").write_text(
    "# Speckle filter comparison - T1 2025-02-16 (generated by 10_scripts/filter_metrics.py)\n\n"
    f"Samples: {len(land)} homogeneous land blocks + {len(water)} water blocks (21x21 px), {int(edge_mask.sum())} edge pixels, "
    f"{int(pt_mask.sum())} point targets. Score = sum of VV ranks for ENL, EPI, |PTP-1| and |MR-1| (lower is better).\n\n"
    + "\n".join(md) + "\n")
print(df[["tag", "VV_ENL", "VV_SSI", "VV_MR", "VV_EPI", "VV_PTP", "VH_ENL", "runtime_s", "score"]].round(3).to_string(index=False))
