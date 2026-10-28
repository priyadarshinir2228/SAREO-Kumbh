# Literature Survey — SAREO-Kumbh (Phase 1)

**Version:** 0.1 · 22 Oct 2026
**Status key:** ✔ = checked against the source page during Phase 1 · ○ = standard citation, still to be checked on Google Scholar / IEEE Xplore before the final report.

Each topic follows the same pattern: **classical → machine/deep learning → current state of the art (2024–26) → limitation → what this project does**. The matrix version is in `literature_matrix.csv`.

---

## 1. Kumbh Mela and mass temporary settlements (closest prior work)

| Work | Data | What it did | Limitation | Status |
| --- | --- | --- | --- | --- |
| Harvard GSD / Mittal Institute, *Kumbh Mela: Mapping the Ephemeral Mega-City* (2013 event, book 2015) | Aerial images, field mapping | Documented how the temporary city is planned and built; urban-design view | Planning study, no satellite time-series analysis | ✔ |
| ISRO / NRSC release on Maha Kumbh 2025 (Jan 2025) | EOS-04 (RISAT-1A) C-band SAR, FRS-1 mode, 2.25 m; dates 15 Sep 2023 and 29 Dec 2024 | Showed tent-city layout, roads, pontoon-bridge network, Shivalay Park construction | Image release only: no quantitative analysis, no published method or accuracy | ✔ |
| Spröhnle, Fuchs, Aravena Pelizari (2017), IEEE JSTARS 10(5) | WorldView-2 + TerraSAR-X | Object-based dwelling detection in refugee camps; fused optical + SAR | Single-pol SAR detected only metal-sheet dwellings; optical worked for all materials; VHR commercial data | ✔ |
| Braun, Fakhri, Hochschild (2019), *Remote Sensing* 11(17):2047 | 11 Sentinel-1 + ALOS-2 pairs, DEM | Radar-based monitoring of Kutupalong camp growth and forest loss; accuracies 88–95% | Land-cover level, not individual shelters; single camp | ✔ |
| Mask R-CNN dwelling extraction in IDP/refugee settlements (Univ. Salzburg) | WorldView-2/3 time series | Instance segmentation of individual dwellings | Commercial VHR optical only; cloud-dependent | ✔ (abstract) |
| Ahn et al. (2025, arXiv 2511.07231) | Sub-metre imagery, Cox's Bazar, multi-year | Semi-supervised shelter segmentation (F1 76.4%) and WASH-access analysis; people per facility 25 → 29.4 (2022–2025) | Sub-metre commercial data; optical only | ✔ |

**Takeaway:** the Kumbh tent city has been *shown* in SAR imagery (ISRO, 2025), and camps have been *mapped* with VHR optical deep learning or with Sentinel-1 land-cover classification. No published study quantifies a mass temporary settlement's full life cycle (empty → peak → cleared) with free Sentinel-1 + Sentinel-2 data and a reproducible GIS workflow.

> Correction to earlier notes: the Cox's Bazar 2025 paper uses a **semi-supervised segmentation model** (F1 76.4%), not SAM as stated in an earlier draft.

## 2. SAR fundamentals and Sentinel-1 preprocessing

- **Classical references:** *The SAR Handbook* (Flores-Anderson et al., SERVIR/NASA 2019) ○; Woodhouse, *Introduction to Microwave Remote Sensing* (2006) ○; NASA ARSET SAR training ○.
- **Preprocessing chain:** Filipponi (2019), "Sentinel-1 GRD preprocessing workflow", MDPI Proceedings ○ — orbit → thermal noise → border noise → calibration → speckle filter → terrain correction → dB. This is the chain in Implementation Guide B4.
- **Data availability (checked):** Sentinel-1B failed in Dec 2021. Sentinel-1C products were first released 30 Jan 2025, opened to users 26 Mar 2025, and **calibrated / operational from 19 May 2025** ✔. → For T0 and T1 (Oct 2024 – Feb 2025) only Sentinel-1A is usable; Sentinel-1C can help for T3 (Aug–Sep 2025).
- **What we do:** standard SNAP chain, one relative orbit across epochs, σ⁰ in dB.

## 3. Speckle filtering

