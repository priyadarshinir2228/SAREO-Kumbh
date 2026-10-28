# QGIS Plugin Demonstrations — SAREO-Kumbh (Phase 11, brief item 8)

**Date:** 23 Oct 2026 · **QGIS:** 3.44.14 LTR · **Demo project:** `D:\SAREO-Kumbh\SAREO_plugin_demo.qgz` (separate from `SAREO_Kumbh.qgz`, EPSG:32644, relative paths). It already contains every layer the demos below need: S2 T1 natural colour, S1 σ⁰ dB T0/T1/T2, the T1 fused stack, tent blocks, pontoon bridges, temporary roads, training samples, the four sector shapefiles and a Serval-safe raster copy.

**How to use this booklet:** open the demo project, follow each plugin's steps, and save the screenshot under the file name given into `09_docs/plugin_screenshots/` (create the folder). The report's plugin section is built from these screenshots and the results below.

## Overview

| # | Plugin | Purpose in this project | Demonstrated | Result |
| --- | --- | --- | --- | --- |
| 1 | **Orfeo ToolBox provider** 3.0.3 | SAR speckle filters (Kuan, Lee, Frost, Gamma-MAP), PCA, contrast | ✔ scripted (Phase 6) + GUI | Kuan 3/5/7 in the filter comparison |
| 2 | **GRASS GIS provider** | 307 raster/vector tools (e.g. r.texture for SAR texture) | ✔ enabled, GUI step | — |
| 3 | **Georeferencer** (core) | GCP georeferencing of a scanned map | ✔ scripted (Phase 8) + GUI with `.points` file | Polynomial 2: 5.1 m check RMSE |
| 4 | **Raster Calculator** (core) | Band maths: ΔVV = VV_T1 − VV_T0 | ✔ scripted (QgsRasterCalculator) + GUI | Identical to NumPy (max difference 0.0 dB); 11.1 % of pixels ≥ +3 dB |
| 5 | **Graphical Modeler** (core) | Reusable tent-change workflow | ✔ model built and run | 256 polygons, 17.2 km², 85 % of tent blocks |
| 6 | **QuickOSM** 2.5.4 | OSM roads, bridges, water | ✔ provider loads; ✖ run blocked by Overpass 502 today | Same query done in Phase 4 via Overpass (240 bridges) |
| 7 | **QuickMapServices** 1.5.2 | Basemaps (OSM, ESRI World Imagery) for visual checks | GUI | — |
| 8 | **Value Tool** | Read σ⁰ / reflectance of all layers under the cursor | GUI | — |
| 9 | **Profile Tool** 4.3.4 | Backscatter profiles across tents, river, bridges | GUI | — |
| 10 | **Serval** 3.32.0 | Edit raster pixel values (fix an artefact) | GUI (on a copy) | — |
| 11 | **MMQGIS** 2024.11.8 | Merge the 4 sector shapefiles (brief item 9, GUI route) | GUI | Compare with the scripted merge: 51 features, 12.275 km² |
| 12 | **Topology Checker** 1.1.0 | Topology rules on the feature database | GUI | Scripted check found 0 overlaps |
| 13 | **dzetsaka** 5.1.1 | Random Forest / GMM / SVM classification | GUI (scikit-learn installed for it) | — |
| 14 | **Semi-Automatic Classification (SCP)** 8.5.0 | Band set, spectral signatures, classification | GUI only (needs the map canvas) | — |
| 15 | **GeoAI** 1.8.1 | SAM-based AI segmentation of tent blocks | GUI (install its dependencies first) | Phase 14 compares with the rule-based tents |

Plugins 1–6 were run by script where they offer a Processing provider (OTB, GRASS, QuickOSM) or a core API (Georeferencer, Raster Calculator, Modeler). Plugins 7–15 work only inside the QGIS window: SCP fails headless (`iface.mapCanvas()` is None), and dzetsaka and MMQGIS have no Processing provider.

## 1. Orfeo ToolBox provider

- **Setup done:** `OTB_FOLDER = D:/OTB`, `OTB_APP_FOLDER = D:/OTB/lib/otb/applications` (the plugin has no "Activate" box).
- **Steps:** Processing Toolbox → OTB → Feature Extraction → **Despeckle** → Input `S1 T1 2025-02-16 sigma0 dB` *(use the linear file `02_preproc/S1/S1A_20250216_Sig0_nofilter_lin.tif` — filters need linear σ⁰)* → Filter `Lee`, radius 2, looks 4 → Run.
- **Result:** smoother image with the pontoon bridges kept; compare with the Phase 6 table (Kuan 7×7: ENL 26.4, EPI 0.70).
- 📷 `01_otb_despeckle.png`

