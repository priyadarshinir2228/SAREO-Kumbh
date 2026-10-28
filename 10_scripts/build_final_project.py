"""Phase 15: assemble SAREO_Kumbh.qgz (all products in the standard groups) and build + export the print layouts.
Run with QGIS Python while QGIS is closed: python-qgis-ltr.bat build_final_project.py

Groups: 01_SAR, 02_EO, 03_Fused, 04_Vectors, 05_Analysis (+ OSM basemap). Layer files (.qlr) from Phases 5/7/9/10 are
reused so styles stay identical. Layouts (A4 landscape, title, map(s), legend, scale bar, north arrow, grid, credits):
  01 AOI and location · 02 Sentinel-1 T0/T1/T2 · 03 Sentinel-2 composites T1 · 04 Fusion products · 05 Change map
  06 Classification · 07 Feature database
Exports: 08_layouts/<nn>_<name>.pdf and .png (150 dpi)
"""
import shutil
from pathlib import Path

from qgis.core import (Qgis, QgsApplication, QgsColorRampShader, QgsContrastEnhancement, QgsCoordinateReferenceSystem,
                       QgsLayerDefinition, QgsLayoutExporter, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap,
                       QgsMapLayerLegendUtils,
                       QgsLayoutItemPicture, QgsLayoutItemScaleBar, QgsLayoutPoint, QgsLayoutSize, QgsPalettedRasterRenderer,
                       QgsPrintLayout, QgsProject, QgsRasterLayer, QgsRasterShader, QgsRectangle, QgsSingleBandGrayRenderer,
                       QgsSingleBandPseudoColorRenderer, QgsStyle, QgsUnitTypes, QgsVectorLayer)
from qgis.PyQt.QtGui import QColor, QFont

ROOT = Path(r"D:\SAREO-Kumbh")
PROJ = ROOT / "SAREO_Kumbh.qgz"
LAY = ROOT / "08_layouts"
AOI_EXT = QgsRectangle(582400, 2807200, 596600, 2821000)
ZOOM = QgsRectangle(587000, 2810500, 593000, 2816500)
CREDITS = ("Contains modified Copernicus Sentinel data 2024-2025 (ESA). OSM data (c) OpenStreetMap contributors. "
           "CRS WGS 84 / UTM 44N (EPSG:32644). SAREO-Kumbh, Oct 2026.")

qgs = QgsApplication([], False)
qgs.initQgis()
shutil.copy2(PROJ, PROJ.with_name("SAREO_Kumbh_before_phase15.qgz"))
proj = QgsProject.instance()
proj.read(str(PROJ))
proj.setCrs(QgsCoordinateReferenceSystem("EPSG:32644"))
proj.setFilePathStorage(Qgis.FilePathType.Relative)
proj.setTitle("SAREO-Kumbh: Maha Kumbh 2025 tent city from Sentinel-1 and Sentinel-2")
root = proj.layerTreeRoot()
for lyr in list(proj.mapLayers().values()):  # rebuild cleanly (keeps nothing but groups' order)
    if lyr.name() != "AOI_Kumbh":
        proj.removeMapLayer(lyr.id())
groups = {g: (root.findGroup(g) or root.addGroup(g)) for g in ("04_Vectors", "05_Analysis", "03_Fused", "02_EO", "01_SAR", "Basemap")}


def raster(path, name, group, visible=False):
    l = QgsRasterLayer(str(path), name)
    assert l.isValid(), path
    proj.addMapLayer(l, False)
    groups[group].addLayer(l).setItemVisibilityChecked(visible)
    return l


def gray(l, band, lo, hi):
    ce = QgsContrastEnhancement(l.dataProvider().dataType(band))
    ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
    ce.setMinimumValue(lo); ce.setMaximumValue(hi)
    r = QgsSingleBandGrayRenderer(l.dataProvider(), band); r.setContrastEnhancement(ce); l.setRenderer(r)
    return l


def pseudo(l, ramp, lo, hi, invert=False):
    fn = QgsColorRampShader(lo, hi, QgsStyle.defaultStyle().colorRamp(ramp))
    if invert:
        fn.sourceColorRamp().invert()
    fn.classifyColorRamp(9, -1)
    sh = QgsRasterShader(); sh.setRasterShaderFunction(fn)
    l.setRenderer(QgsSingleBandPseudoColorRenderer(l.dataProvider(), 1, sh))
    return l


