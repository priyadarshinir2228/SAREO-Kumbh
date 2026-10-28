# Optical (EO) Processing and Enhancement — SAREO-Kumbh (Phase 7, brief items 3.1 and 3.2)

**Date:** 23 Oct 2026 · **Data:** Sentinel-2 L2A, tile 44RNP, processing baseline 05.11 — T0 2024-11-13 (S2A), T1 2025-02-16 (S2B), T2 2025-04-17 (S2B)

## 1. Preprocessing (brief 3.1) — `10_scripts/s2_preprocess.py`

| Step | What was done | Why |
| --- | --- | --- |
| Radiometric / atmospheric correction | Not re-done: L2A is already bottom-of-atmosphere reflectance (Sen2Cor). Converted DN → reflectance with **ρ = (DN + BOA_ADD_OFFSET) / QUANTIFICATION = (DN − 1000) / 10000**, values read from each product's `MTD_MSIL2A.xml` | Baseline ≥ 04.00 adds a −1000 offset; forgetting it biases every band by +0.1 |
| Cloud and shadow masking | Masked where SCL ∈ {0 no data, 1 saturated, 3 cloud shadow, 8 cloud medium, 9 cloud high, 10 cirrus} or DN = 0 → NaN; mask saved separately | Keeps cloud-contaminated pixels out of indices and signatures |
| Subsetting to the AOI | Exact AOI window 582400–596600 E, 2807200–2821000 N, read straight from the zip | Tile 44RNP is UTM 44N with origin on the 20 m grid → a pure crop, no reprojection |
| Band stacking | 10 bands: B02 B03 B04 B05 B06 B07 B08 B8A B11 B12, named in the file | One file per date for composites, indices and fusion |
| Resampling | 20 m bands → 10 m **bilinear**; SCL → 10 m **nearest neighbour** | Continuous vs categorical data |
| Reprojection | None needed (already EPSG:32644). Verified: **identical grid to the Sentinel-1 rasters** (same transform, 1420 × 1380 px) | Fusion without any further resampling |

| Date | Tile cloud | AOI masked | SCL classes present (AOI) |
| --- | --- | --- | --- |
| 2024-11-13 | 0.010% | 0.040% | 4 vegetation, 5 not vegetated, 6 water, 7 unclassified, 8 cloud medium (608 px) |
| 2025-02-16 | 0.001% | 0.009% | 2 dark area, 4, 5, 6, 7, 8 (164 px), 9 cloud high (4 px) |
| 2025-04-17 | 0.002% | 0.022% | 2, 4, 5, 6, 7, 8 (12 px) |

Outputs: `02_preproc/S2/S2_<date>_L2A_refl10m.tif` (Float32, NaN = masked), `_SCL10m.tif`, `_mask10m.tif`. Reflectance 1st–99th percentile: 0.008–0.39 (T0), 0.019–0.43 (T1), −0.021–0.46 (T2). Small negatives over dark water are normal for L2A and are kept.

## 2. Image enhancement (brief 3.2) — `09_docs/s2_enhancement_panel.png`

The same T1 natural-colour image shown with six display transforms (reflectance values are never changed):

| Transform | Result |
| --- | --- |
| No stretch (0–1) | Almost black: surface reflectance occupies 0–0.3 |
| Min–max linear | Still dark: a few specular pixels reach reflectance 2.31, so the full range is wasted on outliers |
| **2–98 % linear per band** | Best general-purpose display: tent grid, roads, pontoon bridges and water all readable. **Used for all map products** |
| Histogram equalisation | Maximum contrast, flat histogram; exaggerates sand texture and shifts colours — good for spotting faint roads, poor for interpretation of colour |
| 2–98 % + gamma 0.7 | Brightens mid-tones; tent blocks and lanes separate better |
| 2–98 % + gamma 1.4 | Darkens mid-tones; bright tents and sand bars stand out against everything else |

## 3. Colour composites — `09_docs/s2_composites.png`

| Composite | Bands (R-G-B) | What it shows here |
| --- | --- | --- |
| Natural colour | B04-B03-B02 | Tent city as a white/grey grid on the floodplain at T1; bare sand at T0/T2; river green-brown |
| False-colour infrared | B08-B04-B03 | Vegetation red; tents and sand cyan-white; water black — fields east of the Ganga very clear |
| SWIR | B12-B8A-B04 | Vegetation green; tents and sand pink-white; water dark blue; moisture differences on the floodplain |

Saved as lossless virtual rasters (`03_enhanced/S2/S2_<date>_<comp>.vrt`, pointing at the reflectance stack) and as 8-bit 2–98 % display copies (`_p2-98.tif`, for layouts only — never for analysis).

## 4. Spectral indices — `09_docs/s2_indices.png`

| Index | Formula | Median T0 / T1 / T2 | Reading |
| --- | --- | --- | --- |
| NDVI | (B08 − B04) / (B08 + B04) | +0.28 / +0.23 / +0.20 | Vegetation > 0.4 (fields east of the Ganga, gardens); falls as crops are harvested toward April |
| MNDWI | (B03 − B11) / (B03 + B11) | −0.43 / −0.36 / −0.41 | Water > 0 — river channels; Ganga narrower in February than in November |
| NDBI | (B11 − B08) / (B11 + B08) | +0.05 / +0.04 / +0.10 | Built-up / tents > 0, **but also high over bare sand and turbid water** — not usable alone to separate tents from sand; SAR is needed for that |

## 5. AI cloud mask comparison — `10_scripts/s2_cloudmask_ai.py`, `09_docs/cloudmask_comparison.csv`

| Date | SCL masked | OmniCloudMask masked | Agreement | Run time (CPU) |
| --- | --- | --- | --- | --- |
| 2024-11-13 | 0.031% | 0.000% | 99.969% | 26 s |
| 2025-02-16 | 0.009% | 0.000% | 99.991% | 24 s |
| 2025-04-17 | 0.001% | 0.000% | 99.999% | 24 s |

- All three scenes are cloud-free, so the comparison mainly shows **false positives**: the pixels SCL flags as cloud sit next to very bright surfaces (T1 class-9 neighbours: B02 0.24, B11 0.43 — about 3× and 2× the scene medians), i.e. most likely white tent roofs and metal sheets. OmniCloudMask did not flag them.
- Kappa is undefined in practice (0) because OmniCloudMask flagged nothing.
- The conservative SCL mask is kept (it removes 168 px at T1). A proper test needs a cloudy scene — the optional T3 Sentinel-2 (2025-09-24, tile cloud 13.9%) in the manifest; planned for Phase 14.
- Technical note: PyTorch and the conda GDAL stack load different OpenMP runtimes. The model therefore runs in a separate process (`ocm_worker.py`); the unsafe `KMP_DUPLICATE_LIB_OK` workaround was deliberately not used.

## 6. Files

- QGIS: drag `08_layouts/S2_composites_indices.qlr` into the project (group "S2 L2A (10 m)", T1 natural colour visible), move it into **02_EO**, save.
- Scripts: `inspect_s2.py`, `s2_preprocess.py`, `s2_enhance.py`, `s2_cloudmask_ai.py` + `ocm_worker.py`, `make_s2_qlr.py`.
- Environment change: installed `libgdal-jp2openjpeg` (conda-forge) for Sentinel-2 JPEG2000; `sareo_env.ps1` now sets `GDAL_DRIVER_PATH`.
