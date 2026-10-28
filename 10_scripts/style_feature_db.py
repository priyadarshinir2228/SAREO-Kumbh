"""Phase 10 (brief 4.4): store a default style in kumbh_features.gpkg for every layer (QGIS layer_styles table):
standard colours per class, a Value Map drop-down on 'class' and 'confidence', and field aliases. The styles open
automatically in any QGIS project that loads the GeoPackage. Run with QGIS Python: python-qgis-ltr.bat style_feature_db.py"""
from pathlib import Path

from qgis.core import (QgsApplication, QgsEditorWidgetSetup, QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
                       QgsVectorLayer)

GPKG = Path(r"D:\SAREO-Kumbh\06_vectors\kumbh_features.gpkg")
CLASSES = ["tent_block", "temp_road", "pontoon_bridge", "water", "sand_bar", "permanent_building", "veg_field", "dugout"]
STYLE = {  # layer: (geometry kind, symbol properties) - one colour per class, used in every map of the project
    "tent_blocks": ("fill", {"color": "213,0,0,110", "outline_color": "213,0,0,255", "outline_width": "0.3"}),
    "pontoon_bridges": ("line", {"line_color": "255,214,0,255", "line_width": "1.2"}),
    "river_T0": ("fill", {"color": "21,101,192,90", "outline_color": "21,101,192,255", "outline_width": "0.2"}),
    "river_T1": ("fill", {"color": "21,101,192,90", "outline_color": "21,101,192,255", "outline_width": "0.2"}),
    "river_T2": ("fill", {"color": "21,101,192,90", "outline_color": "21,101,192,255", "outline_width": "0.2"}),
    "sand_bars": ("fill", {"color": "249,168,37,90", "outline_color": "249,168,37,255", "outline_width": "0.2"}),
    "veg_fields": ("fill", {"color": "46,125,50,80", "outline_color": "46,125,50,255", "outline_width": "0.1"}),
    "temp_roads": ("line", {"line_color": "255,255,255,255", "line_width": "0.5"}),
    "permanent_buildings": ("fill", {"color": "120,120,120,120", "outline_color": "70,70,70,255", "outline_width": "0.05"}),
}
ALIASES = {"id": "Feature ID", "class": "Class", "sub_class": "Sub-class", "epoch": "Epoch", "date": "Date",
           "sensor": "Sensor", "source_ref": "Source", "method": "Method", "confidence": "Confidence",
           "area_m2": "Area (m²)", "length_m": "Length (m)", "remarks": "Remarks"}

qgs = QgsApplication([], False)
qgs.initQgis()
for layer, (kind, props) in STYLE.items():
    lyr = QgsVectorLayer(f"{GPKG}|layername={layer}", layer, "ogr")
    assert lyr.isValid(), layer
    sym = QgsFillSymbol.createSimple(props) if kind == "fill" else QgsLineSymbol.createSimple(props)
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    fields = lyr.fields()
    lyr.setEditorWidgetSetup(fields.indexOf("class"), QgsEditorWidgetSetup("ValueMap", {"map": [{c: c} for c in CLASSES]}))
    lyr.setEditorWidgetSetup(fields.indexOf("confidence"),
                             QgsEditorWidgetSetup("ValueMap", {"map": [{"high": "high"}, {"medium": "medium"}, {"low": "low"}]}))
    for f, a in ALIASES.items():
        if fields.indexOf(f) >= 0:
            lyr.setFieldAlias(fields.indexOf(f), a)
    msg = lyr.saveStyleToDatabase(layer, "SAREO-Kumbh standard style", True, "")
    print(f"{layer:20s} style saved {msg if msg else 'ok'}")
qgs.exitQgis()
