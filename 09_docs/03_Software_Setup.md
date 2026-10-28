# Software Setup — SAREO-Kumbh (Phase 2)

**Checked:** 22 Oct 2026 on this PC.

## 1. What is already on this PC

| Item | Found | Notes |
| --- | --- | --- |
| QGIS | **No** | Install (step 3) |
| ESA SNAP | **No** | Install (step 4) |
| Orfeo ToolBox | **No** | Install (step 5) |
| GDAL command line | **No** (not on PATH) | Comes with QGIS/OSGeo4W and the `sareo` conda env |
| Miniconda3 (Python 3.14, conda 26.5.3) | Yes — `python` on PATH points here | Used to create the project env |
| Anaconda3 2025.06 (Python 3.13) | Yes | Not used for this project |
| Python 3.12.10 (python.org) | Yes | Not used for this project |
| Existing conda envs | kidney, kidney_tf, sih_env | Left untouched |
| Git 2.51.2 | Yes | Optional, for versioning scripts |

## 2. Hardware

| Item | Value | Impact |
| --- | --- | --- |
| CPU | Intel Core Ultra 5 125H, 14 cores / 18 threads | Good for SNAP and Random Forest |
| RAM | 15.5 GB usable (16 GB) | Enough; SNAP max heap ≈ 11 GB; always subset to the AOI early |
| GPU | Intel Arc (integrated), no NVIDIA/CUDA | AI steps (SAR2SAR, OmniCloudMask, SAM) run on **CPU** — slower but fine for a small AOI |
| C: free | **46.6 GB** — tight | Keep SNAP user data, caches and conda env **off C:** |
| D: free | 184.9 GB | Project data, conda env, SNAP user dir go here |
| E: free | 57.6 GB | Spare / backup |

## 2b. Installed by Claude via PowerShell (22 Oct 2026)

| Software | Version | Location | How | Verified |
| --- | --- | --- | --- | --- |
| QGIS LTR | 3.44.14 | `C:\Program Files\QGIS 3.44.14` | `winget install OSGeo.QGIS_LTR --silent` | launches via `qgis-ltr.bat`; providers: native (298 algs), GDAL (57), PDAL, 3D |
| GDAL (bundled with QGIS) | 3.13.3 | `C:\Program Files\QGIS 3.44.14\bin` | with QGIS | `gdalinfo --version` |
| ESA SNAP (Sentinel Toolboxes) | 14.0.0 | `D:\esa-snap` | official installer from download.esa.int, silent (`-q -dir`) | `gpt -h` lists Apply-Orbit-File, ThermalNoiseRemoval, Remove-GRD-Border-Noise, Calibration, Speckle-Filter, Multi-Temporal-Speckle-Filter, Terrain-Correction, LinearToFromdB, Coherence |
| SNAP heap | `-Xmx10G` | `D:\esa-snap\bin\gpt.vmoptions`, `etc\snap.conf` | installer default | kept (10 GB of 16 GB) |
| SNAP user dir | `D:/snap_userdir` | `D:\esa-snap\etc\snap.properties` (backup `.bak`) | edited | auxdata now created on D: |
| Orfeo ToolBox | 9.1.1 | `D:\OTB` | official zip, extracted with `tar` | `otbcli.ps1 Despeckle -help` runs (load `D:\OTB\otbenv.ps1` first) |
| Python env `sareo` | Python 3.11 | `D:\conda_envs\sareo` | conda-forge + pip (CPU PyTorch) | `10_scripts\check_env.py` |

Installers kept in `D:\installers` (SNAP .exe 1,070 MB, MD5 676DD30BE6E598D25CB3ECDC7BC31BFC; OTB zip 107 MB) — delete later to free space. ESA publishes no checksum or code signature for the SNAP installer; it was downloaded over HTTPS from the official ESA server.

### Still to do by hand in QGIS (GUI)

1. Open **QGIS 3.44.14 LTR** from the Start menu.
2. Plugins → Manage and Install Plugins → **Installed**: tick **GRASS GIS provider** (GRASS currently shows 0 algorithms).
3. **All** tab → install: **OrfeoToolbox Provider** (OTB plugin is in the catalogue since QGIS 3.36), **Processing Saga NextGen Provider** (optional — needs a separate SAGA install), **Semi-Automatic Classification Plugin**, **QuickMapServices**, **QuickOSM**, **Value Tool**, **Profile Tool**, **Serval**, **MMQGIS**, **dzetsaka**, **GeoAI** (or **Geo-SAM**), and enable **Topology Checker**.
4. Settings → Options → Processing → Providers → **OTB**: tick Activate, OTB folder `D:\OTB`, applications folder `D:\OTB\lib\otb\applications`.
5. Create the project: Project → New → Properties → CRS **EPSG:32644**, General → Save paths **Relative** → save as `D:\SAREO-Kumbh\SAREO_Kumbh.qgz`.

## 3. QGIS — install the LTR

- **Version:** QGIS **3.44 LTR** (3.44.15 "Solothurn" at time of check). The newest release is 4.2.3, but QGIS 4 moved to Qt6 and some plugins this project needs may not support it yet; the LTR is the safer choice for a graded submission.
- **Installer:** OSGeo4W Network Installer from https://qgis.org/download/ (recommended there) → *Express Install* → tick **QGIS LTR** (and GRASS GIS). It bundles GDAL, GRASS, SAGA.
- **After install:**
  1. Open QGIS LTR → Settings → Options → Processing → Providers: confirm GDAL, GRASS and SAGA are active.
  2. Plugins → Manage and Install Plugins → install: **Semi-Automatic Classification Plugin (SCP)**, **QuickMapServices**, **QuickOSM**, **Value Tool**, **Profile Tool**, **Serval**, **MMQGIS**, **dzetsaka**, **GeoAI** (or **Geo-SAM**). Georeferencer and Topology Checker are built in (enable Topology Checker under *Installed*).
  3. Open `D:\SAREO-Kumbh` and create `SAREO_Kumbh.qgz`: Project → Properties → CRS **EPSG:32644**; General → Save paths **Relative**.
