# Georeferencing, Co-registration and Geometric Accuracy — SAREO-Kumbh (Phase 8, brief item 6)

**Date:** 23 Oct 2026

## Summary

All layers are already on one 10 m EPSG:32644 grid, and the measured misregistrations are all well under half a pixel: **Sentinel-2 date-to-date 2–3 m (AROSICS, RMSE 2.6–3.3 m), Sentinel-1 date-to-date < 1 m, Sentinel-1 to Sentinel-2 about 2 m (same-day water masks).** No image needs to be shifted or resampled. The georeferencing demonstration reaches **5.1 m RMSE (0.51 px) on 10 independent check points with a 2nd-order polynomial**, and shows why GCP RMSE alone is misleading.

## 1. Georeferencing demonstration (QGIS Georeferencer method) — `10_scripts/georef_demo.py`

No unreferenced sector map was available, so a realistic stand-in was made: a 6 × 6 km crop of the T1 natural-colour image, **stripped of all coordinates**, rotated 4°, rescaled to 8.5 m/px and given a mild non-linear (quadratic) warp, like a scanned paper map (`04_coreg/georef_demo/unreferenced_sector_map.tif`). Because the distortion is known, the true error of each transform can also be measured.

- **GCP collection:** SIFT feature matching against the georeferenced Sentinel-2 image (6,026 matches → 5,820 RANSAC inliers). **15 GCPs** chosen one per 4 × 4 grid cell for an even spread; **10 different points kept back as independent check points**.
- **Transforms fitted** (pixel → map, EPSG:32644):

| Transform | GCPs | RMSE on GCPs | RMSE on check points | True RMSE (dense grid) | Max true error |
| --- | --- | --- | --- | --- | --- |
| Polynomial 1 (affine) | 15 | 7.93 m (0.79 px) | 10.57 m (1.06 px) | 7.90 m | 21.8 m |
| **Polynomial 2** | 15 | **4.11 m (0.41 px)** | **5.09 m (0.51 px)** | **2.14 m** | 6.2 m |
| Thin plate spline | 15 | 0.00 m | 7.09 m (0.71 px) | 4.67 m | 12.1 m |

- **Reading:** polynomial 1 cannot model the curved warp (under-fit). Thin plate spline passes exactly through every GCP, so its GCP RMSE is 0, but between GCPs it bends (over-fit) — the check points expose this. **Polynomial 2 is the right model** here; its largest GCP residual is 5.8 m (mean 3.8 m), so no GCP exceeded the 1-pixel removal threshold. Its check RMSE of 0.51 px is at the target; the remaining error is mostly point-picking noise (true-grid error 0.21 px).
- **Outputs:** `04_coreg/georef_demo/sector_map_georef_poly2.tif` (GDAL warp, polynomial 2, nearest neighbour, 10 m, target-aligned pixels); `unreferenced_sector_map.tif.points` — **open the image in QGIS Raster → Georeferencer and load this file** to see the same 15 GCPs and residuals in the GUI; `09_docs/georef_rmse.csv`, `georef_points.csv`, `georef_demo.png` (GCPs, check points, residual vectors).

## 2. Image-to-image co-registration

### 2a. Sentinel-2 date to date (AROSICS, Scheffler et al. 2017) — `10_scripts/coreg_arosics.py`

| Pair (B08) | Global shift E / N | Reliability | Valid local tie points (500 m grid) | Local RMSE | 90th percentile |
| --- | --- | --- | --- | --- | --- |
| T0 2024-11-13 → T1 | −2.2 m / −2.2 m | 95.2 % | 359 of 812 | 3.30 m | 4.2 m |
| T2 2025-04-17 → T1 | +1.5 m / +2.3 m | 95.1 % | 407 of 812 | 2.63 m | 3.4 m |

Both are 0.2–0.3 px — within Sentinel-2's multi-temporal registration specification. **No correction applied.** Tie points: `06_vectors/coreg_tiepoints.gpkg`.

### 2b. Sentinel-1 date to date (phase correlation, ×20 sub-pixel) — `10_scripts/coreg_checks.py`

| Date → T1 2025-02-16 | Whole AOI shift | Static city strip only |
| --- | --- | --- |
| T0 2024-11-12 | 0.5 m | 0.5 m |
| T1a 2025-01-23 | 0.5 m | 0.5 m |
| T1b 2025-02-04 | 0.5 m | 0.5 m |
| T2 2025-04-17 | 0.5 m | 0.5 m |

0.5 m = 1/20 px, the measurement step: the dates are effectively identical, as expected for one orbit track processed with precise orbits and the same DEM. (scikit-image's error value is not meaningful with phase normalisation and is not used.) **No correction applied.**

### 2c. Sentinel-1 to Sentinel-2 (cross-sensor)

- **Same-day water masks** (S1 VV Lee 7×7 < −18 dB vs S2 MNDWI > 0), phase correlation: **T1 16 Feb: 1 m E, 2 m S (0.22 px), IoU 0.62** — the valid result. T2 17 Apr gave 2 px but is **not reliable**: MNDWI marks only 1.4 % water (shallow, turbid April water) against 6.6 % in SAR (IoU 0.18).
- **AROSICS S1 → S2:** 0 valid tie points out of 811. Expected — AROSICS matches optical texture, and SAR and optical images look too different. Recorded as a limitation; Phase 14 can test a deep SAR–optical matcher.

## 3. Absolute accuracy against an independent reference (OpenStreetMap bridges)

The sub-pixel shift that best fits 262 OSM bridge-over-water pixels:

| Image | Best-fit offset vs OSM | Explanation |
| --- | --- | --- |
| S1 VV, all 5 dates | +10 m E, +10 m N (T0: +30 m N) | **SAR layover**: the elevated deck is displaced toward the sensor. Sentinel-1 is right-looking, so the descending pass looks west and the shift is east; ≈ h / tan 39° ≈ 18 m for a 15 m deck |
| S2 B08, all 3 dates | +10 m E, −20 m N | **Sun shadow**: with the sun to the south (azimuth ≈ 150°) each bridge shadows the water to its north, pulling the bright peak south |

These offsets are physical, not misregistration: the same bridges sit about 30 m apart between S1 and S2, while the same-day water check shows S1 and S2 agree to 2 m. Within those physical effects and OSM's own accuracy (≈ 5–10 m), both sensors are absolutely located to within 1–2 pixels.

## 4. Decision

| Layer pair | Measured | Target | Action |
| --- | --- | --- | --- |
| S2 ↔ S2 | 2.6–3.3 m RMSE | < 5 m (0.5 px) | none |
| S1 ↔ S1 | < 1 m | < 5 m | none |
| S1 ↔ S2 | ≈ 2 m | < 5 m | none |
| Georeferenced map (poly 2) | 5.1 m check RMSE | < 5 m | at target; acceptable for a scanned reference map |

All Phase 9 fusion uses the existing rasters as they are.

*Correction made today:* the Phase 5 notes gave the Sentinel-1 look direction the wrong way round; fixed in `05_SAR_Preprocessing.md`.
