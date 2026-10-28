"""Build 08_layouts/S2_composites_indices.qlr (natural, FCC, SWIR 8-bit display copies + NDVI/MNDWI/NDBI for T0/T1/T2),
relative paths. Run with QGIS Python: python-qgis-ltr.bat make_s2_qlr.py"""
from pathlib import Path

from qgis.core import (Qgis, QgsApplication, QgsColorRampShader, QgsLayerDefinition, QgsLayerTree, QgsProject,
                       QgsRasterLayer, QgsRasterShader, QgsSingleBandPseudoColorRenderer, QgsStyle)

ROOT = Path(r"D:\SAREO-Kumbh")
E = ROOT / "03_enhanced" / "S2"
DATES = [("T0", "20241113"), ("T1", "20250216"), ("T2", "20250417")]
RAMPS = {"NDVI": ("RdYlGn", -0.2, 0.8), "MNDWI": ("RdBu", -0.6, 0.6), "NDBI": ("PuOr", -0.4, 0.3)}

qgs = QgsApplication([], False)
qgs.initQgis()
tree = QgsLayerTree()
root = tree.addGroup("S2 L2A (10 m)")
for ep, date in DATES:
    g = root.addGroup(f"{ep} {date[:4]}-{date[4:6]}-{date[6:]}")
    for comp in ("natural", "fcc", "swir"):
        lyr = QgsRasterLayer(str(E / f"S2_{date}_{comp}_p2-98.tif"), f"{ep} {comp} (2-98 %)")
        QgsProject.instance().addMapLayer(lyr, False)  # project owns the layer; otherwise Python frees it and the .qlr keeps only the last one
        g.addLayer(lyr).setItemVisibilityChecked(comp == "natural" and ep == "T1")
    for name, (ramp, lo, hi) in RAMPS.items():
        lyr = QgsRasterLayer(str(E / f"S2_{date}_{name}.tif"), f"{ep} {name}")
        shader_fn = QgsColorRampShader(lo, hi, QgsStyle.defaultStyle().colorRamp(ramp))
        shader_fn.classifyColorRamp(5, -1)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(shader_fn)
        lyr.setRenderer(QgsSingleBandPseudoColorRenderer(lyr.dataProvider(), 1, shader))
        QgsProject.instance().addMapLayer(lyr, False)
        g.addLayer(lyr).setItemVisibilityChecked(False)
out = ROOT / "08_layouts" / "S2_composites_indices.qlr"
ok, msg = QgsLayerDefinition.exportLayerDefinition(str(out), [root], Qgis.FilePathType.Relative)
print("qlr written:", ok, msg, out)
qgs.exitQgis()