- **Check:** Processing Toolbox lists GDAL, GRASS, SAGA.

## 4. ESA SNAP 14 — Sentinel-1 processing

- **Version:** SNAP **14.0.0** (released 18 Aug 2026), from https://step.esa.int/main/download/snap-download/ → Windows 64-bit **Sentinel Toolboxes** (≈ 1 GB; includes Microwave = Sentinel-1 toolbox).
- **Install path:** `D:\esa-snap` (keeps C: free).
- **During install:** accept the default Java bundled with SNAP; when asked about memory, allow the suggested max heap (≈ 70% of RAM ≈ 11 GB).
- **Move user data off C:** after install, edit `D:\esa-snap\etc\snap.properties` and set `snap.userdir=D:/snap_userdir` (orbit files, DEM tiles and caches go there; they grow to several GB).
- **Heap check:** `D:\esa-snap\bin\gpt.vmoptions` and `snap64.exe.vmoptions` should contain `-Xmx11G`.
- **First run:** Help → Check for Updates; then Tools → Options → S1TBX: allow automatic download of orbit files and DEM.
- **Check:** open a Sentinel-1 GRD `.zip` → Radar → Apply Orbit File runs without error.

## 5. Orfeo ToolBox (OTB)

- Download the Windows 64-bit OTB zip from https://www.orfeo-toolbox.org/ (no installer — unzip only) to `D:\OTB`.
- QGIS → Settings → Options → Processing → Providers → **OTB**: tick *Activate*, OTB folder = `D:\OTB`, application folder = `D:\OTB\lib\otb\applications`.
- Known issue: on some QGIS versions the *Activate* box is missing; if so, install/enable the "OrfeoToolbox Provider" plugin from the plugin manager and retry.
- **Check:** Processing Toolbox shows OTB → *Despeckle*, *DimensionalityReduction*, *ContrastEnhancement*.

## 6. Python environment `sareo` (created by Claude)

- **Location:** `D:\conda_envs\sareo` (Python 3.11, conda-forge).
- **Packages:** gdal, rasterio, geopandas, numpy, scipy, matplotlib, scikit-image, scikit-learn, arosics, jupyterlab, tqdm; then pip: omnicloudmask, deepdespeckling (CPU PyTorch).
- **Activate:**

```
conda activate D:\conda_envs\sareo
```

- **Check:** `python D:\SAREO-Kumbh\10_scripts\check_env.py` prints every package version.

## 7. Accounts to register (free)

| Portal | Use | URL |
| --- | --- | --- |
| Copernicus Data Space Ecosystem | Sentinel-1, Sentinel-2, DEM | https://dataspace.copernicus.eu |
| ASF Vertex (NASA Earthdata login) | Sentinel-1 backup, baseline tool | https://search.asf.alaska.edu |
| USGS EarthExplorer | Landsat 8/9 | https://earthexplorer.usgs.gov |
| NRSC Bhoonidhi | EOS-04, Resourcesat, Cartosat | https://bhoonidhi.nrsc.gov.in |
| Hugging Face (optional) | SAM 3 access for the GeoAI plugin | https://huggingface.co |

You create these accounts yourself — Claude does not sign up or enter passwords.

## 8. Phase 2 completion checklist

- [x] Inventory of installed software and hardware
- [x] Folder structure (Phase 0)
- [x] QGIS 3.44 LTR installed (3.44.14)
- [x] QGIS: GRASS provider enabled (307 algorithms), OTB provider configured (109 algorithms), project plugins installed — verified 22 Oct 2026

### Verification (22 Oct 2026)

| Item | Result |
| --- | --- |
| Plugins in profile | dzetsaka 5.1.1, geoai 1.8.1, mmqgis 2024.11.8, orfeoToolbox_provider 3.0.3, profiletool 4.3.4, QuickOSM 2.5.4, quick_map_services 1.5.2, SemiAutomaticClassificationPlugin 8.5.0, Serval 3.32.0, topology_checker 1.1.0, valuetool |
| OTB provider | Plugin 3.0.3 has **no "Activate" box** (removed upstream). Set by Claude in QGIS3.ini: `Processing/Configuration/OTB_FOLDER=D:/OTB`, `OTB_APP_FOLDER=D:/OTB/lib/otb/applications`, plugin enabled |
| GRASS provider | Enabled (`PythonPlugins/grassprovider=true`) |
| `qgis_process list` | native 298 · GDAL 57 · GRASS 307 · OTB 109 (incl. Despeckle, DimensionalityReduction, ContrastEnhancement, BandMath, Pansharpening) |
| OTB end-to-end test | `otb:Despeckle` Lee 5×5 on a synthetic speckle raster: ENL 1.00 → 11.64 |
| Project | `SAREO_Kumbh.qgz`: CRS EPSG:32644, relative paths, 0 layers |
| SAGA | Not installed (optional; GRASS + OTB cover the needed tools) |

Restart QGIS (File → Exit, reopen) so the open session shows OTB in the Processing Toolbox.
- [x] SNAP 14 installed on D:, user dir on D:, heap 10 GB
- [x] OTB 9.1.1 unzipped to D:\OTB
- [x] `sareo` conda environment created (see check_env.py output)
- [ ] Accounts registered
- [ ] `SAREO_Kumbh.qgz` created with EPSG:32644 and relative paths