# ---- layers ----
osm = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0", "OpenStreetMap", "wms")
proj.addMapLayer(osm, False); groups["Basemap"].addLayer(osm).setItemVisibilityChecked(False)
s1 = {}
for d, lab in (("20241112", "T0 2024-11-12"), ("20250123", "T1a 2025-01-23"), ("20250204", "T1b 2025-02-04"),
               ("20250216", "T1 2025-02-16"), ("20250417", "T2 2025-04-17")):
    s1[d] = gray(raster(ROOT / f"02_preproc/S1/S1A_{d}_Sig0_lee7_dB.tif", f"S1 VV dB Lee7x7 {lab}", "01_SAR", d == "20250216"), 2, -25, 0)
for qlr, grp in (("S2_composites_indices.qlr", "02_EO"), ("Fusion_products.qlr", "03_Fused"), ("Kumbh_features.qlr", "04_Vectors")):
    QgsLayerDefinition.loadLayerDefinition(str(LAY / qlr), proj, groups[grp])
nat = {l.name(): l for l in proj.mapLayers().values()}
lr = pseudo(raster(ROOT / "07_analysis/change/LR_VV_T1-T0_dB.tif", "Log-ratio VV T1-T0 (dB)", "05_Analysis"), "RdBu", -10, 10, invert=True)
chg = raster(ROOT / "07_analysis/change/change_class_T0-T1-T2.tif", "Change class T0-T1-T2", "05_Analysis")
chg.setRenderer(QgsPalettedRasterRenderer(chg.dataProvider(), 1, [
    QgsPalettedRasterRenderer.Class(1, QColor("#ff9800"), "appeared, still present at T2"),
    QgsPalettedRasterRenderer.Class(2, QColor("#1e88e5"), "disappeared only"),
    QgsPalettedRasterRenderer.Class(3, QColor("#d50000"), "temporary: appeared then gone")]))
rf = raster(ROOT / "07_analysis/classification/RF_Fused_plus_temporal_plus_change_rule_T1.tif", "RF fused + temporal + change rule, T1", "05_Analysis")
rf.setRenderer(QgsPalettedRasterRenderer(rf.dataProvider(), 1, [QgsPalettedRasterRenderer.Class(c, QColor(col), n) for c, col, n in (
    (1, "#1565c0", "water"), (2, "#d50000", "tent block"), (3, "#ef8f00", "sand"), (4, "#2e7d32", "vegetation"), (5, "#616161", "built-up"))]))
for f, n in (("RF_Fused_T1.tif", "RF fused, T1"), ("RF_EO-only_T1.tif", "RF EO only, T1"), ("RF_SAR-only_T1.tif", "RF SAR only, T1")):
    raster(ROOT / "07_analysis/classification" / f, n, "05_Analysis")
sam = QgsVectorLayer(str(ROOT / "07_analysis/ai/sam_tents_T1.gpkg"), "SAM tent outlines (AI)", "ogr")
proj.addMapLayer(sam, False); groups["05_Analysis"].addLayer(sam).setItemVisibilityChecked(False)
nat = {l.name(): l for l in proj.mapLayers().values()}
aoi = nat["AOI_Kumbh"]
print("layers in project:", len(proj.mapLayers()))


# ---- layout helpers ----
def new_layout(name, title, subtitle):
    lm = proj.layoutManager()
    old = lm.layoutByName(name)
    if old:
        lm.removeLayout(old)
    lay = QgsPrintLayout(proj); lay.initializeDefaults(); lay.setName(name)
    lay.pageCollection().page(0).setPageSize("A4", 1)  # landscape 297 x 210 mm
    for text, y, size, bold in ((title, 6, 16, True), (subtitle, 14, 10, False)):
        lab = QgsLayoutItemLabel(lay); lab.setText(text); f = QFont("Arial", size); f.setBold(bold); lab.setFont(f)
        lab.attemptMove(QgsLayoutPoint(10, y)); lab.attemptResize(QgsLayoutSize(277, 8)); lay.addLayoutItem(lab)
    cr = QgsLayoutItemLabel(lay); cr.setText(CREDITS); cr.setFont(QFont("Arial", 6))
    cr.attemptMove(QgsLayoutPoint(10, 202)); cr.attemptResize(QgsLayoutSize(277, 5)); lay.addLayoutItem(cr)
    lm.addLayout(lay)
    return lay


