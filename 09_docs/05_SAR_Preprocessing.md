# SAR Preprocessing — SAREO-Kumbh (Phase 5, brief items 2.1 and 2.2)

**Date:** 23 Oct 2026 · **Data:** 5 × Sentinel-1A IW GRDH, relative orbit 92 descending · **Tools:** SNAP 14 `gpt`, Python (rasterio)

## 1. Processing chain (graph `09_docs/snap_graphs/S1_preproc_nofilter.xml`)

| # | Operator | Settings | Why |
| --- | --- | --- | --- |
| 1 | Apply-Orbit-File | Sentinel Precise (auto download) | Precise satellite position → accurate geocoding |
| 2 | ThermalNoiseRemoval | VH, VV | Removes sensor noise floor, important for low-backscatter VH, water, smooth sand |
| 3 | Remove-GRD-Border-Noise | limit 500, threshold 0.5 | Removes invalid low values at swath edges |
| 4 | Calibration | σ⁰, linear | Converts DN to physical backscatter coefficient |
| 5 | Subset | AOI WKT (WGS 84), metadata copied | Process only the AOI → 2 min per scene |
| 6 | Terrain-Correction | Copernicus 30 m DEM, 10 m, EPSG:32644, bilinear, `alignToStandardGrid` origin 5,5 | Geocodes to map; pixel edges on the 10 m grid shared with Sentinel-2 |
| 7 | Write + LinearToFromdB | GeoTIFF (linear) and GeoTIFF (dB) | Linear for statistics/filters, dB for display/differencing |
| 8 | `finalize_s1.py` | crop to AOI 582400–596600 E, 2807200–2821000 N; bands named; NoData = NaN; Float32 DEFLATE | Exact common grid, no resampling |

No speckle filter yet — Phase 6 compares filters on these unfiltered outputs.

Two problems found and fixed during the run:
1. Default terrain correction placed pixel corners 2.6 m / 7.3 m off the 10 m grid → enabled `alignToStandardGrid`.
2. SNAP aligns pixel **centres** to the origin, so origin 0,0 left edges 5 m off → origin set to 5,5. The crop script refuses any raster not on the grid, which caught both.

## 2. Outputs (`02_preproc/S1/`)

| Epoch | Date | Files | VV median (dB) | VH median (dB) |
| --- | --- | --- | --- | --- |
| T0 | 2024-11-12 | `S1A_20241112_Sig0_nofilter_lin.tif` / `_dB.tif` | −10.0 | −17.6 |
| T1a | 2025-01-23 | `S1A_20250123_…` | −9.8 | −17.1 |
| T1b | 2025-02-04 | `S1A_20250204_…` | −10.0 | −17.1 |
| T1 | 2025-02-16 | `S1A_20250216_…` | −10.3 | −17.2 |
| T2 | 2025-04-17 | `S1A_20250417_…` | −11.3 | −18.8 |

Every file: EPSG:32644 · 10.00 × 10.00 m · 1420 × 1380 px · origin on the 10 m grid · covers the full AOI · NoData 0.01% · bands `Sigma0_VH`, `Sigma0_VV`. Details: `s1_output_check.csv`.

## 3. Verification of spatial referencing (brief 2.1)

- **CRS, grid, extent:** all checks above pass for all five dates.
- **Alignment against OpenStreetMap:** median VV on OSM road bridges minus median VV inside OSM water areas = **+13.2 to +13.5 dB**. Shifting the image by 1, 2, 3 pixels lowers this contrast steadily (e.g. T1: 13.2 → 12.8 → 12.4 → 12.3 dB), so the SAR sits on the OSM features within about one pixel (10 m). VH shows the same, less sharply.
- **Integrity:** no gaps or striping inside the AOI; border noise is outside the AOI.

## 4. SAR image characteristics (brief 2.2) — see `s1_characteristics.png`

- **Backscatter intensity:**
    - River water: dark (VV ≈ −20 to −25 dB) — specular reflection away from the sensor.
    - Prayagraj city: bright (VV often > −5 dB) — double-bounce between walls and ground.
    - Tent city (T1): bright, regular grid on the floodplain that was dark/medium at T0.
    - **Pontoon bridges (T1 only): a "ladder" of very bright lines across the Ganga** — metal pontoons + water double-bounce. Absent at T0 and T2.
    - T2: floodplain darker than T0 (dry, smooth, cleared sand); VV histogram shifts about 1.3 dB lower, VH about 1.6 dB lower.
- **Speckle:** a profile across uniform sand varies by more than 10 dB pixel to pixel — the multiplicative speckle that Phase 6 filters will reduce (ENL of the raw data ≈ 4–5 for GRDH; to be measured in Phase 6).
- **Geometric distortion:** terrain is flat (Ganga–Yamuna plain), so layover and shadow are negligible; tall buildings and elevated bridge decks are displaced toward the sensor (east: Sentinel-1 is right-looking, so on a descending pass heading south it looks west). For a ~15 m high deck at 39° incidence the shift is h / tan θ ≈ 18 m — measured in Phase 8 as a +10 m east offset of bridges against OpenStreetMap. *(Corrected 23 Oct 2026: an earlier version gave the look direction the wrong way round.)*
- **Radiometric variation:** VV − VH is high (> 10 dB) over tents, city and bare sand (surface and double-bounce scattering) and low (< 6 dB) over vegetated fields (volume scattering) — the basis for separating tents from vegetation later.
- **VV vs VH:** VV shows structures and bridges more strongly; VH shows vegetation and the field pattern more strongly.

## 5. Files and how to view them

- QGIS: drag `08_layouts/S1_sigma0_nofilter.qlr` into the open project (or Layer → Add from Layer Definition File), move the group into **01_SAR**, then save the project.
- Scripts: `10_scripts/run_s1_preproc.ps1` (batch), `finalize_s1.py` (crop), `check_s1_outputs.py` (checks), `s1_characteristics.py` (panel), `make_s1_qlr.py` (layer file).
