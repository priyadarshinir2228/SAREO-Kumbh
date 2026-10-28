"""Add the AOI layer to SAREO_Kumbh.qgz (run with QGIS Python: python-qgis-ltr.bat add_aoi_to_project.py)."""
import shutil
import sys
from pathlib import Path

from qgis.core import (
    QgsApplication, QgsFillSymbol, QgsLayerTreeGroup, QgsProject, QgsVectorLayer,
)

ROOT = Path(r"D:\SAREO-Kumbh")
PROJECT = ROOT / "SAREO_Kumbh.qgz"
GPKG = ROOT / "06_vectors" / "AOI_Kumbh.gpkg"
GROUPS = ["01_SAR", "02_EO", "03_Fused", "04_Vectors", "05_Analysis"]

qgs = QgsApplication([], False)
qgs.initQgis()

shutil.copy2(PROJECT, PROJECT.with_suffix(".qgz.bak"))
project = QgsProject.instance()
if not project.read(str(PROJECT)):
    sys.exit(f"Cannot read {PROJECT}")

root = project.layerTreeRoot()
for name in GROUPS:  # standard layer groups from the implementation guide
    if root.findGroup(name) is None:
        root.addGroup(name)

for lyr in project.mapLayersByName("AOI_Kumbh"):
    project.removeMapLayer(lyr.id())

layer = QgsVectorLayer(f"{GPKG}|layername=aoi", "AOI_Kumbh", "ogr")
if not layer.isValid():
    sys.exit("AOI layer is not valid")
layer.renderer().setSymbol(QgsFillSymbol.createSimple(
    {"color": "0,0,0,0", "outline_color": "220,30,30,255", "outline_width": "0.8", "outline_style": "solid"}
))
project.addMapLayer(layer, False)
root.findGroup("04_Vectors").addLayer(layer)

print("project CRS:", project.crs().authid())
print("layer CRS:", layer.crs().authid(), "| features:", layer.featureCount(), "| extent:", layer.extent().toString(0))
print("saved:", project.write(str(PROJECT)))
qgs.exitQgis()
