"""Phase 11: scripted QGIS demos + a demo project for the interactive plugins.
Run with QGIS Python: python-qgis-ltr.bat plugin_demos_qgis.py

A. Raster Calculator (QgsRasterCalculator - the engine behind Raster > Raster Calculator): dVV = VV_T1 - VV_T0 (dB)
B. Graphical Modeler: build and save 09_docs/models/tent_change_mask.model3
     inputs: SAR T0 dB, SAR T1 dB, threshold (dB, default 3)
     steps : gdal:rastercalculator (A - B) >= threshold -> gdal:sieve (< 50 px) -> gdal:polygonize -> extract DN = 1
     output: polygons of new strong scatterers (tent-city candidates)
C. QuickOSM (its Processing provider): bridges in the AOI from Overpass
D. Demo project SAREO_plugin_demo.qgz (separate from SAREO_Kumbh.qgz) with the layers each GUI plugin demo needs
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from osgeo import gdal
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsProcessingModelAlgorithm, QgsProcessingModelChildAlgorithm,
                       QgsProcessingModelChildParameterSource, QgsProcessingModelOutput, QgsProcessingModelParameter,
                       QgsProcessingParameterNumber, QgsProcessingParameterRasterLayer, QgsProject, QgsRasterLayer,
                       QgsVectorLayer)

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "07_analysis" / "plugin_demos"
OUT.mkdir(parents=True, exist_ok=True)
MODELS = ROOT / "09_docs" / "models"
MODELS.mkdir(exist_ok=True)
QP = r"C:\Program Files\QGIS 3.44.14\bin\qgis_process-qgis-ltr.bat"
T0 = ROOT / "02_preproc" / "S1" / "S1A_20241112_Sig0_lee7_dB.tif"
T1 = ROOT / "02_preproc" / "S1" / "S1A_20250216_Sig0_lee7_dB.tif"
T2 = ROOT / "02_preproc" / "S1" / "S1A_20250417_Sig0_lee7_dB.tif"

qgs = QgsApplication([], False)
qgs.initQgis()

# ---------- A. Raster Calculator ----------
l0, l1 = QgsRasterLayer(str(T0), "T0"), QgsRasterLayer(str(T1), "T1")
entries = []
for lyr, ref in ((l0, "T0@2"), (l1, "T1@2")):
    e = QgsRasterCalculatorEntry(); e.ref = ref; e.raster = lyr; e.bandNumber = 2; entries.append(e)
dvv = OUT / "rastercalc_dVV_T1-T0.tif"
calc = QgsRasterCalculator('"T1@2" - "T0@2"', str(dvv), "GTiff", l1.extent(), l1.width(), l1.height(), entries)
rc = calc.processCalculation()
ds_out, ds1, ds0 = gdal.Open(str(dvv)), gdal.Open(str(T1)), gdal.Open(str(T0))  # keep datasets alive while reading bands
a = ds_out.ReadAsArray()
ref = ds1.GetRasterBand(2).ReadAsArray() - ds0.GetRasterBand(2).ReadAsArray()
ds_out = ds1 = ds0 = None
print(f"A raster calculator: code {rc} (0 = ok); max |QGIS - numpy| = {np.nanmax(np.abs(a - ref)):.2e} dB; "
      f"pixels with dVV >= +3 dB: {100 * np.nanmean(a >= 3):.1f} %")

# ---------- B. Graphical Modeler ----------
m = QgsProcessingModelAlgorithm("Tent change mask (SAR log-ratio)", "SAREO-Kumbh")
m.setHelpContent({"ALG_DESC": "New strong scatterers between two co-registered Sentinel-1 sigma0 dB rasters: "
                              "(T1 - T0) >= threshold, polygonised. Band 2 = VV."})
for name, desc in (("sar_t0", "Sentinel-1 sigma0 dB, before (T0)"), ("sar_t1", "Sentinel-1 sigma0 dB, during (T1)")):
    m.addModelParameter(QgsProcessingParameterRasterLayer(name, desc), QgsProcessingModelParameter(name))
m.addModelParameter(QgsProcessingParameterNumber("threshold", "Increase threshold (dB)", QgsProcessingParameterNumber.Double, 3.0),
                    QgsProcessingModelParameter("threshold"))
calc_c = QgsProcessingModelChildAlgorithm("gdal:rastercalculator")
calc_c.setChildId("diff"); calc_c.setDescription("dVV >= threshold")
calc_c.addParameterSources("INPUT_A", [QgsProcessingModelChildParameterSource.fromModelParameter("sar_t1")])
calc_c.addParameterSources("BAND_A", [QgsProcessingModelChildParameterSource.fromStaticValue(2)])
calc_c.addParameterSources("INPUT_B", [QgsProcessingModelChildParameterSource.fromModelParameter("sar_t0")])
calc_c.addParameterSources("BAND_B", [QgsProcessingModelChildParameterSource.fromStaticValue(2)])
calc_c.addParameterSources("FORMULA", [QgsProcessingModelChildParameterSource.fromExpression("'(A - B) >= ' || to_string(@threshold)")])
calc_c.addParameterSources("RTYPE", [QgsProcessingModelChildParameterSource.fromStaticValue(0)])  # Byte
m.addChildAlgorithm(calc_c)
sieve = QgsProcessingModelChildAlgorithm("gdal:sieve")
sieve.setChildId("sieve"); sieve.setDescription("Sieve: drop patches < 50 px (0.5 ha)")
sieve.addParameterSources("INPUT", [QgsProcessingModelChildParameterSource.fromChildOutput("diff", "OUTPUT")])
sieve.addParameterSources("THRESHOLD", [QgsProcessingModelChildParameterSource.fromStaticValue(50)])
sieve.addParameterSources("EIGHT_CONNECTEDNESS", [QgsProcessingModelChildParameterSource.fromStaticValue(False)])
m.addChildAlgorithm(sieve)
poly = QgsProcessingModelChildAlgorithm("gdal:polygonize")
poly.setChildId("poly"); poly.setDescription("Polygonize")
poly.addParameterSources("INPUT", [QgsProcessingModelChildParameterSource.fromChildOutput("sieve", "OUTPUT")])
poly.addParameterSources("BAND", [QgsProcessingModelChildParameterSource.fromStaticValue(1)])
poly.addParameterSources("FIELD", [QgsProcessingModelChildParameterSource.fromStaticValue("DN")])
m.addChildAlgorithm(poly)
ext = QgsProcessingModelChildAlgorithm("native:extractbyattribute")
ext.setChildId("keep"); ext.setDescription("Keep DN = 1")
ext.addParameterSources("INPUT", [QgsProcessingModelChildParameterSource.fromChildOutput("poly", "OUTPUT")])
ext.addParameterSources("FIELD", [QgsProcessingModelChildParameterSource.fromStaticValue("DN")])
ext.addParameterSources("OPERATOR", [QgsProcessingModelChildParameterSource.fromStaticValue(0)])
ext.addParameterSources("VALUE", [QgsProcessingModelChildParameterSource.fromStaticValue("1")])
out_def = QgsProcessingModelOutput("change_polygons", "Change polygons")
out_def.setChildOutputName("OUTPUT"); out_def.setChildId("keep")
ext.setModelOutputs({"change_polygons": out_def})
m.addChildAlgorithm(ext)
model_path = MODELS / "tent_change_mask.model3"
print("B model saved:", m.toFile(str(model_path)), model_path)
res = subprocess.run([QP, "run", str(model_path), "-"], capture_output=True, text=True, input=json.dumps({"inputs": {
    "sar_t0": str(T0), "sar_t1": str(T1), "threshold": 3.0, "change_polygons": str(OUT / "model_change_polygons_T1-T0.gpkg")}}))
print("  model run:", "ok" if res.returncode == 0 else res.stderr[-600:])

# ---------- C. QuickOSM ----------
aoi = "582400,596600,2807200,2821000 [EPSG:32644]"
for server in ("https://overpass.kumi.systems/api/interpreter", "https://overpass-api.de/api/interpreter"):
    res = subprocess.run([QP, "run", "quickosm:downloadosmdataextentquery", "-"], capture_output=True, text=True, input=json.dumps(
        {"inputs": {"KEY": "bridge", "VALUE": "yes", "EXTENT": aoi, "TIMEOUT": 120, "SERVER": server,
                    "OUTPUT_LINES": str(OUT / "quickosm_bridges_lines.gpkg")}}))
    if res.returncode == 0:
        break
    print("  QuickOSM server failed, trying next:", server.split("/")[2])
if res.returncode == 0:
    n = QgsVectorLayer(str(OUT / "quickosm_bridges_lines.gpkg"), "q", "ogr").featureCount()
    print(f"C QuickOSM bridge=yes lines: {n} features")
else:
    print("C QuickOSM failed:", res.stderr[-600:])

# ---------- D. demo project for the GUI plugins ----------
proj = QgsProject.instance()
proj.clear()
proj.setCrs(QgsCoordinateReferenceSystem("EPSG:32644"))
proj.setFilePathStorage(Qgis.FilePathType.Relative)
proj.setTitle("SAREO-Kumbh plugin demonstrations")
root = proj.layerTreeRoot()
layers = [
    ("rasters", QgsRasterLayer(str(ROOT / "03_enhanced/S2/S2_20250216_natural_p2-98.tif"), "S2 T1 natural colour")),
    ("rasters", QgsRasterLayer(str(T0), "S1 T0 2024-11-12 sigma0 dB (VH, VV)")),
    ("rasters", QgsRasterLayer(str(T1), "S1 T1 2025-02-16 sigma0 dB (VH, VV)")),
    ("rasters", QgsRasterLayer(str(T2), "S1 T2 2025-04-17 sigma0 dB (VH, VV)")),
    ("rasters", QgsRasterLayer(str(ROOT / "05_fused/fused_stack_T1_20250216.tif"), "T1 fused stack (11 bands)")),
    ("vectors", QgsVectorLayer(f"{ROOT / '06_vectors/kumbh_features.gpkg'}|layername=tent_blocks", "tent_blocks", "ogr")),
    ("vectors", QgsVectorLayer(f"{ROOT / '06_vectors/kumbh_features.gpkg'}|layername=pontoon_bridges", "pontoon_bridges", "ogr")),
    ("vectors", QgsVectorLayer(f"{ROOT / '06_vectors/kumbh_features.gpkg'}|layername=temp_roads", "temp_roads", "ogr")),
]
layers += [
    ("training (dzetsaka / SCP)", QgsVectorLayer(f"{ROOT / '06_vectors/training_samples.gpkg'}|layername=training", "training_samples", "ogr")),
    ("Serval (edit this copy only)", QgsRasterLayer(str(OUT / "serval_demo_copy_T1_dB.tif"), "serval_demo_copy_T1_dB")),
]
for sector in ("NW", "NE", "SW", "SE"):
    layers.append(("merge demo (MMQGIS)", QgsVectorLayer(str(ROOT / f"06_vectors/merge_demo/tents_sector_{sector}.shp"), f"tents_sector_{sector}", "ogr")))
groups = {}
for gname, lyr in layers:
    assert lyr.isValid(), lyr.name()
    lyr.loadDefaultStyle() if isinstance(lyr, QgsVectorLayer) else None
    groups.setdefault(gname, root.addGroup(gname))
    proj.addMapLayer(lyr, False)
    groups[gname].addLayer(lyr)
demo = ROOT / "SAREO_plugin_demo.qgz"
print("D demo project written:", proj.write(str(demo)), demo)
qgs.exitQgis()
