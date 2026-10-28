"""Phase 13b: Random Forest classification of T1 (2025-02-16) with five input sets, accuracy on independent polygons.

Classes (training_samples.gpkg, code): 1 water, 2 tent_block, 3 sand, 4 vegetation, 5 built_up
Extra product 'Fused + temporal + change rule': pixels classified tent_block whose VV did not rise by >= 1 dB from T0 to
T1 are reassigned to sand (bare ground) - a temporary structure must have appeared; this removes fallow fields
(no 'bare field' class could be sampled) that otherwise look like tents.
Input sets:
  SAR-only        VV, VH, VV-VH (T1)
  EO-only         B02 B03 B04 B08 B11 B12 + NDVI MNDWI (T1)
  Fused           SAR-only + EO-only
  SAR multi-temp  VV and VH at T0, T1, T2 + dVV(T1-T0) + dVV(T2-T1)
  Fused + temporal   Fused + SAR multi-temp
Training: up to 3,000 pixels per class drawn from the 144 TRAINING polygons; accuracy from ALL pixels of the 56 separate
VALIDATION polygons (polygon-level split, so no polygon contributes to both). Random Forest: 300 trees, balanced class
weights, fixed seed. Metrics: overall accuracy, Cohen's kappa, producer's / user's accuracy, F1, per-polygon majority accuracy.
Outputs: 07_analysis/classification/RF_<set>_T1.tif (+ colour table), 09_docs/classification_accuracy.csv,
         classification_confusion.csv, classification_maps.png, classification_importance.csv
"""
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score

ROOT = Path(r"D:\SAREO-Kumbh")
F = ROOT / "05_fused"
OUT = ROOT / "07_analysis" / "classification"
OUT.mkdir(parents=True, exist_ok=True)
NAMES = {1: "water", 2: "tent_block", 3: "sand", 4: "vegetation", 5: "built_up"}
COLOURS = {1: (21, 101, 192), 2: (213, 0, 0), 3: (239, 143, 0), 4: (46, 125, 50), 5: (97, 97, 97)}
TENT_RULE_DB = 1.0  # post-classification: 'tent' needs a real SAR increase T0 -> T1, else bare ground (sand)
rng = np.random.default_rng(42)

stk = {}
for ep, d in (("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")):
    with rasterio.open(F / f"fused_stack_{ep}_{d}.tif") as s:
        stk[ep] = {s.descriptions[i]: s.read(i + 1).astype("float32") for i in range(s.count)}
        prof, tf, shape = s.profile, s.transform, s.shape
