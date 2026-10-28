"""Build 08_layouts/Fusion_products.qlr: feature stacks (RGB = VV / NDVI / MNDWI), HPF fusion (natural colour) and the
multi-temporal SAR RGB, relative paths. Run with QGIS Python: python-qgis-ltr.bat make_fusion_qlr.py"""
from pathlib import Path

from qgis.core import (Qgis, QgsApplication, QgsContrastEnhancement, QgsLayerDefinition, QgsLayerTree,
                       QgsMultiBandColorRenderer, QgsProject, QgsRasterLayer)

ROOT = Path(r"D:\SAREO-Kumbh")
F = ROOT / "05_fused"


def rgb_layer(path, name, bands, ranges):
    lyr = QgsRasterLayer(str(path), name)
    r = QgsMultiBandColorRenderer(lyr.dataProvider(), *bands)
    for setter, b, (lo, hi) in zip((r.setRedContrastEnhancement, r.setGreenContrastEnhancement, r.setBlueContrastEnhancement), bands, ranges):
        ce = QgsContrastEnhancement(lyr.dataProvider().dataType(b))
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        ce.setMinimumValue(lo); ce.setMaximumValue(hi)
        setter(ce)
    lyr.setRenderer(r)
    QgsProject.instance().addMapLayer(lyr, False)  # keep the layer alive until the .qlr is written
    return lyr


qgs = QgsApplication([], False)
qgs.initQgis()
tree = QgsLayerTree()
g = tree.addGroup("Fusion (10 m, lossless)")
mt = QgsRasterLayer(str(F / "mtRGB_VV_R-T1_G-T0_B-T2_display.tif"), "Multi-temporal SAR RGB (R=T1 G=T0 B=T2)")
QgsProject.instance().addMapLayer(mt, False)
g.addLayer(mt)
g.addLayer(rgb_layer(F / "fusion_HPF_T1_20250216.tif", "T1 HPF fusion, natural colour", (3, 2, 1),
                     [(0.03, 0.30), (0.04, 0.27), (0.03, 0.25)])).setItemVisibilityChecked(False)
for ep, d in (("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")):
    g.addLayer(rgb_layer(F / f"fused_stack_{ep}_{d}.tif", f"{ep} stack RGB = VV / NDVI / MNDWI", (1, 10, 11),
                         [(-25, 0), (-0.2, 0.8), (-0.6, 0.4)])).setItemVisibilityChecked(False)
out = ROOT / "08_layouts" / "Fusion_products.qlr"
ok, msg = QgsLayerDefinition.exportLayerDefinition(str(out), [g], Qgis.FilePathType.Relative)
print("qlr written:", ok, msg, out)
qgs.exitQgis()
