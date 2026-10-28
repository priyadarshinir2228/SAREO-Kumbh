# Change Detection and Classification — SAREO-Kumbh (Phase 13)

**Date:** 23 Oct 2026 · **Data:** Sentinel-1A σ⁰ Lee 7×7 (5 dates, orbit 92), lossless SAR + EO stacks T0/T1/T2, sample polygons `06_vectors/training_samples.gpkg`

## Summary

- **Tent city from SAR change:** about **11 km² on 23 Jan 2025** (fixed +3 dB rule; 15 km² with the Otsu +2.0 dB threshold). It shrank to 8.7 km² by 16 Feb and was **gone by 17 Apr (0.3 km²)**. "Temporary" ground that appeared at T1 and vanished at T2: **12.2 km²**, matching the Phase 10 tent-block layer (12.3 km²).
- **Classification:** **fused SAR + EO with the T0/T2 SAR dates is the most accurate input — overall accuracy 0.867, kappa 0.82** on independent validation polygons — against 0.59 for SAR alone and 0.78 for optical alone. A temporal rule removes fallow fields mislabelled as tents, at a cost of 0.8 points of accuracy.

## 1. Log-ratio change detection — `10_scripts/change_detection.py`, `07_analysis/change/`

**Method:** LR = σ⁰_dB(later) − σ⁰_dB(earlier), VV, same orbit and grid. The ratio (a difference in dB) is used because speckle is multiplicative. Thresholds come from Otsu (maximum between-class variance) inside a 1.5 km floodplain envelope, compared with fixed thresholds.

| Product | Value |
| --- | --- |
| Otsu threshold, build-up LR (T1 − T0) | **+1.97 dB** (fixed rule: +3 dB) |
| Otsu threshold, clearing LR (T2 − T1) | **−3.53 dB** (fixed rule: −2 dB) |
| Appeared T0 → T1 (≥ +3 dB, ≥ 0.5 ha) | 15.45 km² |
| Disappeared T1 → T2 (≤ −2 dB) | 34.75 km² — includes crop harvest and drying soil across the whole AOI, not only tents |
| **Temporary (appeared and disappeared)** | **12.22 km²** |

Files: `LR_VV_T1-T0_dB.tif`, `LR_VV_T2-T1_dB.tif`, `change_class_T0-T1-T2.tif` (1 appeared and stayed, 2 disappeared only, 3 temporary); figure `09_docs/change_maps.png`.

## 2. Tent-city area over time (5 SAR dates) — `09_docs/change_area_timeseries.csv`, `change_area_timeseries.png`

Area where VV rose above the 12 Nov 2024 baseline, on ground that was bare (NDVI_T0 < 0.3), not water, inside the floodplain (0.5 ha minimum):

| Date | Event context | Fixed +3 dB | Otsu +2.0 dB |
| --- | --- | --- | --- |
| 2024-11-12 | baseline (floodplain drying, little setup) | 0.00 km² | 0.00 km² |
| 2025-01-23 | 10 days after opening; before Mauni Amavasya (29 Jan) | **10.95 km²** | **15.12 km²** |
| 2025-02-04 | Basant Panchami week | 10.25 km² | 13.72 km² |
| 2025-02-16 | after Maghi Purnima (12 Feb) | 8.71 km² | 11.53 km² |
| 2025-04-17 | seven weeks after the close (26 Feb) | 0.26 km² | 0.63 km² |

