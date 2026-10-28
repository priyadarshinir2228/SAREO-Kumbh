# Data Selection — SAREO-Kumbh (Phase 4)

**Date:** 22 Oct 2026 · **AOI:** UTM 44N 582400–596600 E, 2807200–2821000 N (14.2 × 13.8 km = 196 km²)

## 1. How scenes were found

1. `10_scripts/search_scenes.py` queried the **Copernicus Data Space Ecosystem** OData catalogue (public, no login) with the AOI polygon for each epoch window → 84 products in `scene_candidates.csv`.
2. `10_scripts/preview_s2.py` read only the AOI window (20 m) of every cloud-free Sentinel-2 L2A date from the open Earth Search COGs on AWS → `s2_previews_T0.png`, `_T1.png`, `_T2.png`.
3. A wider T1 window (`s2_extent_check_T1.png`) showed east-bank Mela sectors reaching the AOI's north edge → **north edge raised from 2819600 to 2821000 m** (25.504° N).

## 2. What the previews show

| Epoch | Dates checked | Observation | Choice |
| --- | --- | --- | --- |
| T0 | 19 Oct – 8 Dec 2024 | 19 Oct: floodplain still flooded. Nov: water recedes, sand exposed, little structure. 8 Dec: road lines appearing (setup underway) | **mid-Nov 2024** |
| T1 | 22 Jan – 21 Feb 2025 | Tent-city grid clear on both Ganga banks and south of the Yamuna on every date | **16 Feb 2025** (same-day S1 + S2) |
| T2 | 28 Mar – 24 Apr 2025 | 28 Mar: faint remains; mid/late Apr: cleared sand | **17 Apr 2025** (same-day S1 + S2) |
| T3 | Aug – Sep 2025 | Only one S2 date under 20% tile cloud (24 Sep, 13.9%) | optional |

## 3. Sentinel-1 orbit decision

Both Sentinel-1A tracks cover the AOI every 12 days: **relative orbit 56 ascending** (~12:50 UTC) and **relative orbit 92 descending** (~00:28 UTC). Sentinel-1C is not usable for T0–T2 (calibrated only from 19 May 2025).

**Chosen: relative orbit 92, descending**, because its dates fall on or one day from clear Sentinel-2 dates (12 Nov / 13 Nov, 16 Feb / 16 Feb, 17 Apr / 17 Apr) — ideal for SAR–EO fusion and signature comparison. One orbit for all epochs keeps viewing geometry identical, which change detection needs.

## 4. Selected products (full list with IDs: `download_manifest.csv`)

| Priority | Epoch | Product | Date | Purpose | Size |
| --- | --- | --- | --- | --- | --- |
| core | T0 | S1A IW GRDH, orbit 92 | 2024-11-12 | baseline SAR | 1.7 GB |
| core | T1 | S1A IW GRDH, orbit 92 | 2025-01-23 | multi-temporal filter stack | 1.7 GB |
| core | T1 | S1A IW GRDH, orbit 92 | 2025-02-04 | multi-temporal filter stack | 1.7 GB |
| core | T1 | S1A IW GRDH, orbit 92 | 2025-02-16 | **main peak scene** | 1.7 GB |
| core | T2 | S1A IW GRDH, orbit 92 | 2025-04-17 | after clearing | 1.7 GB |
| core | T0 | S2A L2A, tile 44RNP | 2024-11-13 | baseline optical (cloud 0.01%) | 1.3 GB |
| core | T1 | S2B L2A, tile 44RNP | 2025-02-16 | peak optical (cloud 0.0%) | 1.3 GB |
| core | T2 | S2B L2A, tile 44RNP | 2025-04-17 | after optical (cloud 0.0%) | 1.3 GB |
| optional | T3 | S1A IW GRDH, orbit 92 | 2025-08-15 | monsoon flooding | 1.7 GB |
| optional | T3 | S2B L2A, tile 44RNP | 2025-09-24 | monsoon optical; cloud test for OmniCloudMask | 1.2 GB |
| optional | T0 | S1A IW SLC × 2 | 2024-11-12, 2024-11-24 | coherence pair before construction | 15.4 GB |
| optional | T1 | S1A IW SLC × 2 | 2025-02-04, 2025-02-16 | coherence pair during Mela | 15.4 GB |

**Core total ≈ 12.4 GB; with all optional ≈ 46 GB** (D: has about 180 GB free). All products were online at the time of search. Sentinel-2 processing baseline 05.11 → reflectance = (DN − 1000) / 10000.

## 5. How to download

The Copernicus download needs **your** free account (register at https://dataspace.copernicus.eu). Either:

- **Script (recommended):** run in your own terminal — it asks for your login, keeps nothing, skips finished files, and appends each file to `download_log.csv`:

```
. D:\SAREO-Kumbh\10_scripts\sareo_env.ps1
& $env:SAREO_PY D:\SAREO-Kumbh\10_scripts\download_cdse.py
```

  Add `--all` to include the optional products.
- **Browser:** Copernicus Browser → upload `06_vectors/AOI_Kumbh_4326.geojson` → search each product name from the manifest → download the .zip into `01_raw/S1` or `01_raw/S2`.

## 6. Open data sources (brief item 5)

| Portal | Operator | Data | Access | Used here |
| --- | --- | --- | --- | --- |
| Copernicus Data Space Ecosystem | ESA / European Commission | Sentinel-1, Sentinel-2, Copernicus DEM | free account | **primary source** |
| Earth Search (AWS Registry of Open Data) | Element 84 | Sentinel-2 L2A COGs | no login | previews only |
| ASF Vertex | NASA / Alaska Satellite Facility | Sentinel-1, ALOS PALSAR | free Earthdata login | backup |
| USGS EarthExplorer | USGS | Landsat 8/9 | free account | optional cross-check |
| NRSC Bhoonidhi | ISRO / NRSC | EOS-04 SAR, Resourcesat, Cartosat | free account | VHR reference if available |
| Umbra / Capella open data (AWS) | Umbra, Capella Space | sub-metre SAR | no login | VHR reference if a scene exists |
| OpenStreetMap (Overpass) | OSM Foundation | roads, bridges, landmarks | no login | AOI check, reference vectors |

## 7. Still to do in Phase 4

- [x] Register a Copernicus Data Space account.
- [x] Run the download script for the core products — 8/8 downloaded 23 Oct 2026 and verified (size, zip CRC, manifest.safe).
- [ ] Copernicus DEM GLO-30: let SNAP download it automatically during terrain correction (no manual step).
- [x] OSM reference layers in `06_vectors/osm.gpkg` (via `10_scripts/fetch_osm.py`): roads 11,428 · bridges 240 · rivers 48 · water areas 57 · buildings 66,311. Note: OSM shows today's map, not the 2025 Mela layout — use it for permanent features only.
- [ ] Check Umbra / Capella / Bhoonidhi for any VHR scene over the Sangam.