t1 = stk["T1"]
feat = {
    "VV": t1["VV_dB"], "VH": t1["VH_dB"], "VVminusVH": t1["VVminusVH_dB"],
    **{b: t1[b] for b in ("B02", "B03", "B04", "B08", "B11", "B12")}, "NDVI": t1["NDVI"], "MNDWI": t1["MNDWI"],
    "VV_T0": stk["T0"]["VV_dB"], "VH_T0": stk["T0"]["VH_dB"], "VV_T2": stk["T2"]["VV_dB"], "VH_T2": stk["T2"]["VH_dB"],
    "dVV_T1-T0": t1["VV_dB"] - stk["T0"]["VV_dB"], "dVV_T2-T1": stk["T2"]["VV_dB"] - t1["VV_dB"],
}
SAR = ["VV", "VH", "VVminusVH"]
EO = ["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "MNDWI"]
MT = ["VV_T0", "VV", "VV_T2", "VH_T0", "VH", "VH_T2", "dVV_T1-T0", "dVV_T2-T1"]
SETS = {"SAR-only": SAR, "EO-only": EO, "Fused": SAR + EO, "SAR multi-temporal": MT,
        "Fused + temporal": list(dict.fromkeys(SAR + EO + MT))}
valid = np.all([np.isfinite(v) for v in feat.values()], axis=0)


def labels(layer):
    g = gpd.read_file(ROOT / "06_vectors" / "training_samples.gpkg", layer=layer)
    lab = rasterize(zip(g.geometry, g["code"]), out_shape=shape, transform=tf, fill=0, dtype="uint8")
    pid = rasterize(zip(g.geometry, range(1, len(g) + 1)), out_shape=shape, transform=tf, fill=0, dtype="int32")
    return lab, pid


tr_lab, _ = labels("training")
va_lab, va_pid = labels("validation")
tr_idx = []
for c in NAMES:
    idx = np.flatnonzero((tr_lab.ravel() == c) & valid.ravel())
    tr_idx.append(rng.choice(idx, min(3000, len(idx)), replace=False))
tr_idx = np.concatenate(tr_idx)
va_idx = np.flatnonzero((va_lab.ravel() > 0) & valid.ravel())
print(f"training pixels {len(tr_idx)} | validation pixels {len(va_idx)} from {va_pid.max()} polygons")

acc_rows, conf_rows, imp_rows, maps = [], [], [], {}
RUN = list(SETS.items()) + [("Fused + temporal + change rule", SETS["Fused + temporal"])]
for name, cols in RUN:
    X = np.stack([feat[c].ravel() for c in cols], 1)
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced", n_jobs=-1, random_state=42, min_samples_leaf=2)
    rf.fit(X[tr_idx], tr_lab.ravel()[tr_idx])
    y_true, y_pred = va_lab.ravel()[va_idx], rf.predict(X[va_idx])
    rule = name.endswith("change rule")
    dvv = feat["dVV_T1-T0"].ravel()
    if rule:
        y_pred = np.where((y_pred == 2) & (dvv[va_idx] < TENT_RULE_DB), 3, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=list(NAMES))
    pa, ua = np.diag(cm) / cm.sum(1), np.diag(cm) / np.maximum(cm.sum(0), 1)
    # polygon-level: majority predicted class per validation polygon
    pids = va_pid.ravel()[va_idx]
    poly = pd.DataFrame({"pid": pids, "true": y_true, "pred": y_pred}).groupby("pid").agg(true=("true", "first"), pred=("pred", lambda s: s.mode()[0]))
    row = {"input_set": name, "n_features": len(cols), "overall_accuracy": (y_true == y_pred).mean(),
           "kappa": cohen_kappa_score(y_true, y_pred), "macro_F1": f1_score(y_true, y_pred, average="macro"),
           "polygon_majority_accuracy": (poly.true == poly.pred).mean()}
    for c, n in NAMES.items():
        row[f"PA_{n}"], row[f"UA_{n}"] = pa[c - 1], ua[c - 1]
    acc_rows.append(row)
    for i, c in enumerate(NAMES):
        conf_rows.append({"input_set": name, "true_class": NAMES[c], **{f"pred_{NAMES[k]}": int(cm[i, j]) for j, k in enumerate(NAMES)}})
    for c, imp in zip(cols, rf.feature_importances_):
        imp_rows.append({"input_set": name, "feature": c, "importance": imp})
    pred = np.zeros(shape, "uint8")
    flat = np.flatnonzero(valid.ravel())
    for k in range(0, len(flat), 400_000):  # predict in chunks to limit memory
        part = flat[k:k + 400_000]
        pred.ravel()[part] = rf.predict(X[part])
    if rule:
        pred[(pred == 2) & (feat["dVV_T1-T0"] < TENT_RULE_DB)] = 3
    maps[name] = pred
    p = prof.copy(); p.update(count=1, dtype="uint8", nodata=0, compress="deflate", predictor=1)
    path = OUT / f"RF_{name.replace(' ', '_').replace('+', 'plus')}_T1.tif"
    with rasterio.open(path, "w", **p) as dst:
        dst.write(pred, 1)
        dst.write_colormap(1, {0: (0, 0, 0, 0), **{c: (*COLOURS[c], 255) for c in NAMES}})
        dst.update_tags(CLASSES="; ".join(f"{c}={n}" for c, n in NAMES.items()), INPUTS=", ".join(cols))
    tent_km2 = (pred == 2).sum() * 100 / 1e6
    print(f"{name:20s} OA {row['overall_accuracy']:.3f}  kappa {row['kappa']:.3f}  F1 {row['macro_F1']:.3f}  "
          f"polygon {row['polygon_majority_accuracy']:.3f}  tent PA/UA {row['PA_tent_block']:.2f}/{row['UA_tent_block']:.2f}  "
          f"tent area {tent_km2:.1f} km2")
    acc_rows[-1]["tent_block_area_km2"] = tent_km2

pd.DataFrame(acc_rows).round(3).to_csv(ROOT / "09_docs" / "classification_accuracy.csv", index=False)
pd.DataFrame(conf_rows).to_csv(ROOT / "09_docs" / "classification_confusion.csv", index=False)
pd.DataFrame(imp_rows).round(4).sort_values(["input_set", "importance"], ascending=[True, False]).to_csv(
    ROOT / "09_docs" / "classification_importance.csv", index=False)

cmap = matplotlib.colors.ListedColormap(["white"] + [np.array(COLOURS[c]) / 255 for c in NAMES])
fig, axes = plt.subplots(1, len(maps), figsize=(5.2 * len(maps), 5.6))
for ax, (name, m) in zip(axes, maps.items()):
    r = next(a for a in acc_rows if a["input_set"] == name)
    ax.imshow(m, cmap=cmap, vmin=0, vmax=len(NAMES), interpolation="nearest"); ax.axis("off")
    ax.set_title(f"{name}\nOA {r['overall_accuracy']:.2f}  kappa {r['kappa']:.2f}", fontsize=10)
axes[-1].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=np.array(COLOURS[c]) / 255) for c in NAMES],
                labels=list(NAMES.values()), loc="lower right", fontsize=8)
fig.suptitle("Random Forest classification of T1 2025-02-16 - accuracy on independent validation polygons", fontsize=13)
fig.tight_layout(); fig.savefig(ROOT / "09_docs" / "classification_maps.png", dpi=55)
