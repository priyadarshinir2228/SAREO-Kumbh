# Vector Feature Database — SAREO-Kumbh (Phase 10, brief items 4.1–4.6 and 9)

**Date:** 23 Oct 2026 · **Database:** `06_vectors/kumbh_features.gpkg` (EPSG:32644)

## Summary

A validated 9-layer feature database with one common attribute schema, standard styles and drop-down attribute rules stored inside the GeoPackage. The **tent city at T1 covers 12.3 km² in 51 blocks**. Features were drafted with documented SAR + EO rules and are traceable through `method` and `confidence`. The shapefile-merge demonstration harmonised four different schemas with no loss of features or area. Validation found **0 invalid geometries, 0 NULLs in required fields, 0 tent-block overlaps**, and 4 duplicate OSM building footprints, which were removed.

## 1. Schema (brief 4.1)

| Field | Type | Content |
| --- | --- | --- |
| `id` | text | unique, prefix + epoch + number, e.g. `TB-T1-0007` |
| `class` | text (Value Map) | tent_block · temp_road · pontoon_bridge · water · sand_bar · permanent_building · veg_field · dugout |
| `sub_class` | text | e.g. "tent sector (block level)", OSM building / road type |
| `epoch` | text | T0 / T1 / T2 / static |
| `date` | text, ISO | acquisition date of the evidence |
| `sensor` | text | S1A + S2, S1A, S2, OSM |
| `source_ref` | text | exact files or source used |
| `method` | text | the rule or tool that produced the feature |
| `confidence` | text (Value Map) | high / medium / low |
| `area_m2` / `length_m` | real | computed from the geometry in EPSG:32644 |
| `remarks` | text | free notes, e.g. bridge also visible at T0/T2 |

Pontoon bridges also carry `present_T0` / `present_T2`.

## 2. Layers (draft extraction rules from the lossless stacks, `10_scripts/extract_features.py`)

