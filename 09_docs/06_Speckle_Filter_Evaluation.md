# Speckle Filter Evaluation — SAREO-Kumbh (Phase 6, brief items 2.3 and 10)

**Date:** 23 Oct 2026 · **Scene:** Sentinel-1A IW GRDH, 2025-02-16 (T1, peak tent city), relative orbit 92 descending

## Decision

**Lee 7×7 (ENL 4.4) is the speckle filter for the main SAR chain.** It has the best overall score: VV ENL 5.2 → 22.3, VH ENL 3.8 → 13.0, mean preserved (MR 0.998, i.e. no radiometric bias), edge preservation EPI 0.85 and point-target preservation 0.83, in about 2 minutes per scene with a standard SNAP operator. The **multi-temporal Quegan filter** is kept for change detection (best detail preservation), and **SAR2SAR** is reported as the AI comparison.

## 1. Method

All filters were applied to the **same input** — a calibrated σ⁰ (linear) AOI subset in radar geometry (`09_docs/snap_graphs/S1_cal_subset.xml`) — and every result went through the **same terrain correction** (`S1_filter_tc.xml`, identical to Phase 5) and crop, so all 26 outputs share one 10 m grid and are compared pixel for pixel.

| Group | Configurations | Tool |
| --- | --- | --- |
| Non-adaptive | Boxcar 3/5/7, Median 3/5/7 | SNAP 14 Speckle-Filter |
| Adaptive local statistics | Lee 3/5/7, Frost 3/5/7 (damping 2), Gamma-MAP 3/5/7 (ENL 4.4) | SNAP 14 |
| Adaptive, edge / neighbourhood | Refined Lee, Lee Sigma 7×7 and 9×9 (σ 0.9, 4 looks), IDAN (50) | SNAP 14 |
| Log-domain / variational | MuLoG | SNAP 14 |
| Kuan | Kuan 3/5/7 (4 looks) — written back into the radar-geometry product, then the same TC | OTB 9.1.1 Despeckle |
| Multi-temporal | Quegan & Yu, 3 T1 dates (23 Jan, 4 Feb, 16 Feb), 5×5 local means | Python (on terrain-corrected Phase 5 rasters) |
| Deep learning | SAR2SAR (self-supervised, Sentinel-1 GRD weights) on amplitude = 500·√σ⁰, written back, same TC | deepdespeckling 0.8, CPU |

**Sample areas were chosen objectively** from a 3-date T1 average — never from a filter output — and saved in `06_vectors/filter_samples.gpkg`: 25 homogeneous land blocks + 10 calm-water blocks (21×21 px, lowest coefficient of variation), 97,619 edge pixels (top 5% Sobel gradient) and 6,231 point targets (3×3 local maxima > 0 dB VV: bridges, metal, buildings).

**Metrics** (formulas in Part C of the main document): ENL, SSI, mean ratio MR, SMPI on homogeneous blocks; EPI on edge pixels (amplitude); PTP = median(filtered/original) on point targets. Overall score = sum of VV ranks for ENL (high), EPI (high), |PTP−1| (low) and |MR−1| (low).

## 2. Results (top 10 of 25; full table `filter_comparison.md`, raw values `filter_metrics.csv`)