| Stage | Methods | Key references | Status |
| --- | --- | --- | --- |
| Classical, local statistics | Lee (1980), Refined Lee (1981), Frost (1982), Kuan (1985), Gamma-MAP (Lopes 1990), Improved Lee Sigma (2009) | IEEE TPAMI / TGRS papers | ○ |
| Supervised CNN | SAR-CNN (Chierchia 2017), ID-CNN (Wang 2017) | trained on synthetic speckle | ○ |
| Self-supervised | **SAR2SAR** (Dalsasso, Denis, Tupin, IEEE JSTARS 2021, 14:4321–4329); **MERLIN** (Dalsasso et al.) | learn from real speckled data, no clean reference | ✔ |
| Sentinel-1 GRD specific | Gasnier, Dalsasso, Denis, Tupin (2021), SAR2SAR trained on Sentinel-1 GRD, improves narrow-river segmentation (arXiv 2102.00692) | ✔ |
| Transformer / diffusion (2024–25) | DDPM + Swin Transformer (Remote Sensing 2024, +0.93 dB PSNR); Efficient Conditional Diffusion (2025); TransSARNet (2025) | ✔ (abstracts) |
| Surveys | Fracastoro et al. (2020/21) deep despeckling survey; 2021 restoration-training review | ✔ |

- **Limitation:** deep models are trained mostly on synthetic speckle or specific sensors; diffusion models are slow; classical filters remain the operational default (SNAP).
- **Tool check (✔):** the `deepdespeckling` package (MIT licence; `conda install -c conda-forge gdal` then `pip install deepdespeckling`) provides **SAR2SAR for Sentinel-1 GRD amplitude GeoTIFFs** and **MERLIN for complex SLC** (Sentinel-TOPS, TerraSAR-X stripmap/spotlight).
- **What we do:** evaluate 9 classical filters + multi-temporal with ENL/SSI/SMPI/EPI, and add **SAR2SAR on our GRD data** as the AI row. MERLIN is optional, only if we download SLC.

## 4. Optical preprocessing and cloud masking

- **Classical:** DOS1 (Chavez 1996) ○; Sen2Cor / Sentinel-2 L2A SCL; Fmask; Landsat QA bits.
- **Machine learning:** s2cloudless (gradient boosting).
- **Deep learning:** CloudSEN12 dataset (Scientific Data 2022) ✔; CloudS2Mask (Wright et al., RSE 2024; up to 44× faster) ✔; **OmniCloudMask** (RSE 2025; sensor-agnostic, 10–50 m) ✔.
- **Limitation:** AI masks are heavier to run; benchmarks are mostly Sentinel-2.
- **What we do:** SCL mask as baseline, OmniCloudMask as AI comparison (on T0 or T3 where some cloud/haze exists).

## 5. Georeferencing and co-registration

- **Classical:** GCP polynomial / thin plate spline (QGIS Georeferencer); AROSICS (Scheffler et al., Remote Sensing 2017) ○; RIFT.
- **Deep learning:** XoFTR and other deep matchers; multi-expert state-space model (TGRS 2025) ✔; ACAMatch (Remote Sensing 2025) ✔.
- **Benchmark (✔):** the 2025 multi-resolution SAR–optical registration review (arXiv 2502.01002) reports classical **RIFT 66.5%** vs best deep method **XoFTR 40.6%** — deep learning does not yet win here.
- **What we do:** classical GCP + AROSICS with RMSE on independent check points; cite the benchmark to justify the classical choice.

## 6. SAR–optical fusion

- **Classical:** IHS, PCA, Brovey, wavelet (Pohl & van Genderen 1998) ○.
- **Deep learning reviews:** Cheng et al. 2022 (no unified fusion metric) ✔; Vivone et al. 2025 (IEEE, remote-sensing fusion) ✔; Optical–SAR fusion review (Remote Sensing, Dec 2025) ✔; Guo et al. (Remote Sensing 2026) ✔.
- **SAR-assisted cloud removal:** DSen2-CR (Meraner et al. 2020) ✔; UnCRtainTS (2023) ✔; AllClear benchmark (NeurIPS 2024) ✔.
- **SAR-to-optical translation:** GANs → conditional / Brownian-bridge / latent diffusion (2024–25) ✔; survey "Generative AI meets SAR" (2024) ✔.
- **What we do:** lossless classical fusion (stack, PCA, IHS/Brovey, multi-temporal RGB) with quality metrics; deep fusion and translation as future work.

## 7. Change detection