def add_map(lay, layers, extent, x, y, w, h=None, grid=True, label=None):
    h = h or w * extent.height() / extent.width()  # frame follows the extent's aspect, so nothing is cut off
    m = QgsLayoutItemMap(lay); m.attemptMove(QgsLayoutPoint(x, y)); m.attemptResize(QgsLayoutSize(w, h))
    m.setLayers(layers); m.setKeepLayerSet(True); m.setCrs(QgsCoordinateReferenceSystem("EPSG:32644")); m.setExtent(extent)
    m.setFrameEnabled(True)
    if grid:
        g = m.grid(); g.setEnabled(True); g.setIntervalX(2000); g.setIntervalY(2000); g.setAnnotationEnabled(True)
        g.setAnnotationPrecision(0); g.setAnnotationFont(QFont("Arial", 5)); g.setFrameStyle(1)
    lay.addLayoutItem(m)
    if label:
        t = QgsLayoutItemLabel(lay); t.setText(label); f = QFont("Arial", 9); f.setBold(True); t.setFont(f)
        t.attemptMove(QgsLayoutPoint(x, y - 6)); t.attemptResize(QgsLayoutSize(w, 5)); lay.addLayoutItem(t)
    return m


def decorate(lay, m, legend_layers=None, x_leg=None, scale_x=None, scale_y=None, titles=None):
    """Scale bar under the map, north arrow + legend to the right of the last map."""
    right = m.pos().x() + m.rect().width()
    x_leg = x_leg if x_leg is not None else right + 12
    sb = QgsLayoutItemScaleBar(lay); sb.setStyle("Single Box"); sb.setLinkedMap(m); sb.setUnits(QgsUnitTypes.DistanceKilometers)
    sb.setUnitLabel("km"); sb.setNumberOfSegments(4); sb.setNumberOfSegmentsLeft(0); sb.setUnitsPerSegment(1)
    sb.setFont(QFont("Arial", 7))
    sb.attemptMove(QgsLayoutPoint(scale_x if scale_x is not None else m.pos().x(),
                                  scale_y if scale_y is not None else m.pos().y() + m.rect().height() + 4))
    lay.addLayoutItem(sb)
    na = QgsLayoutItemPicture(lay); na.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
    na.attemptMove(QgsLayoutPoint(x_leg, 26)); na.attemptResize(QgsLayoutSize(9, 13)); na.setLinkedMap(m); lay.addLayoutItem(na)
    if legend_layers:
        lg = QgsLayoutItemLegend(lay); lg.setLinkedMap(m); lg.setAutoUpdateModel(False)
        mdl = lg.model().rootGroup(); mdl.removeAllChildren()
        for i, l in enumerate(legend_layers):
            node = mdl.addLayer(l)
            if titles:
                node.setCustomProperty("legend/title-label", titles[i])
            if isinstance(l, QgsRasterLayer) and l.renderer().type() == "paletted":
                n = len(l.renderer().classes())  # drop the "Band 1 (Palette)" header node, keep the classes
                QgsMapLayerLegendUtils.setLegendNodeOrder(node, list(range(1, n + 1)))
            lg.model().refreshLayerLegend(node)
        lg.setTitle("Legend"); lg.setWrapString("|"); lg.attemptMove(QgsLayoutPoint(x_leg, 44)); lay.addLayoutItem(lg)


def export(lay, stem):
    ex = QgsLayoutExporter(lay)
    r1 = ex.exportToPdf(str(LAY / f"{stem}.pdf"), QgsLayoutExporter.PdfExportSettings())
    s = QgsLayoutExporter.ImageExportSettings(); s.dpi = 150
    r2 = ex.exportToImage(str(LAY / f"{stem}.png"), s)
    print(f"{stem}: pdf {'ok' if r1 == 0 else r1}, png {'ok' if r2 == 0 else r2}")


s2_nat = nat["T1 natural (2-98 %)"]
# 01 AOI and location
lay = new_layout("01 AOI and location", "Study area: Triveni Sangam, Prayagraj (Maha Kumbh 2025)",
                 "AOI 14.2 x 13.8 km (196 km²) over Sentinel-2 natural colour, 16 Feb 2025; inset: OpenStreetMap")
