"""Phase 12 (brief item 12): signature reference values per class and epoch from the lossless SAR + EO stacks.

Sample areas: all 200 polygons in 06_vectors/training_samples.gpkg (water, tent_block, sand, vegetation, built_up)
plus the 5 pontoon-bridge lines buffered by 5 m. Polygons are fixed in space, so the T0 and T2 values of the
'tent_block' class show what the same ground looked like before and after the Mela (the change signature).
Features: VV_dB, VH_dB, VVminusVH_dB (cross-pol ratio), NDVI, MNDWI, NDBI (= (B11 - B08) / (B11 + B08)) and the
S2 reflectance bands for spectral profiles.
Separability: Jeffries-Matusita (JM, 0..2; > 1.9 = well separable) between class pairs at T1 for single features and
for three feature sets: SAR only (VV, VH, ratio), EO only (6 S2 bands), fused (both).
Outputs: 09_docs/signatures_stats.csv, signatures_separability.csv, signatures_boxplots.png, signatures_spectral.png,
         signatures_trajectory.png
"""
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

ROOT = Path(r"D:\SAREO-Kumbh")
F = ROOT / "05_fused"
EPOCHS = [("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")]
CLASSES = ["water", "pontoon_bridge", "tent_block", "sand", "vegetation", "built_up"]
COLOURS = {"water": "#1565c0", "pontoon_bridge": "#c9a400", "tent_block": "#d50000", "sand": "#ef8f00",
           "vegetation": "#2e7d32", "built_up": "#616161"}
FEATS = ["VV_dB", "VH_dB", "VVminusVH_dB", "NDVI", "MNDWI", "NDBI"]
BANDS = ["B02", "B03", "B04", "B08", "B11", "B12"]

samples = pd.concat([gpd.read_file(ROOT / "06_vectors" / "training_samples.gpkg", layer=l) for l in ("training", "validation")])
bridges = gpd.read_file(ROOT / "06_vectors" / "kumbh_features.gpkg", layer="pontoon_bridges")
geoms = {c: samples[samples["class"] == c].geometry for c in CLASSES if c != "pontoon_bridge"}
geoms["pontoon_bridge"] = bridges.buffer(5)

data = {}  # (epoch, class) -> DataFrame of pixels
for ep, d in EPOCHS:
    with rasterio.open(F / f"fused_stack_{ep}_{d}.tif") as s:
        st = {s.descriptions[i]: s.read(i + 1).astype("float64") for i in range(s.count)}
        tf, shape = s.transform, s.shape
    st["NDBI"] = (st["B11"] - st["B08"]) / (st["B11"] + st["B08"])
    for c in CLASSES:
        m = geometry_mask(geoms[c], out_shape=shape, transform=tf, invert=True)
        df = pd.DataFrame({k: st[k][m] for k in FEATS + BANDS}).dropna()
        data[(ep, c)] = df

rows = []
for (ep, c), df in data.items():
    for f in FEATS + BANDS:
        v = df[f]
        rows.append({"epoch": ep, "class": c, "feature": f, "n_px": len(v), "mean": v.mean(), "std": v.std(),
                     "p25": v.quantile(0.25), "median": v.median(), "p75": v.quantile(0.75)})
stats = pd.DataFrame(rows).round(4)
stats.to_csv(ROOT / "09_docs" / "signatures_stats.csv", index=False)


def jm(a, b):
    """Jeffries-Matusita distance between two Gaussian classes (multivariate)."""
    a, b = np.atleast_2d(a.T).T, np.atleast_2d(b.T).T
    m1, m2 = a.mean(0), b.mean(0)
    c1, c2 = np.atleast_2d(np.cov(a, rowvar=False)), np.atleast_2d(np.cov(b, rowvar=False))
    c = (c1 + c2) / 2
    dm = (m1 - m2)[:, None]
    bh = (dm.T @ np.linalg.pinv(c) @ dm).item() / 8 + 0.5 * np.log(np.linalg.det(c) / np.sqrt(np.linalg.det(c1) * np.linalg.det(c2)))
    return 2 * (1 - np.exp(-bh))


# multi-temporal SAR per pixel: same polygons, same pixel order at every epoch -> join on position
def mt(c):
    with rasterio.open(F / "fused_stack_T1_20250216.tif") as s:
        tf, shape = s.transform, s.shape
    m = geometry_mask(geoms[c], out_shape=shape, transform=tf, invert=True)
    cols = {}
    for ep, d in EPOCHS:
        with rasterio.open(F / f"fused_stack_{ep}_{d}.tif") as s:
            cols[f"VV_{ep}"] = s.read(1).astype("float64")[m]
    return pd.DataFrame(cols).dropna().values