| Layer | Features | Total | Rule / source | Confidence |
| --- | --- | --- | --- | --- |
| `tent_blocks` | 51 | 12.27 km² | ΔVV (T1 − T0) ≥ +3 dB **and** ΔVV (T2 − T1) ≤ −2 dB (appears, then disappears), NDVI_T0 < 0.3, not water | medium |
| `pontoon_bridges` | 5 | 1.2 km | VV_T1 > −6 dB in the river channel, elongated (L/W ≥ 4, ≥ 80 m), ≥ 40 % of the line over T1 water | medium |
| `river_T0` / `_T1` / `_T2` | 17 / 19 / 71 | 15.1 / 11.6 / 7.9 km² | MNDWI > 0 **or** (VV < −18 dB and MNDWI > −0.25) | high |
| `sand_bars` | 66 | 19.0 km² | T2: NDVI < 0.15, MNDWI < 0, VV < −14 dB, within the floodplain | medium |
| `veg_fields` | 277 | 48.3 km² | NDVI_T1 > 0.45 | high |
| `temp_roads` | 165 | — | OSM roads clipped to the tent blocks | low (today's OSM, not the 2025 lanes) |
| `permanent_buildings` | 65,499 | — | OSM footprints outside the tent city | medium |

Cleaning: opening/closing, minimum areas (0.5–2 ha), polygonise, simplify 10 m. Figure: `09_docs/features_overview.png`.

**Problems found while drafting:**
1. The first water rule (VV < −18 dB **and** MNDWI) missed the 150–250 m wide Ganga channel under the dense pontoon bridges, where Lee 7×7 VV stays at −9…−17 dB. Clear optical water (MNDWI > 0) is now accepted on its own.
2. "Bridge absent at T0 and T2" was wrong: several pontoon bridges already stood on 12 Nov 2024 and some still stood on 17 Apr 2025. Presence is now an attribute, not a filter.
3. The T0 water mask included floodplain flooded in November but dry in February, so tent rows were taken for bridges. A bridge must now lie at least 40 % over T1 water.

**Known limitation:** only 5 of the roughly 30 pontoon bridges reported for the whole Mela are extracted. At 10 m, closely spaced 1–2 px bridges merge or blur, and detecting on unfiltered data made it worse (3 bridges). The remaining bridges, temporary roads and any dugouts should be **digitised by hand** in QGIS on the T1 SAR + S2 images, with `method = manual digitising` and `confidence` set accordingly.

## 3. Organisation and styles (brief 4.4)

- Standard colours per class (tents red, bridges yellow, water blue, sand amber, vegetation green, buildings grey, roads white), **stored as default styles in the GeoPackage** (`layer_styles` table) → identical look in every project.
- `class` and `confidence` have a **Value Map drop-down**, so typing errors are impossible during manual digitising; field aliases are set.
- `08_layouts/Kumbh_features.qlr` loads the whole group (bridges, roads, tents and T1 water visible) — move it into **04_Vectors**.

## 4. Shapefile merge and transfer (brief item 9) — `10_scripts/merge_demo.py`, `06_vectors/merge_demo/`

| Sector shapefile | Features | Schema (as if digitised by different people) |
| --- | --- | --- |
| `tents_sector_NW.shp` | 26 | project schema |
| `tents_sector_NE.shp` | 12 | `Class`, `Area`, `Conf` |
| `tents_sector_SW.shp` | 8 | `CLASS`, `AREA_HA` (hectares) |
| `tents_sector_SE.shp` | 5 | project schema |

1. **Refactor fields** (`native:refactorfields`) maps each sector onto one schema, e.g. `AREA_HA * 10000 → area_m2`, `Conf → confidence`.
2. **Merge vector layers** (`native:mergevectorlayers`) → `tents_merged_qgis.gpkg`, 51 features, plus automatic `layer` and `path` fields recording each feature's source file.
3. **Dissolve by class** (`native:dissolve`) → `tents_dissolved_by_class.gpkg`, 1 feature.
4. Same merge with **ogr2ogr `-append -update`** and an SQL field mapping per sector → `tents_merged_ogr2ogr.gpkg`, 51 features.
5. **Check:** area 12.275 km² original = merged (attribute and geometry) = ogr2ogr = dissolved; 0 NULL classes; ids unique.
6. **Transfer to another project or document:** `native:package` → `tents_transfer_package.gpkg` (merged + dissolved + bridges, **styles included**); `.qlr` layer definition files; and for documents, the Print Layout (Phase 15).

## 5. Validation (brief 4.2, 4.3) — `10_scripts/validate_features.py`, `09_docs/validation_report.csv`

| Check | Result |
| --- | --- |
| CRS of every layer | EPSG:32644 |
| Invalid geometries (QGIS `native:checkvalidity`, GEOS) | 0 in all 9 layers |
| Duplicate geometries (`native:deleteduplicategeometries`) | 4 in `permanent_buildings` (OSM) → **removed**; 0 elsewhere |
| NULLs in id, class, epoch, sensor, method, confidence | 0 |
| Unique ids | yes, all layers |
| Tent blocks overlapping each other | 0 m² |
| Tent blocks on T1 water | 7,130 m² = 0.06 % of tent area (edge pixels) |
| Bridges crossing T1 water | 50–96 % of each line over water |
| Permanent buildings inside tent blocks | 0 |
| Road dangles | 355 of 390 ends — expected, roads are clipped at tent-block edges |

## 6. Exports (brief 4.6) — `07_analysis/exports/vectors/`, `09_docs/export_manifest.csv`

Every layer as **Shapefile** (`shp/`, EPSG:32644; all field names ≤ 10 characters so nothing is truncated), **GeoJSON** (`geojson/`, WGS 84) and **CSV with WKT geometry** (`csv/`). Re-reading each Shapefile gives the same feature count and field list as the GeoPackage. GeoTIFF exports of the rasters are already in `02_preproc`, `03_enhanced` and `05_fused`; the final export set is assembled in Phase 15.