| Rank | Filter | Window | VV ENL | VV EPI | VV PTP | VV MR | VH ENL | Runtime (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| – | Unfiltered | – | 5.17 | 1.00 | 1.00 | 1.00 | 3.76 | – |
| 1 | **Lee** | 7×7 | 22.28 | 0.85 | 0.83 | 1.00 | 13.03 | 118 |
| 2 | Gamma-MAP | 7×7 | 22.06 | 0.99 | 1.00 | 0.98 | 10.22 | 117 |
| 3 | SAR2SAR | – | 25.99 | 0.93 | 0.94 | 0.97 | 7.78 | 371 |
| 4 | Frost | 7×7 | 23.64 | 0.84 | 0.70 | 1.00 | 15.80 | 90 |
| 5 | Gamma-MAP | 5×5 | 15.10 | 0.97 | 1.00 | 0.98 | 8.34 | 143 |
| 6 | Kuan (OTB) | 7×7 | 26.35 | 0.70 | 0.72 | 1.00 | 15.77 | 312 |
| 7 | Lee Sigma | 7×7 | 17.15 | 0.87 | 0.75 | 0.98 | 11.10 | 122 |
| 8 | Multi-temporal | 3 dates | 9.81 | 0.96 | 1.01 | 0.99 | 6.74 | 1 |
| 9 | Lee Sigma | 9×9 | 22.08 | 0.86 | 0.75 | 0.98 | 13.35 | 121 |
| 10 | Lee | 5×5 | 15.44 | 0.85 | 0.78 | 0.99 | 9.68 | 119 |

Lowest ranks: Median (EPI 0.19–0.71, mean bias up to −7%), MuLoG, Refined Lee and IDAN (IDAN darkens by 10%, MR 0.90).

## 3. Findings

1. **Window size is the main trade-off.** For every filter family, ENL roughly doubles from 3×3 to 7×7; non-adaptive filters pay for it in edges (Boxcar 7×7 EPI 0.22, Median 7×7 0.19), adaptive filters do not (Lee EPI ≈ 0.85 at every size).
2. **Gamma-MAP's near-perfect EPI and PTP are misleading.** Its ratio image (original ÷ filtered, `filter_finalists.png`) is flat across much of the tent city: Gamma-MAP leaves high-variance pixels untouched, so heterogeneous areas — exactly the tent blocks — stay speckled. It is rejected for this AOI despite rank 2.
3. **Lee and Frost 7×7 soften the pontoon bridges slightly** (the bridge line is faintly visible in their ratio images, correlation of log-ratio with the reference +0.27–0.28); Lee keeps more point-target energy (PTP 0.83 vs 0.70).
4. **SAR2SAR (AI) gives the best VV edge/point balance** (ENL 26, EPI 0.93, PTP 0.94) but: (a) VH smoothing is weak (ENL 7.8 vs 13.0 for Lee), (b) a −2.6% mean bias, (c) on calm water it *adds* variance (water ENL 0.78, below the unfiltered 3.64) — very dark, thermal-noise-corrected water is outside its training range, (d) 3× slower on CPU.
5. **Multi-temporal filtering removes almost no structure** (log-ratio correlation +0.03, PTP 1.01, EPI 0.96) but only reaches ENL 9.8 with three dates — ideal where detail matters more than smoothness, e.g. change detection.

## 4. Problem found and fixed

The first run used SNAP's default ENL = 1 for Lee, Gamma-MAP and Lee Sigma. Sentinel-1 IW GRDH has ENL ≈ 4.4, so the filters assumed four times too much noise and **Lee and Gamma-MAP collapsed into a boxcar** (identical metrics to three decimals). Caught by comparing outputs pixel-wise; all ENL-dependent filters were re-run with ENL 4.4 / 4 looks (Lee and Gamma-MAP now differ from Boxcar at 79% of pixels). Run times in the table are from the clean runs; Frost 3×3 (2,870 s) was slowed by the PC sleeping and is not representative (Frost 5×5 / 7×7 took 90–96 s).

## 5. Outputs

| File | Content |
| --- | --- |
| `03_enhanced/S1_filters/T1_<filter>_lin.tif` | 26 filtered T1 rasters (σ⁰ linear, VH + VV, AOI grid) |
| `09_docs/filter_comparison.md`, `filter_metrics.csv` | full metric table, all 25 filters |
| `09_docs/filter_panel.png` | 13 filter families, 3 × 3 km at the Sangam + VV profile |
| `09_docs/filter_finalists.png` | top 5 at 1.5 × 1.5 km + ratio images |
| `06_vectors/filter_samples.gpkg` | homogeneous blocks used for ENL / SSI / MR / SMPI |
| `09_docs/snap_graphs/S1_preproc.xml` | **final chain with Lee 7×7** |
| `02_preproc/S1/S1A_<date>_Sig0_lee7_lin.tif` / `_dB.tif` | all 5 dates with the chosen filter |

Scripts: `run_filters.ps1`, `run_filters_extra.py`, `filter_metrics.py`, `filter_panel.py`, `filter_finalists.py`.