m = add_map(lay, [aoi, s2_nat], AOI_EXT, 14, 26, 166)
add_map(lay, [aoi, osm], QgsRectangle(540000, 2770000, 640000, 2860000), 205, 118, 80, grid=False, label="Location")
decorate(lay, m, [aoi], titles=["Area of interest"])
export(lay, "01_AOI_location")


def triptych(name, title, subtitle, items, extent, stem):
    lay = new_layout(name, title, subtitle)
    for i, (layer, lab) in enumerate(items):
        m = add_map(lay, [layer], extent, 10 + i * 93, 40, 88, grid=False, label=lab)
    decorate(lay, m, None, x_leg=275, scale_x=10)
    export(lay, stem)


# 02 Sentinel-1 T0 / T1 / T2
triptych("02 Sentinel-1 epochs", "Sentinel-1 VV backscatter before, during and after the Mela",
         "Sigma0 dB, Lee 7x7, relative orbit 92 descending; grey stretch -25 (black) to 0 dB (white); AOI 14.2 x 13.8 km",
         [(s1["20241112"], "T0  12 Nov 2024 (before)"), (s1["20250216"], "T1  16 Feb 2025 (Mela)"), (s1["20250417"], "T2  17 Apr 2025 (after)")],
         AOI_EXT, "02_S1_T0_T1_T2")
# 03 Sentinel-2 composites, T1
triptych("03 Sentinel-2 composites T1", "Sentinel-2 colour composites during the Mela (16 Feb 2025)",
         "2-98 % linear stretch per band, 10 m; zoom 6 x 6 km on the Sangam",
         [(nat["T1 natural (2-98 %)"], "Natural colour  B4-B3-B2"), (nat["T1 fcc (2-98 %)"], "False colour  B8-B4-B3"),
          (nat["T1 swir (2-98 %)"], "SWIR  B12-B8A-B4")], ZOOM, "03_S2_composites_T1")

# 04 Fusion
lay = new_layout("04 Fusion", "SAR-EO fusion products (16 Feb 2025, zoom 6 x 6 km)",
                 "Left: multi-temporal SAR RGB (R = T1, G = T0, B = T2) - red/orange = bright only during the Mela. Right: high-pass SAR detail injected into S2")
m1 = add_map(lay, [nat["Multi-temporal SAR RGB (R=T1 G=T0 B=T2)"]], ZOOM, 14, 34, 130, grid=False, label="Multi-temporal SAR RGB")
add_map(lay, [nat["T1 HPF fusion, natural colour"]], ZOOM, 152, 34, 130, grid=False, label="HPF fusion, natural colour")
decorate(lay, m1, None, x_leg=286, scale_x=14)
export(lay, "04_Fusion")

# 05 Change
lay = new_layout("05 Change map", "Temporary tent city from Sentinel-1 change detection",
                 "Log-ratio VV: T1-T0 >= +3 dB and T2-T1 <= -2 dB (0.5 ha minimum); temporary area 12.2 km²; over Sentinel-1 VV T0")
m = add_map(lay, [aoi, chg, s1["20241112"]], AOI_EXT, 14, 26, 166)
decorate(lay, m, [chg], titles=["Change class (T0 -> T1 -> T2)"])
export(lay, "05_Change_map")

# 06 Classification
lay = new_layout("06 Classification", "Land cover during the Mela - Random Forest on fused SAR + EO + SAR time series",
                 "16 Feb 2025; overall accuracy 0.859, kappa 0.81 on 57 independent validation polygons; tent class requires ΔVV >= +1 dB")
m = add_map(lay, [aoi, rf], AOI_EXT, 14, 26, 166)
decorate(lay, m, [rf], titles=["Land-cover class"])
export(lay, "06_Classification")

# 07 Feature database
lay = new_layout("07 Feature database", "Feature database: tent blocks, pontoon bridges, river and temporary roads",
                 "kumbh_features.gpkg over Sentinel-2 natural colour, 16 Feb 2025 (zoom 6 x 6 km)")
vec = [nat[n] for n in ("pontoon_bridges", "temp_roads", "tent_blocks", "river_T1")]
m = add_map(lay, vec + [s2_nat], ZOOM, 14, 26, 166)
decorate(lay, m, vec, titles=["Pontoon bridges", "Temporary roads (OSM)", "Tent blocks", "River, T1"])
export(lay, "07_Feature_database")

print("project saved:", proj.write(str(PROJ)))
qgs.exitQgis()
