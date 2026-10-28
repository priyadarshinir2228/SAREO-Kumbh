# SAR–EO Fusion without Loss — SAREO-Kumbh (Phase 9, brief item 11)

**Date:** 23 Oct 2026 · **Inputs:** Sentinel-1 σ⁰ (Lee 7×7, dB) and Sentinel-2 L2A reflectance, same-day pairs on 16 Feb (T1) and 17 Apr (T2), T0 one day apart (12/13 Nov 2024)

## Summary

**The lossless SAR + EO layer stack is the main fusion product**: every band is bit-identical to its source, at the original 10 m, with names and source tags kept. Of the pixel-level fusions, **high-pass (HPF) injection is the only one that keeps the optical spectrum** (mean correlation 0.895, ERGAS 24.6) while adding SAR detail (spatial correlation with SAR 0.83). PCA, IHS and Brovey replace the optical brightness with SAR backscatter, which is physically unrelated, and destroy the spectra (correlation 0.07–0.29, ERGAS 61–77).

## 1. How "without loss" is guaranteed

| Risk of loss | What was done |
| --- | --- |
| Resolution | All layers already share one 10 m EPSG:32644 grid (Phase 5 alignment, Phase 7 crop, Phase 8 checks < 0.5 px) → **no resampling at all** |
| Values | Float32 kept (no conversion to 8-bit or integer); **DEFLATE lossless compression** (never JPEG) |
| NoData | NaN preserved in every band |
| Attributes | Every band named (`VV_dB`, `VH_dB`, `VVminusVH_dB`, `B02`…`B12`, `NDVI`, `MNDWI`); file tags record the S1 and S2 source files |
| Display | 8-bit copies only for maps (multi-temporal RGB display file); analysis always uses the Float32 files |
| **Test** | Each stack re-read and compared with its sources: **all 11 bands bit-identical, same grid** (T0, T1, T2) |

## 2. Products (`05_fused/`)

| File | Content |
| --- | --- |
| `fused_stack_T0_20241113.tif`, `_T1_20250216.tif`, `_T2_20250417.tif` | 11-band lossless SAR + EO stacks (the input for signatures and classification) |
| `fusion_PCA_T1_20250216.tif` | PCA component substitution (6 optical bands) |
| `fusion_IHS_T1_20250216.tif` | Fast additive IHS (natural colour) |
| `fusion_Brovey_T1_20250216.tif` | Brovey ratio (natural colour) |
| `fusion_HPF_T1_20250216.tif` | High-pass SAR detail injection (6 optical bands) |
| `mtRGB_VV_R-T1_G-T0_B-T2.vrt` / `_display.tif` | Multi-temporal SAR RGB: R = VV T1, G = VV T0, B = VV T2 (lossless VRT + 8-bit −25…0 dB display) |

## 3. Methods (formulas in Part C, C10, of the main document)

- **PCA:** standardise B02 B03 B04 B08 B11 B12 → eigen-decomposition (PC1 explains 79.1 % of variance, PC2 15.9 %, PC3 4.2 %) → replace PC1 with SAR VV dB matched to PC1's mean and standard deviation (sign aligned) → inverse PCA.
- **IHS (fast additive):** I = (B04 + B03 + B02)/3; S′ = VV dB matched to I; Fₖ = Bₖ + (S′ − I).
- **Brovey:** Fₖ = Bₖ · S″ / I with S″ = linear VV matched to I.
- **HPF injection:** HP = VV dB − 5×5 mean; Fₖ = Bₖ + 0.5 · σ(Bₖ)/σ(HP) · HP — only SAR's fine spatial detail is added.

## 4. Quality (T1, all valid pixels; `09_docs/fusion_quality.csv`)

| Method | Mean CC with original bands | ERGAS | SAM (°) | sCC with SAR (original S2: ≈ 0.01) |
| --- | --- | --- | --- | --- |
| Layer stack | 1.000 (bit-identical) | 0 | 0 | — (SAR kept as its own bands) |
| **HPF injection** | **0.895** | **24.6** | **3.8** | **0.83** |
| PCA | 0.287 (B08 0.89, others 0.12–0.21) | 60.9 | 13.2 | 0.63 |
| IHS | 0.114 | 76.5 | 13.7 | 0.85 |
| Brovey | 0.073 | 75.4 | 0.00 | 0.23 |

CC = correlation coefficient (spectral fidelity, 1 = perfect); ERGAS = relative global error (lower is better; < 3 is excellent for pansharpening); SAM = spectral angle mapper (0 = spectral shape unchanged); sCC = correlation of the fused image's high-pass detail with SAR's (how much SAR structure was injected).

**Reading:**
1. Classic pansharpening methods assume the "sharp" image looks like the optical brightness. SAR backscatter does not (double-bounce makes the city bright, specular reflection makes smooth sand dark), so PCA, IHS and Brovey **replace** content instead of sharpening it.
2. Brovey's SAM of exactly 0° is not an error: it multiplies all three bands by the same factor at each pixel, so the spectral angle cannot change — yet its radiometry collapses (ERGAS 75, histogram squeezed around 0.13).
3. HPF keeps the spectrum and still carries the pontoon bridges and tent-block edges from SAR — the only pixel fusion suitable for visual interpretation here.
4. For quantitative work (signatures, classification, change detection) the **stack** is used, because it loses nothing and lets each sensor contribute its own measurement.

## 5. Visual comparison — `09_docs/fusion_panel.png`

3 × 3 km at the Sangam on T1: S2 natural colour, S1 VV, the stack composite (R = VV, G = NDVI, B = MNDWI: tents and city red, vegetation green, water blue), the four pixel fusions, the multi-temporal SAR RGB (**tent city and pontoon bridges red/orange = bright only at T1**; stable city white; water dark), and B04 histograms (HPF and PCA close to the original, Brovey squeezed).

## 6. Files

- QGIS: drag `08_layouts/Fusion_products.qlr` into the project (multi-temporal RGB visible; HPF and the three stacks with RGB = VV/NDVI/MNDWI), move into **03_Fused**, save.
- Scripts: `10_scripts/fusion.py` (products + quality), `fusion_panel.py`, `make_fusion_qlr.py`.
