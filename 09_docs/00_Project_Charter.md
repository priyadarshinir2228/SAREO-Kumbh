# Project Charter — SAREO-Kumbh

**Title:** GeoFusion-QGIS: Monitoring the Maha Kumbh 2025 Tent City at Prayagraj Using Multi-Sensor SAR and Optical Imagery in QGIS
**Short name:** SAREO-Kumbh
**Context:** Internship selection assessment (remote sensing / GIS)
**Version:** 0.1 (Phase 0 draft) · 22 Oct 2026
**Submission deadline:** _TBD — fill in_

---

## 1. Problem statement

Mass temporary settlements — religious gatherings, refugee camps, disaster relief camps — appear and disappear within weeks. Planners and responders need fast, reliable maps of their extent, internal roads, river crossings and density, in any weather and at any time of day.

Optical satellite imagery is easy to interpret but is blocked by cloud, smoke and darkness. Synthetic Aperture Radar (SAR) works through cloud and at night but is noisy (speckle) and harder to read. Most existing settlement-mapping work uses expensive commercial very-high-resolution optical imagery on a single date.

This project builds an open-source, reproducible QGIS + SNAP workflow that combines free Sentinel-1 SAR and Sentinel-2 optical imagery to map the Maha Kumbh 2025 tent city at Prayagraj across its whole life cycle — empty floodplain, peak tent city, and cleared floodplain — and covers every task in the assessment brief.

## 2. Gap statement (updated after Phase 1 — see 02_Literature_Survey.md)

Mass temporary settlements have been imaged with SAR (ISRO's EOS-04 release of the Maha Kumbh 2025 tent city) and mapped with very-high-resolution commercial optical imagery and deep learning, or with Sentinel-1 at land-cover level. No published study measures the full life cycle of a mass temporary settlement — empty, peak and cleared — using only free Sentinel-1 and Sentinel-2 data in a documented, reproducible open-source GIS workflow, nor tests where AI tools improve on the classical steps of that workflow.

## 3. Objectives

1. Acquire Sentinel-1 and Sentinel-2 imagery for four epochs from authorised open portals, with full provenance.
2. Process SAR to analysis-ready backscatter and quantitatively evaluate speckle filters.
3. Preprocess and enhance optical imagery (cloud mask, stack, stretches, composites, indices).
4. Georeference and co-register all layers to sub-pixel accuracy, with RMSE reported.
5. Fuse SAR and optical data without loss of resolution or attributes.
6. Build a validated, well-documented feature database (tents, roads, pontoon bridges, water, buildings).
7. Produce a signature reference sheet and explain how backscatter changes with surface change.
8. Detect and measure the tent city's growth and removal, and classify land cover from SAR, EO and fused inputs.
9. Compare three classical steps with AI alternatives (despeckling, cloud masking, digitising).

## 4. Research questions

- **RQ1:** How does SAR backscatter change from empty floodplain (T0) to tent city (T1) and back (T2)?
- **RQ2:** Which speckle filter best preserves tent-block edges and pontoon bridges, measured by ENL and EPI?
- **RQ3:** Does SAR–EO fusion classify tents, sand, water and roads more accurately than either sensor alone?
- **RQ4:** How much do AI tools (deep despeckling, AI cloud masks, SAM digitising) improve on the classical steps?

## 5. Study area

| Item | Value |
| --- | --- |
| Location | Triveni Sangam (Ganga–Yamuna confluence), Prayagraj, Uttar Pradesh, India |
| Centre | about 25.425° N, 81.885° E |
| AOI (final, Phase 4) | UTM 44N 582400–596600 E, 2807200–2821000 N (100 m grid) ≈ 81.819–81.961° E, 25.378–25.504° N; 14.2 × 13.8 km = 195.96 km² — `06_vectors/AOI_Kumbh.gpkg`. North edge raised twice (25.47° → 25.49° → 25.504° N) after the S2 2025-02-11 extent check showed east-bank sectors at the edge |
| CRS / grid | WGS 84 / UTM 44N (EPSG:32644), 10 m |
| Event | Maha Kumbh Mela, 13 Jan – 26 Feb 2025 |

## 6. Epochs

| Epoch | Window | State of the floodplain | Status |
| --- | --- | --- | --- |
| T0 baseline | S1 2024-11-12 · S2 2024-11-13 | Dry floodplain, before tent construction (19 Oct still flooded; road lines by 8 Dec) | fixed (Phase 4) |
| T1 peak | S1 2025-02-16 (+ 2025-01-23, 2025-02-04) · S2 2025-02-16 | Full tent city on both banks | fixed (Phase 4) |
| T2 after | S1 2025-04-17 · S2 2025-04-17 | Cleared sand | fixed (Phase 4) |
| T3 optional | S1 2025-08-15 · S2 2025-09-24 | Monsoon flooding | optional |

All Sentinel-1 scenes: Sentinel-1A, relative orbit 92, descending (~00:28 UTC). Sentinel-2: tile 44RNP, baseline 05.11. See `04_Data_Selection.md`.

## 7. Scope

**In scope:** all 12 brief items on the Prayagraj AOI; four epochs; classical workflow; three AI comparisons.
**Out of scope:** commercial imagery purchase; training large deep-learning models; field survey; individual tent detection at 10 m (block level only).

## 8. Deliverables

1. Packaged QGIS project (`SAREO_Kumbh.qgz` + GPKG + GeoTIFF + styles), relative paths, tested on a second PC.
2. Report (15–25 pages): intent, literature + gap, data, methods, results, limitations, references.
3. Map layouts: AOI, S1 T0/T1/T2, filter panel, composites, fusion, change, classification.
4. Processing log, download log, SNAP graph XML, `.model3` models.
5. Plugin demo booklet and one-page signature reference sheet.
6. Optional 5-minute walkthrough video.

## 9. Tools

QGIS (LTR), ESA SNAP, Orfeo ToolBox, GDAL/OGR, Python (rasterio, numpy, geopandas, scikit-image, scikit-learn, arosics, omnicloudmask), QGIS plugins listed in the tracker (Phase 11).

## 10. Timeline (fill in once the deadline is known)

| Phase | Name | Target date |
| --- | --- | --- |
| 0 | Project setup and intent | |
| 1 | Literature survey | |
| 2 | Software installation | |
| 3 | AOI definition | |
| 4 | Data acquisition | |
| 5 | SAR preprocessing | |
| 6 | Speckle filter experiment | |
| 7 | EO preprocessing and enhancement | |
| 8 | Georeferencing and co-registration | |
| 9 | Lossless fusion | |
| 10 | Vector database, merging, validation | |
| 11 | Plugin demonstrations | |
| 12 | Signature reference sheet | |
| 13 | Change detection and classification | |
| 14 | AI comparisons | |
| 15 | Layouts, report, packaging | |
| 16 | Interview preparation | |

## 11. Risks

| Risk | Mitigation |
| --- | --- |
| 10 m cannot resolve single tents | Map tent blocks; verify with VHR basemaps / Umbra; state the limit |
| Sentinel-1 revisit gaps | Only Sentinel-1A covers T0/T1 (Sentinel-1C calibrated from 19 May 2025, usable for T3); pick nearest dates on one relative orbit |
| No ground truth | VHR basemaps + OSM + official sector maps as reference |
| SNAP memory limits | Subset early, process per epoch |
| No dugouts in AOI | Cover from literature in the signature sheet |
| Deadline pressure | Do graded items first; AI comparisons and optional items last |

See `01_Brief_to_Phase_Mapping.md` for how every brief item maps to a phase.
