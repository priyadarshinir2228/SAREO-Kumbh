# Classical vs AI Comparison — SAREO-Kumbh (Phase 14)

**Date:** 23 Oct 2026 · **Hardware:** CPU only (Intel Core Ultra 5 125H, no CUDA) · **Rule:** AI is reported as a comparison next to the classical step; the classical workflow remains the graded core.

## Summary

| Step | Classical | AI | Verdict for this project |
| --- | --- | --- | --- |
| Speckle filtering | Lee 7×7 (ENL 4.4) | SAR2SAR (self-supervised, Sentinel-1 GRD weights) | **AI keeps more VV detail; classical is safer overall.** Keep Lee 7×7 |
| Cloud / shadow masking | Sentinel-2 SCL | OmniCloudMask (2025) | **AI is better.** It avoids SCL's false clouds on bright floodwater and finds thin haze. Use OmniCloudMask for any cloudy date |
| Tent-block digitising | Rule-based SAR change polygons + manual editing | Segment Anything (SAM ViT-B), 10 clicks per 4 km² | **AI is a fast, clean first draft** (IoU 0.63 with the classical layer, 7 s per 4 km²). Use it with SAR change as a check |

## 1. Speckle filtering — SAR2SAR vs Lee 7×7 (T1 2025-02-16; same input, same terrain correction, same grid; Phase 6)

| Metric (VV unless stated) | Unfiltered | **Lee 7×7** | SAR2SAR (AI) | Better |
| --- | --- | --- | --- | --- |
| ENL, homogeneous land (↑) | 5.2 | 22.3 | **26.0** | AI |
| ENL, calm water (↑) | 3.6 | **12.6** | 0.8 | Classical — AI *adds* noise on dark water |
| Mean ratio (= 1) | 1.00 | **0.998** | 0.974 | Classical — AI darkens by 2.6 % |
| EPI, edges (↑) | 1.00 | 0.85 | **0.93** | AI |
| Point-target preservation (= 1) | 1.00 | 0.83 | **0.94** | AI (bridges, metal) |
| VH ENL (↑) | 3.8 | **13.0** | 7.8 | Classical |
| Run time, 16 km² subset | — | **118 s** | 371 s | Classical |

**Reading:** SAR2SAR is the best VV filter on land, keeping edges and bright point targets better than any classical filter. But it was trained on typical land scenes: on very dark, thermal-noise-corrected water it becomes unstable, it shifts the mean, and it smooths VH much less. For a chain that measures backscatter change, radiometric fidelity matters most, so **Lee 7×7 stays the production filter**. SAR2SAR is the better choice where only visual detail matters.

## 2. Cloud and shadow masking — OmniCloudMask vs SCL

**a) Clear project dates (Phase 7).** SCL masked 0.001–0.031 %, OmniCloudMask 0 %; agreement ≥ 99.97 %. SCL's few flags sat on bright tent roofs (false positives).

**b) Cloudy monsoon scenes (this phase).** AOI window from Earth Search (AWS), 10 m, same rules: `10_scripts/cloudmask_test_monsoon.py`, figure `09_docs/cloudmask_monsoon.png`.

| Scene | Category | SCL | OmniCloudMask | Agreement | Kappa | SCL only | OCM only |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-08-15 (S2B) | cloud + shadow | 54.6 % | 44.8 % | 82.6 % | 0.66 | 13.6 % | 3.8 % |
| | cloud | 43.3 % | 29.3 % | 81.2 % | 0.60 | 16.4 % | 2.4 % |
| | shadow | 11.3 % | 15.6 % | 91.5 % | 0.64 | 2.1 % | 6.3 % |
| 2025-09-24 (S2B) | cloud + shadow | 25.5 % | 36.7 % | 83.4 % | 0.62 | 2.7 % | 13.9 % |
| | cloud (incl. 9.3 % thin cloud by OCM) | 21.6 % | 26.5 % | 87.6 % | 0.66 | 3.7 % | 8.7 % |
| | shadow | 3.9 % | 10.1 % | 93.3 % | 0.50 | 0.2 % | 6.4 % |

