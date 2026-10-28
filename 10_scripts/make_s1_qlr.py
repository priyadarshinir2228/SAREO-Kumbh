"""Build 08_layouts/S1_sigma0_nofilter.qlr: the 5 unfiltered Sentinel-1 dB rasters (VV display, -25..0 dB grey),
grouped, with relative paths. Drag the .qlr into QGIS (or Layer > Add from Layer Definition File) and save.
Run with QGIS Python: python-qgis-ltr.bat make_s1_qlr.py"""
from pathlib import Path

from qgis.core import (
    Qgis, QgsApplication, QgsContrastEnhancement, QgsLayerDefinition, QgsLayerTree, QgsRasterLayer,
    QgsSingleBandGrayRenderer,
)

ROOT = Path(r"D:\SAREO-Kumbh")
EPOCH = {"20241112": "T0", "20250123": "T1a", "20250204": "T1b", "20250216": "T1", "20250417": "T2"}

qgs = QgsApplication([], False)
qgs.initQgis()
tree = QgsLayerTree()
group = tree.addGroup("S1 sigma0 dB (unfiltered, orbit 92 desc)")
layers = []
for tif in sorted((ROOT / "02_preproc" / "S1").glob("S1A_*_Sig0_nofilter_dB.tif")):
    date = tif.name[4:12]
    lyr = QgsRasterLayer(str(tif), f"{EPOCH.get(date, date)} {date[:4]}-{date[4:6]}-{date[6:]} VV dB")
    ce = QgsContrastEnhancement(lyr.dataProvider().dataType(2))
    ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
    ce.setMinimumValue(-25.0)
    ce.setMaximumValue(0.0)
    renderer = QgsSingleBandGrayRenderer(lyr.dataProvider(), 2)  # band 2 = Sigma0_VV
    renderer.setContrastEnhancement(ce)
    lyr.setRenderer(renderer)
    layers.append(lyr)
    group.addLayer(lyr)
    print("added", lyr.name(), lyr.crs().authid(), lyr.width(), "x", lyr.height())

out = ROOT / "08_layouts" / "S1_sigma0_nofilter.qlr"
ok, msg = QgsLayerDefinition.exportLayerDefinition(str(out), [group], Qgis.FilePathType.Relative)
print("qlr written:", ok, msg, out)
qgs.exitQgis()
