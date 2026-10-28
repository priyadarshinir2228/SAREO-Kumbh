# Signature Reference Sheet — SAREO-Kumbh (Phase 12, brief item 12)

**Date:** 23 Oct 2026 · *Revised in Phase 13: the first "sand" samples (taken from the April sand-bar layer) contained ground that carried tents in February. Sand samples now exclude anything within 30 m of a tent block, and all values below were recomputed.*
**Data:** lossless SAR + EO stacks (Sentinel-1A σ⁰ Lee 7×7, Sentinel-2 L2A), T0 2024-11-12/13, T1 2025-02-16, T2 2025-04-17 · **Samples:** 200 polygons (40 per class) + 5 pontoon bridges; 119–15,805 pixels per class at T1

## Key findings

1. **Optically, tent blocks and bare sand are the same surface**: B04 / B08 / B11 = 0.23 / 0.29 / 0.35 (tents) vs 0.22 / 0.32 / 0.36 (sand). **SAR separates them**: VV −6.3 vs −15.8 dB, VH −16.7 vs −25.6 dB.
2. **On a single date, tents and permanent buildings look alike in SAR** (VV −6.3 vs −5.5 dB; JM 0.49 for VV + VH). **Time separates them**: tent ground goes **−12.4 → −6.3 → −14.3 dB** (T0 → T1 → T2), while buildings stay at −5.3 to −5.5 dB. Multi-temporal SAR raises JM to **1.74**.
3. **Pontoon bridges are the brightest class** (VV +0.8 dB at T1): metal pontoons plus double-bounce between deck and water.
4. **Fusing SAR and EO gives the best separability for every class pair** (JM 1.70–2.00). The hardest pair is tent vs sand (1.70).

## 1. Reference table, T1 2025-02-16 — median [25th, 75th percentile]

| Class | VV (dB) | VH (dB) | VV−VH (dB) | NDVI | MNDWI | NDBI | B04 red | B08 NIR | B11 SWIR | Scattering mechanism | Image appearance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Tent block** | **−6.3** [−9.6, −3.4] | −16.7 [−19.8, −14.8] | 10.8 | 0.10 | −0.29 | 0.11 | 0.23 | 0.29 | 0.35 | Corner reflection from tent walls + ground, metal frames and poles; dense regular rows | SAR: bright regular grid on the floodplain. S2: white/grey grid, same colour as sand |
| **Pontoon bridge** | **+0.8** [−1.9, +3.8] | −12.2 [−17.4, −9.3] | 11.9 | 0.04 | +0.08 | −0.11 | 0.09 | 0.10 | 0.08 | Double-bounce between metal pontoons / deck and water; layover pushes the deck toward the sensor (east) | SAR: very bright straight lines across dark water ("ladder"). S2: thin dark lines, shadow to the north |
| **Built-up (permanent)** | −5.5 [−7.2, −3.2] | −14.2 [−15.6, −12.7] | 8.3 | 0.12 | −0.28 | 0.08 | 0.14 | 0.18 | 0.22 | Double-bounce wall–ground; dihedral corners; some volume from trees | SAR: very bright, textured, with layover and shadow. S2: grey, mixed with trees |
| **Sand / bare floodplain** | −15.8 [−19.7, −12.8] | −25.6 [−29.9, −20.9] | 9.1 | 0.06 | −0.22 | 0.10 | 0.22 | 0.32 | 0.36 | Surface scattering; smooth dry sand → mostly forward-scattered (dark) | SAR: dark, smooth. S2: bright beige/white |
| **Vegetation (crops)** | −11.0 [−12.3, −9.7] | −16.9 [−18.3, −15.5] | **5.9** | **0.74** | −0.44 | −0.34 | 0.05 | 0.35 | 0.17 | Volume scattering in the canopy → relatively strong VH, low VV−VH | SAR: medium grey, uniform field texture. FCC: bright red |
| **Water (river)** | **−21.1** [−22.5, −19.3] | **−28.3** [−31.5, −26.0] | 8.0 | −0.07 | **+0.20** | 0.02 | 0.03 | 0.03 | 0.03 | Specular reflection away from the sensor | SAR: black (wind ripples brighten it). S2: dark green-brown, turbid |
| **Dugout** *(not in this AOI — from literature)* | dark core with a bright rim | — | — | low | negative | ≈ sand | — | — | — | Pit: radar shadow on the far wall and bright near rim; spoil heaps rougher than undisturbed ground; usually < 10 m, so needs sub-metre SAR or VHR optical | VHR: shadowed hole with spoil ring; craters and trenches mapped this way in VHR studies (e.g. eastern Ukraine, 0.5 m WorldView-2) |

Full statistics for every class, epoch and band: `09_docs/signatures_stats.csv`. Figures: `signatures_boxplots.png` (6 features × 3 epochs), `signatures_spectral.png` (S2 spectra + S1 backscatter), `signatures_trajectory.png` (T0 → T1 → T2).

## 2. Change signatures — the same ground at three dates (median)