**Reading:**
- On **15 Aug** SCL marks the **whole bright, flooded Ganga floodplain as cloud**. 43 % of its extra cloud lies within 300 m of the river channel, which covers only 18 % of the AOI — 2.4 times over-represented. OmniCloudMask masks only the real cloud puffs and their shadows.
- On **24 Sep** OmniCloudMask also detects **thin haze** (9.3 %) and more shadow that SCL misses.
- Run time: 7–8 s per scene on CPU.
- **Limitation:** no hand-labelled reference exists, so "better" rests on visual inspection of the natural-colour images plus the floodplain test, not on an accuracy figure.

## 3. Tent-block digitising — SAM vs classical (T1 2025-02-16)

**Set-up** (`10_scripts/sam_tents.py`, `sam_worker.py`): Segment Anything ViT-B (Meta, `sam_vit_b_01ec64.pth`, checksum verified) on the Sentinel-2 natural-colour image. 5 tiles of 2 × 2 km, each at least 20 % tent city. Per tile, **5 clicks inside and 5 outside tent blocks** (placed at random on eroded masks, fixed seed), imitating a GeoAI / Geo-SAM operator. Scored with IoU against the change-based tent blocks (Phase 10) and the Random Forest tent class (Phase 13). **Neither reference is ground truth.**

| Tile | Tent share (rule) | IoU SAM vs rule | IoU SAM vs RF | IoU rule vs RF | SAM score | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 42 % | 0.57 | 0.58 | 0.63 | 0.94 | 7.0 |
| 1 | 49 % | 0.69 | 0.67 | 0.69 | 0.90 | 7.1 |
| 2 | 22 % | 0.41 | 0.51 | 0.53 | 0.93 | 7.2 |
| 3 | 60 % | 0.73 | 0.66 | 0.84 | 0.97 | 7.3 |
| 4 | 34 % | 0.73 | 0.68 | 0.79 | 0.96 | 7.5 |
| **Mean** | | **0.63** | **0.62** | **0.70** | 0.94 | **7.2 (1.8 s/km²)** |

**Reading** (`09_docs/sam_tents.png`):
- SAM draws **smooth, continuous outlines that follow the river banks and sector edges**, cleaner than the ragged 10 m rule polygons. Its agreement with the classical layers (IoU 0.62–0.63) is close to how well the two classical layers agree with each other (0.70).
- **Weakness:** working only on optical colour, SAM includes **open sand between sectors** (tiles 0 and 1) — the same tent-vs-sand confusion the signatures showed (Phase 12). It cannot tell a temporary tent from a permanent roof without the SAR time series.
- **Practical workflow:** SAM for a fast first outline (≈ 7 s and 10 clicks per 4 km²), then clip it with the SAR change mask (ΔVV ≥ +1 dB) and fix the edges by hand.
- Outputs: `07_analysis/ai/sam_tents_T1.tif`, `sam_tents_T1.gpkg`. The GeoAI plugin GUI route is in the plugin booklet (Phase 11, item 15).

## 4. Not run, documented as future work

- **Foundation models** (TerraMind, Prithvi, Copernicus-FM): fine-tuning for tent-city segmentation from S1 + S2 needs a GPU and labelled tiles; the 200 sample polygons and the change layers here are a starting dataset.
- **SAR-to-optical translation** (diffusion models) for cloudy monsoon dates, and **deep SAR–optical matching** (AROSICS found 0 SAR–optical tie points in Phase 8).
- **MERLIN** despeckling needs SLC data (not downloaded).

## 5. Responsible use

- AI outputs are never used as reference data: all scores here compare AI with the classical layers, and both are labelled "not ground truth".
- Each model is recorded in the processing log with name, version, weights source and licence:
    - SAR2SAR: deepdespeckling 0.8, MIT.
    - OmniCloudMask: 1.8.0, weights from Hugging Face.
    - SAM ViT-B: segment-anything 1.0, Apache-2.0.
- Known domain gaps are reported rather than hidden: SAR2SAR on water, SAM's optical-only view, OmniCloudMask with no labelled reference.
- **Technical notes:**
    - PyTorch and the conda GDAL stack load different OpenMP runtimes, so every model runs in a separate worker process.
    - The SAR2SAR checkpoint needed one numpy type allow-listed for PyTorch's safe loader (`weights_only` kept on).
