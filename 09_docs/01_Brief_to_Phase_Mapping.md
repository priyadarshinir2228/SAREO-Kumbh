# Brief-to-Phase Mapping — SAREO-Kumbh

Every item in the assessment brief (QGIS RASTER.pdf) and where it is delivered.

| Brief item | Requirement (summary) | Phase | Evidence in submission |
| --- | --- | --- | --- |
| 1 | Acquire imagery from authorised, publicly accessible portals | 4 | Download log, sources table |
| 2.1 | Import SAR into QGIS; verify spatial referencing and integrity | 5 | CRS/extent/NoData checks, alignment screenshots |
| 2.2 | Examine backscatter, speckle, geometric distortion, radiometric variation | 5 | Annotated characteristics panel |
| 2.3 | Evaluate speckle filters: noise suppression vs boundary/small-feature preservation | 6 | Filter comparison table (ENL, SSI, SMPI, EPI) + panels |
| 3.1 | EO preprocessing: correction, cloud/shadow mask, clip, stack, resample, reproject | 7 | Processing log, clean stacks |
| 3.2 | Enhancement: linear stretch, histogram equalisation, gamma, natural/false-colour composites | 7 | Before/after panels, composites |
| 4.1 | Attribute tables: identifiers, classes, dates, sources, descriptions | 10 | `kumbh_features.gpkg` schema |
| 4.2 | Validation: missing attributes, duplicates, invalid geometries, spatial inconsistencies | 10 | Validation report |
| 4.3 | Correct CRS assignment and transformations | 5, 7, 10 | CRS table in report |
| 4.4 | Standard naming, symbology, project organisation | 2, 10 | README conventions, `.qml` styles, layer groups |
| 4.5 | Data provenance and record of all steps | all | `processing_log.csv`, `download_log.csv`, SNAP XML, `.model3` |
| 4.6 | Export GeoTIFF, CSV etc. | 10, 15 | `07_analysis/exports` |
| 4.7 | Project reopens with all layers and outputs | 15 | Reopen test on second PC |
| 5 | Open sources for SAR and EO imagery | 4 | Sources table |
| 6 | Precise georeferencing, image-to-image co-registration, geometric accuracy | 8 | RMSE table, residual map |
| 8 | QGIS plugins with a demonstration of each | 11 | Plugin booklet |
| 9 | Merge shapefiles with the same attributes; transfer to another project/document | 10 | Merge demo, `.qlr` / Package Layers |
| 10 | Filters for enhancing SAR, with demonstration of each | 6 | Filter panels + metrics |
| 11 | Fuse EO and SAR without loss of resolution or attributes | 9 | Fused rasters + quality table |
| 12 | Signature reference sheet (building, tent, dugout, road, water…); backscatter vs surface change; SAR methods | 12, 13 | Signature sheet, change maps |

Phases 0, 1, 14 and 16 (charter, literature, AI comparisons, interview prep) support the brief but are not graded items on their own.