SAR = ["VV_dB", "VH_dB"]  # VV-VH is an exact linear combination of the two -> left out of multivariate sets (singular)
sep = []
for c1, c2 in combinations([c for c in CLASSES if c != "pontoon_bridge"], 2):
    a, b = data[("T1", c1)], data[("T1", c2)]
    row = {"pair": f"{c1} vs {c2}"}
    for f in FEATS:
        row[f] = jm(a[[f]].values, b[[f]].values)
    row["SAR T1 (VV, VH)"] = jm(a[SAR].values, b[SAR].values)
    row["SAR multi-temporal (VV T0, T1, T2)"] = jm(mt(c1), mt(c2))
    row["EO T1 (6 bands)"] = jm(a[BANDS].values, b[BANDS].values)
    row["Fused T1 (SAR + EO)"] = jm(a[SAR + BANDS].values, b[SAR + BANDS].values)
    sep.append(row)
sep = pd.DataFrame(sep).round(3)
sep.to_csv(ROOT / "09_docs" / "signatures_separability.csv", index=False)

# ---- figure 1: box plots, rows = features, cols = epochs ----
fig, axes = plt.subplots(len(FEATS), 3, figsize=(15, 3.1 * len(FEATS)), sharey="row")
for i, f in enumerate(FEATS):
    for j, (ep, _) in enumerate(EPOCHS):
        ax = axes[i, j]
        vals = [data[(ep, c)][f].values for c in CLASSES]
        bp = ax.boxplot(vals, showfliers=False, patch_artist=True, widths=0.6)
        for patch, c in zip(bp["boxes"], CLASSES):
            patch.set_facecolor(COLOURS[c]); patch.set_alpha(0.6)
        ax.set_xticks(range(1, len(CLASSES) + 1), [c.replace("_", "\n") for c in CLASSES], fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        if i == 0:
            ax.set_title(f"{ep} {EPOCHS[j][1]}")
        if j == 0:
            ax.set_ylabel(f)
fig.suptitle("Signatures per class and epoch (polygons fixed in space: 'tent_block' at T0/T2 = same ground before/after)", fontsize=12)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "signatures_boxplots.png", dpi=65); plt.close(fig)

# ---- figure 2: spectral profiles at T1 + SAR bar chart ----
wl = {"B02": 490, "B03": 560, "B04": 665, "B08": 842, "B11": 1610, "B12": 2190}
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
for c in CLASSES:
    df = data[("T1", c)]
    ax[0].plot([wl[b] for b in BANDS], [df[b].median() for b in BANDS], "-o", color=COLOURS[c], label=c)
    ax[0].fill_between([wl[b] for b in BANDS], [df[b].quantile(0.25) for b in BANDS], [df[b].quantile(0.75) for b in BANDS],
                       color=COLOURS[c], alpha=0.12)
ax[0].set_xlabel("wavelength (nm)"); ax[0].set_ylabel("surface reflectance"); ax[0].set_title("Sentinel-2 spectral signatures, T1 (median, IQR)")
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
x = np.arange(len(CLASSES))
for k, (f, off) in enumerate((("VV_dB", -0.2), ("VH_dB", 0.2))):
    med = [data[("T1", c)][f].median() for c in CLASSES]
    lo = [data[("T1", c)][f].quantile(0.25) for c in CLASSES]
    hi = [data[("T1", c)][f].quantile(0.75) for c in CLASSES]
    ax[1].errorbar(x + off, med, yerr=[np.subtract(med, lo), np.subtract(hi, med)], fmt="o" if k == 0 else "s", capsize=4,
                   label=f.replace("_dB", ""))
ax[1].set_xticks(x, [c.replace("_", "\n") for c in CLASSES], fontsize=8); ax[1].set_ylabel("sigma0 (dB)")
ax[1].set_title("Sentinel-1 backscatter signatures, T1 (median, IQR)"); ax[1].legend(); ax[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "signatures_spectral.png", dpi=70); plt.close(fig)

# ---- figure 3: trajectories T0 -> T1 -> T2 of VV and NDBI for each class's ground ----
fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
for c in CLASSES:
    for a, f in zip(ax, ("VV_dB", "VVminusVH_dB", "NDBI")):
        a.plot([0, 1, 2], [data[(ep, c)][f].median() for ep, _ in EPOCHS], "-o", color=COLOURS[c], label=c)
for a, f in zip(ax, ("VV_dB", "VVminusVH_dB", "NDBI")):
    a.set_xticks([0, 1, 2], ["T0\n2024-11", "T1\n2025-02", "T2\n2025-04"]); a.set_title(f"{f} median"); a.grid(alpha=0.3)
ax[0].legend(fontsize=8)
fig.suptitle("Change trajectories on fixed ground (tent ground: sand -> tents -> sand)", fontsize=12)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "signatures_trajectory.png", dpi=70); plt.close(fig)

pt = stats[stats.feature.isin(FEATS)].pivot_table(index=["class", "epoch"], columns="feature", values="median")[FEATS]
print(pt.round(2).to_string())
print("\nT1 separability (JM, 0..2):")
print(sep.to_string(index=False))
print("\npixels per class at T1:", {c: len(data[("T1", c)]) for c in CLASSES})