| Ground | VV T0 → T1 → T2 (dB) | VH T0 → T1 → T2 (dB) | NDVI T0 → T1 → T2 | What happened |
| --- | --- | --- | --- | --- |
| Tent-city ground | −12.4 → **−6.3** → −14.3 | −22.4 → **−16.7** → −24.4 | 0.12 → 0.10 → 0.08 | Bare floodplain → tents (+6.1 dB) → cleared (−8.0 dB) |
| Pontoon-bridge lines | −3.7 → **+0.8** → −1.9 | −13.1 → −12.2 → −12.1 | — | Several bridges already in place in Nov and some still standing in Apr |
| Sand | −13.2 → −15.8 → −16.8 | −25.3 → −25.6 → −27.6 | 0.08 → 0.06 → 0.05 | Stable bare sand, drier and smoother over the dry season (−3.5 dB) |
| Vegetation | −10.1 → −11.0 → −12.5 | −17.9 → −16.9 → −20.7 | 0.32 → **0.74** → 0.21 | Rabi crop: green in Feb, harvested by Apr (VH −3.8 dB) |
| Built-up | −5.3 → −5.5 → −5.4 | −14.3 → −14.2 → −14.0 | 0.15 → 0.12 → 0.11 | Stable (±0.2 dB) — the reference that rules out calibration drift |
| Water (T1 channel) | −21.2 → −21.1 → −22.0 | −29.5 → −28.3 → −29.2 | — | Stays dark; MNDWI 0.48 → 0.20 → −0.16 as the channel narrows and becomes turbid |

## 3. Separability at T1 — Jeffries–Matusita distance (0 = identical, 2 = fully separable) — `signatures_separability.csv`

| Class pair | Best single feature | SAR T1 (VV, VH) | SAR multi-temporal (VV T0, T1, T2) | EO T1 (6 bands) | **Fused T1 (SAR + EO)** |
| --- | --- | --- | --- | --- | --- |
| tent vs sand | VV 0.86 | 0.93 | 1.08 | 1.41 | **1.70** |
| tent vs built-up | VH 0.39 | 0.49 | **1.74** | 1.77 | **1.81** |
| tent vs vegetation | NDVI 1.89 | 0.99 | 1.22 | 1.98 | **1.99** |
| tent vs water | MNDWI 1.52 | 1.60 | 1.63 | 1.93 | **1.98** |
| sand vs built-up | VV 1.32 | 1.52 | 1.79 | 1.84 | **1.99** |
| sand vs water | NDVI 0.55 | 0.31 | 0.63 | 1.75 | **1.78** |
| vegetation vs built-up | NDVI 1.80 | 1.25 | 1.36 | 1.95 | **1.97** |

**Reading:** no single feature separates tents from buildings, and SAR alone cannot separate dark sand from water. Fusion is best for every pair. Adding time to SAR solves tent vs buildings. Classification (Phase 13) confirms the order: fused + temporal is the most accurate input.

## 4. How backscatter varies with surface change (confirmed in this AOI)

| Surface change | Physical cause | Expected σ⁰ change | Measured here |
| --- | --- | --- | --- |
| Sand → tent city | Vertical walls + ground form corner reflectors; metal poles and frames | Strong increase | **+6.1 dB VV, +5.8 dB VH** (T0 → T1) |
| Tent city → cleared | Structures removed, smooth sand returns | Decrease to the old level | **−8.0 dB VV** (T1 → T2) |
| Water → pontoon bridge | Metal deck + water double-bounce | Very strong increase along a line | **≈ +22 dB** above the river (+0.8 vs −21.1 dB) |
| Bare → green crop | Canopy volume scattering | VH increases, VV−VH falls | VH −17.9 → −16.9 dB; VV−VH 7.8 → 5.9 dB |
| Green crop → harvested / dry | Canopy gone, soil drier and smoother | VH decreases | VH −16.9 → −20.7 dB |
| Wet → dry sand | Lower dielectric constant + smoother | Decrease | Sand −13.2 → −16.8 dB (Nov → Apr) |
| Calm → windy water | Small waves roughen the surface above the Rayleigh limit (≈ 0.9 cm for C-band at 39°) | Increase | Local bright streaks on the river (not measured per date) |
| Land → flooded open land | Specular reflection | Strong decrease | Not in T0–T2 (monsoon T3 optional) |
| Permanent buildings | No change | Stable | ±0.2 dB across 5 months (calibration check) |

## 5. SAR processing methods used for this content

| Purpose | Method | Where |
| --- | --- | --- |
| Radiometric quantities | Calibration to σ⁰; dB conversion; thermal and border noise removal | Phase 5 |
| Speckle | Lee 7×7 (ENL 4.4) single date; Quegan multi-temporal for change; SAR2SAR tested | Phase 6 |
| Geometry | Range-Doppler terrain correction on the Copernicus 30 m DEM, aligned 10 m grid; layover awareness for bridges | Phases 5, 8 |
| Change detection | Log-ratio ΔVV = VV_T1 − VV_T0 (dB); Otsu (+2.0 / −3.5 dB) and fixed (+3 / −2 dB) thresholds; multi-temporal RGB | Phases 9, 13 |
| Polarimetric cue | Cross-pol ratio VV−VH: low (≈ 6 dB) = volume (vegetation), high (≈ 9–12 dB) = surface/double-bounce | this sheet |
| Fusion | Lossless SAR + EO stack for statistics and classification; HPF injection for visual products | Phase 9 |
| Separability | Jeffries–Matusita on Gaussian class models | this sheet |

## 6. Limits of these signatures

- 10 m pixels mix tents with lanes and sand, so the tent class is a **tent-block** signature, not a single-tent one (single tents need sub-metre SAR).
- Samples come from the rule-based layers (Phase 10). They are consistent with the imagery but not ground-truthed, and the "tent_block" sample cannot be fully independent of the rules that drew it.
- Dugouts are not present in the AOI; their row is from literature and physics.

Script: `10_scripts/signatures.py`.
