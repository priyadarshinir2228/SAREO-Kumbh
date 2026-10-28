"""Phase 15 reopen test (brief 4.7): open the packaged projects from a DIFFERENT folder and check every layer loads.
Usage: python-qgis-ltr.bat reopen_test.py <extracted SAREO-Kumbh folder>
Checks per project: layers valid, data source inside the extracted folder (relative paths worked), layouts present.
Writes <folder>/09_docs/reopen_test_report.txt"""
import sys
from pathlib import Path

from qgis.core import QgsApplication, QgsProject

folder = Path(sys.argv[1]).resolve()
qgs = QgsApplication([], False)
qgs.initQgis()
lines = [f"Reopen test of {folder}"]
for name in ("SAREO_Kumbh.qgz", "SAREO_plugin_demo.qgz"):
    proj = QgsProject.instance()
    proj.clear()
    ok = proj.read(str(folder / name))
    layers = list(proj.mapLayers().values())
    bad = [l.name() for l in layers if not l.isValid()]
    local = [l for l in layers if l.providerType() in ("gdal", "ogr")]
    outside = [l.name() for l in local if not str(Path(l.source().split("|")[0]).resolve()).lower().startswith(str(folder).lower())]
    layouts = [lay.name() for lay in proj.layoutManager().layouts()]
    lines += [f"\n{name}: read {ok}; {len(layers)} layers; invalid {len(bad)} {bad}",
              f"  file layers outside the package folder: {len(outside)} {outside[:5]}",
              f"  CRS {proj.crs().authid()}; layouts {len(layouts)}: {layouts}"]
report = "\n".join(lines)
print(report)
(folder / "09_docs" / "reopen_test_report.txt").write_text(report, encoding="utf-8")
qgs.exitQgis()
