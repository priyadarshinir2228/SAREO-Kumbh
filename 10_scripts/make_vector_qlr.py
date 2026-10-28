"""Build 08_layouts/Kumbh_features.qlr from kumbh_features.gpkg (each layer loads its default style from the
GeoPackage layer_styles table), relative paths. Run with QGIS Python: python-qgis-ltr.bat make_vector_qlr.py"""
from pathlib import Path

from qgis.core import Qgis, QgsApplication, QgsLayerDefinition, QgsLayerTree, QgsProject, QgsVectorLayer

ROOT = Path(r"D:\SAREO-Kumbh")
GPKG = ROOT / "06_vectors" / "kumbh_features.gpkg"
ORDER = ["pontoon_bridges", "temp_roads", "tent_blocks", "river_T1", "river_T0", "river_T2", "sand_bars", "veg_fields",
         "permanent_buildings"]
VISIBLE = {"pontoon_bridges", "tent_blocks", "river_T1"}
qgs = QgsApplication([], False)
qgs.initQgis()
tree = QgsLayerTree()
g = tree.addGroup("Kumbh feature database")
for name in ORDER:
    lyr = QgsVectorLayer(f"{GPKG}|layername={name}", name, "ogr")
    lyr.loadDefaultStyle()
    QgsProject.instance().addMapLayer(lyr, False)  # keep the layer alive until the .qlr is written
    g.addLayer(lyr).setItemVisibilityChecked(name in VISIBLE)
aoi = QgsVectorLayer(f"{ROOT / '06_vectors' / 'AOI_Kumbh.gpkg'}|layername=aoi", "AOI_Kumbh", "ogr")
QgsProject.instance().addMapLayer(aoi, False)
g.addLayer(aoi)
out = ROOT / "08_layouts" / "Kumbh_features.qlr"
ok, msg = QgsLayerDefinition.exportLayerDefinition(str(out), [g], Qgis.FilePathType.Relative)
print("qlr written:", ok, msg, out)
qgs.exitQgis()