- The decline between late January and mid-February fits pilgrims leaving after the main bathing dates. That is an interpretation from the event calendar, not something the imagery proves on its own.
- Only these 5 dates are measured. Lines between them are not data, and the tent city was already being laid out in December (ISRO's EOS-04 image of 29 Dec 2024), so the build-up was not linear.
- The Otsu threshold is lower (+2.0 dB) and therefore includes weaker changes such as sparse tents, fences and cleared ground. The fixed +3 dB rule is the conservative estimate. Both are reported.

## 3. Random Forest classification — `10_scripts/classify_rf.py`, `07_analysis/classification/`

**Design:** 5 classes (water, tent block, sand, vegetation, built-up). 15,000 training pixels (3,000 per class) from **143 training polygons**. Accuracy from **all 17,611 pixels of 57 separate validation polygons**: the split is by polygon, so no polygon contributes to both. Random Forest: 300 trees, balanced class weights, minimum leaf 2, fixed seed.

| Input set | Features | Overall accuracy | Kappa | Macro-F1 | Polygon-majority accuracy | Mapped tent area |
| --- | --- | --- | --- | --- | --- | --- |
| SAR only (T1) | VV, VH, VV−VH | 0.594 | 0.490 | 0.549 | 0.717 | 30.2 km² |
| EO only (T1) | 6 S2 bands + NDVI + MNDWI | 0.784 | 0.714 | 0.742 | 0.811 | 36.0 km² |
| **Fused (T1)** | SAR + EO | **0.838** | **0.785** | 0.802 | 0.887 | 23.3 km² |
| SAR multi-temporal | VV, VH at T0/T1/T2 + 2 ΔVV | 0.792 | 0.724 | 0.764 | 0.849 | 19.8 km² |
| **Fused + temporal** | all 19 | **0.867** | **0.824** | **0.833** | **0.906** | 24.1 km² |
| Fused + temporal + change rule | as above; tent needs ΔVV ≥ +1 dB | 0.859 | 0.814 | 0.827 | 0.906 | **18.7 km²** |

**Producer's / user's accuracy (fused + temporal):** water 0.91 / 0.88 · **tent block 0.87 / 0.97** · sand 0.55 / 0.54 · vegetation 0.98 / 0.93 · built-up 0.91 / 0.81. Confusion matrices: `09_docs/classification_confusion.csv`; maps: `classification_maps.png`.

**Most important features (fused + temporal, Gini):** NDVI 0.13, VV at T2 0.11, B12 0.10, VV at T1 0.09, B11 0.07, VH at T2 0.07, VV at T0 0.07. The T0 and T2 SAR dates are among the top features, so **time is what the classifier uses to recognise temporary tents**.

**Reading:**
1. **Fusion helps:** +5.4 points over optical alone and +24 over SAR alone at T1; +8.3 over optical when SAR time is added.
2. **SAR alone** confuses tents with buildings (both strong scatterers) and sand with water (both dark): tent producer's accuracy only 0.36. **Optical alone** confuses tents with sand and bare fields, which look identical.
3. **Mapped tent area vs the change-based tent city** (share of mapped "tent" pixels lying on ground whose SAR did not change, i.e. not a tent):

| Input set | Mapped tent area | Within 100 m of the change-based tent city | On unchanged ground (ΔVV < +1 dB), e.g. fallow fields |
| --- | --- | --- | --- |
| EO only | 36.0 km² | 41 % | **48 %** |
| Fused | 23.3 km² | 60 % | 22 % |
| Fused + temporal | 24.1 km² | 62 % | 18 % |
| SAR multi-temporal | 19.8 km² | 69 % | 5 % |
| **Fused + temporal + change rule** | **18.7 km²** | **74 %** | **0 %** |

The remaining 26 % outside the Phase 10 tent blocks is ground that **did** change at T1 (parking, staging, new structures, sectors excluded by the stricter Phase 10 rule).

## 4. Problems found and fixed

1. **Contaminated sand samples.** The first run gave sand producer's accuracy 0.28, with 1,337 of 2,677 sand validation pixels called "tent". The sand samples came from the **April** sand-bar layer, which includes ground that carried **tents in February**. Fixed by excluding everything within 30 m of a tent block. Sand-as-tent confusion dropped from 1,337 to 80 pixels; overall accuracy (fused + temporal) rose from 0.821 to 0.867. Phase 12 signatures were recomputed with the clean samples.
2. **No bare-field class.** Fallow fields were labelled tent or sand. A sixth class sampled outside the floodplain found only 2 candidate polygons (the fields lie inside the 1.5 km envelope), so it was dropped. A physically based **change rule** was used instead: a tent must have appeared (ΔVV ≥ +1 dB).

## 5. Limitations

- **10 m resolution:** tents are mapped as blocks; lanes and sand between rows lower the tent signature, and closely spaced pontoon bridges merge (only 5 extracted in Phase 10).
- **Revisit:** only Sentinel-1A (12 days) for T0–T1; Sentinel-1C was not operational until 19 May 2025. Five dates cannot show the build-up between November and January.
- **No ground truth:** reference polygons come from the rule-based layers checked against the imagery, not from field survey or official sector maps. The tent sample is not fully independent of the change rules that drew it, so tent accuracy is optimistic; sand (PA 0.55) is the honest weak class.
- **Pixel autocorrelation:** validation pixels inside one polygon are correlated. The polygon split and the polygon-majority accuracy (0.906) reduce, but do not remove, this optimism.
- **Coherence change detection** was not run (no SLC data downloaded); it would add a phase-based change measure.

## 6. Files

`07_analysis/change/` (log-ratio and change-class rasters) · `07_analysis/classification/RF_<input set>_T1.tif` (6 maps with colour tables) · `09_docs/change_area_timeseries.csv`, `change_class_areas.csv`, `classification_accuracy.csv`, `classification_confusion.csv`, `classification_importance.csv`, figures `change_maps.png`, `change_area_timeseries.png`, `classification_maps.png`. Scripts: `change_detection.py`, `classify_rf.py`, `make_training_samples.py` (sand fix).