## 2. GRASS GIS provider

- **Steps:** Processing Toolbox → GRASS → Raster → **r.texture** → Input = T1 VV band → method `asm` (angular second moment), window 7 → Run.
- **Result:** texture image — tent blocks show regular, high-texture patterns compared with smooth sand.
- 📷 `02_grass_rtexture.png`

## 3. Georeferencer

- **Steps:** Layer → Georeferencer → open `04_coreg/georef_demo/unreferenced_sector_map.tif` → File → **Load GCP points** → `unreferenced_sector_map.tif.points` (15 GCPs) → Settings → Transformation **Polynomial 2**, resampling Nearest, target CRS EPSG:32644 → Start.
- **Result:** residuals table (mean 3.8 m, max 5.8 m); output aligns with S2 T1. Try Polynomial 1 and Thin Plate Spline to see the RMSE changes reported in Phase 8.
- 📷 `03_georeferencer_gcps.png`, `03b_georef_result.png`

## 4. Raster Calculator

- **Steps:** Raster → Raster Calculator → expression `"S1 T1 2025-02-16 sigma0 dB (VH, VV)@2" - "S1 T0 2024-11-12 sigma0 dB (VH, VV)@2"` → output `07_analysis/plugin_demos/rastercalc_dVV_gui.tif` → OK.
- **Scripted result:** `rastercalc_dVV_T1-T0.tif` — identical to the NumPy difference (max |Δ| = 0.0 dB); **11.1 %** of the AOI gained ≥ 3 dB between T0 and T1 (new tents, bridges, structures).
- 📷 `04_raster_calculator.png` (style the result with a diverging ramp −10…+10 dB)

## 5. Graphical Modeler

- **Model:** `09_docs/models/tent_change_mask.model3` — inputs SAR T0, SAR T1, threshold (3 dB) → **Raster calculator** (A − B ≥ threshold) → **Sieve** (< 50 px) → **Polygonize** → **Extract DN = 1**.
- **Steps:** Processing → Graphical Modeler → Model → Open → `tent_change_mask.model3` (shows the 4-step diagram) → Run → T0 = S1 T0, T1 = S1 T1, threshold 3.
- **Scripted result:** without the sieve 10,148 fragments (speckle); with it **256 polygons, 17.2 km², covering 85 % of the rule-based tent blocks** — the model's simpler rule (no T2 or NDVI test) also picks up new permanent structures.
- 📷 `05_modeler_diagram.png`, `05b_model_output.png`

## 6. QuickOSM

- **Steps:** Vector → QuickOSM → QuickOSM → Key `bridge`, Value `yes` → **Extent of a layer** → `tent_blocks` (or Canvas extent) → Run Query.
- **Status:** the Processing provider loads; the scripted run on 23 Oct 2026 failed because **both public Overpass servers returned "502 Bad Gateway"** (server outage). Retry later or choose another server in QuickOSM → Parameters. The same data was already fetched in Phase 4 (`06_vectors/osm.gpkg`, 240 bridges).
- 📷 `06_quickosm.png`

## 7. QuickMapServices

- **Steps:** Web → QuickMapServices → Settings → More services → **Get contributed pack** → Web → QuickMapServices → **ESRI → ESRI Satellite** (and OSM → OSM Standard).
- **Use:** visual reference for tent blocks and bridges; note that today's basemap imagery is not from February 2025.
- 📷 `07_qms_basemap.png`

## 8. Value Tool

- **Steps:** Plugins → Value Tool (panel opens) → tick S1 T0, T1, T2 and the T1 fused stack → move the cursor over (a) a tent block, (b) the river, (c) a pontoon bridge, (d) dry sand.
- **Expected:** tent block VV rises from about −12 dB (T0) to about −5 dB (T1) and falls back (T2); river ≈ −20 dB; bridge > 0 dB at T1; NDVI and MNDWI in the stack bands.
- 📷 `08_value_tool.png` (cursor on a tent block, all values visible)

## 9. Profile Tool