- **Classical:** log-ratio, coefficient of variation (arXiv 1904.11335) ✔, interferometric coherence change detection ○, Otsu thresholding.
- **Deep learning:** residual / Siamese U-Nets on Sentinel-1; foundation-model change heads.
- **Recent (✔):** UNU-INWEH Sentinel-1 damage assessment of the March 2025 Myanmar earthquake (over 157,000 buildings likely damaged); 2026 comparison of Siamese U-Nets vs Copernicus-FM for Sentinel-1 damage (foundation model generalises better, weaker on rare classes).
- **What we do:** log-ratio + Otsu to measure tent-city area per epoch; optional coherence.

## 8. Earth-observation foundation models

- SatMAE (2022) ○, Prithvi (IBM–NASA 2023) ○, CROMA (2023) ○, DOFA (2024) ○.
- **2025 (✔):** TerraMind (IBM/ESA, any-to-any S1↔S2 generation, outperforms CROMA/DOFA/Prithvi on PANGAEA); TerraFM (MBZUAI, 18.7M S1+S2 tiles); Copernicus-FM (dynamic hypernetworks, any sensor + metadata).
- **What we do:** future work — fine-tune for tent-city segmentation.

## 9. AI tools inside QGIS

- **Deepness** (2023): ONNX segmentation/detection/regression in QGIS ✔.
- **GeoAI plugin**: SAM 3, Moondream, forest and water segmentation; GPU ≥ 8 GB recommended, CPU works 10–20× slower ✔.
- **Geo-SAM** and SAM 2.1/3 plugins ✔.
- **What we do:** SAM-assisted digitising compared with manual (IoU, time).

---

## Gap statement

Mass temporary settlements have been **imaged** with SAR (ISRO's EOS-04 release of the Maha Kumbh 2025 tent city) and **mapped** with very-high-resolution commercial optical imagery and deep learning (refugee and IDP camps), or with Sentinel-1 at land-cover level (Kutupalong). **No published study measures the full life cycle of a mass temporary settlement — empty, peak and cleared — using only free Sentinel-1 SAR and Sentinel-2 optical data in a documented, reproducible open-source GIS workflow, nor tests where AI tools actually improve on the classical steps of that workflow.** SAREO-Kumbh addresses this gap on the largest temporary settlement in recent history.

## Remaining Phase 1 actions

- [ ] Check every ○ citation on Google Scholar / IEEE Xplore and add DOI.
- [ ] Search Google Scholar for "Kumbh" + "remote sensing", "Sentinel", "SAR" (2019–2026) and add any paper found to Section 1.
- [ ] Save PDFs of key papers into `09_docs/literature/`.

## Sources checked in Phase 1

- [Harvard GSD Kumbh Mela proposal](https://mittalsouthasiainstitute.harvard.edu/wp-content/uploads/2013/05/Kumbh-GSD-Proposal.pdf)
- [Tribune India: ISRO radar imaging satellite images of Maha Kumbh](https://www.tribuneindia.com/news/india/isros-radar-imaging-satellite-beams-images-of-maha-kumbh-from-space)
- [Business Standard: ISRO releases Maha Kumbh tent city images](https://www.business-standard.com/india-news/isro-releases-satellite-images-of-maha-kumbh-mela-tent-city-sangam-125012200984_1.html)
- [Spröhnle et al. 2017 (DLR eLib)](https://elib.dlr.de/111971)
- [Braun et al. 2019, Remote Sensing 11(17):2047](https://www.mdpi.com/2072-4292/11/17/2047)
- [Mask R-CNN dwellings in IDP/refugee settlements](https://uni-salzburg.elsevierpure.com/en/publications/mapping-of-dwellings-in-idprefugee-settlements-from-very-high-res/)
- [Ahn et al. 2025, Cox's Bazar WASH access (arXiv)](https://arxiv.org/abs/2511.07231v1)
- [Sentinel-1C products calibrated (Copernicus Data Space)](https://dataspace.copernicus.eu/node/2396)
- [Sentinel-1C user data opening](https://dataspace.copernicus.eu/node/2232)
- [deepdespeckling (GitHub)](https://github.com/hi-paris/deepdespeckling)
- [Gasnier et al. 2021, Despeckling Sentinel-1 GRD (arXiv)](https://arxiv.org/pdf/2102.00692)
- [SAR2SAR (arXiv 2006.15037)](https://arxiv.org/abs/2006.15037v1)
- Earlier-checked sources for Sections 3–9 are listed in the References section of the main project document.