- **Steps:** Plugins → Profile Tool → Terrain profile → Add layers S1 T0 and S1 T1 (band 2 = VV) → draw a line west–east across the Sangam at about 2,813,000 N (city → Ganga with bridges → tent city).
- **Expected:** at T1 a sawtooth of bright peaks where the line crosses bridges and tent rows; at T0 a flat dark floodplain (compare `09_docs/filter_panel.png` profile).
- 📷 `09_profile_tool.png`

## 10. Serval

- **Steps:** select the layer **`serval_demo_copy_T1_dB`** (a copy — never edit the originals) → Serval toolbar → band 2 → **Probe** a speckle spike or NoData pixel → set a new value or use **3×3 mean** → Save.
- **Purpose:** shows manual raster correction (e.g. a single corrupted pixel). Record the edit in the processing log.
- 📷 `10_serval.png`

## 11. MMQGIS — merge layers (brief item 9, GUI route)

- **Steps:** MMQGIS → Combine → **Merge Layers** → select `tents_sector_NW`, `_NE`, `_SW`, `_SE` → output `07_analysis/plugin_demos/mmqgis_merged.shp`.
- **Expected and lesson:** MMQGIS merges by **field name** — the NE (`Class`, `Area`, `Conf`) and SW (`CLASS`, `AREA_HA`) fields stay separate columns. That is why the scripted route ran **Refactor fields** first (Phase 10: 51 features, one schema, 12.275 km²). Compare the two attribute tables.
- 📷 `11_mmqgis_merge.png`

## 12. Topology Checker

- **Steps:** Vector → Topology Checker → Configure → add rules: `tent_blocks` **must not overlap**; `tent_blocks` **must not have invalid geometries**; `temp_roads` **must not have dangles** → Validate All.
- **Expected:** 0 overlap and 0 invalid errors (matches `09_docs/validation_report.csv`); dangles on `temp_roads` are expected because roads are clipped at tent-block edges.
- 📷 `12_topology_checker.png`

## 13. dzetsaka (Random Forest)

- **Setup done:** scikit-learn 1.9.1 installed into QGIS's Python (user install, no admin).
- **Steps:** dzetsaka toolbar → Input raster `T1 fused stack (11 bands)` → Training layer `training_samples`, column **`code`** (1 water, 2 tent block, 3 sand, 4 vegetation, 5 built-up) → classifier **Random Forest** → output `07_analysis/plugin_demos/dzetsaka_RF_T1.tif` → Run.
- **Expected:** a 5-class map; check the confusion values dzetsaka prints. Phase 13 repeats this in Python with the separate `validation` layer for an honest accuracy.
- 📷 `13_dzetsaka.png`

## 14. Semi-Automatic Classification Plugin (SCP)

- **Steps:** SCP → **Band set** → add the S2 T1 bands (or the fused stack) → **Training input** → create a new training file and import `training_samples` (field `code` as macroclass) → **Spectral signature** plot for the 5 classes → Band processing → **Classification** → Random Forest → Run.
- **Expected:** signature plot showing tents bright in visible/SWIR like sand, but separable in SAR bands; a classified map.
- 📷 `14a_scp_signatures.png`, `14b_scp_classification.png`

## 15. GeoAI (Segment Anything)

- **Setup (once):** Plugins → GeoAI → follow its prompt to **install dependencies** (PyTorch CPU + `geoai`; a few hundred MB). SAM 3 needs a Hugging Face account with model access; SAM / SAM 2 do not.
- **Steps:** GeoAI → Segment → input `S2 T1 natural colour` → click points or draw a box on 3–5 tent blocks → Run → save polygons to `07_analysis/plugin_demos/geoai_sam_tents.gpkg`.
- **Expected:** block outlines that follow the visible tent grid; Phase 14 compares them with the rule-based `tent_blocks` (IoU, time per km²).
- 📷 `15_geoai_sam.png`

## Files

- `SAREO_plugin_demo.qgz` (demo project), `07_analysis/plugin_demos/` (outputs), `09_docs/models/tent_change_mask.model3`, `06_vectors/training_samples.gpkg` (200 polygons: 144 training, 56 validation).
- Scripts: `10_scripts/plugin_demos_qgis.py`, `make_training_samples.py`.
- Environment changes: plugin enabled flags written to the QGIS profile; scikit-learn installed for QGIS Python (`pip install --user`).
