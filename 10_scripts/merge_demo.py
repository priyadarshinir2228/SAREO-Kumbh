"""Phase 10 (brief item 9): merge shapefiles that hold the same kind of features but different attribute schemas,
then transfer the result to another project / document.

1. Split tent_blocks into 4 sector shapefiles (NW, NE, SW, SE around the Sangam) with deliberately different schemas,
   as if four people digitised them:  NW = project schema (10-char SHP names)  NE = Class / Area / Conf
   SW = CLASS / AREA_HA (hectares)  SE = project schema
2. QGIS Processing (qgis_process, JSON on stdin):  native:refactorfields per sector -> one schema
   native:mergevectorlayers -> merged layer (adds 'layer' + 'path' provenance fields)  native:dissolve by class
3. Same merge with GDAL: ogr2ogr -append with an SQL field mapping per sector
4. native:package -> one GeoPackage for transfer (plus the .qlr written by make_vector_qlr.py)
Outputs: 06_vectors/merge_demo/
"""
import json
import subprocess
from pathlib import Path

import geopandas as gpd

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "06_vectors" / "merge_demo"
OUT.mkdir(exist_ok=True)
QP = r"C:\Program Files\QGIS 3.44.14\bin\qgis_process-qgis-ltr.bat"
OGR = r"D:\conda_envs\sareo\Library\bin\ogr2ogr.exe"
CX, CY = 589500, 2813500

tb = gpd.read_file(ROOT / "06_vectors" / "kumbh_features.gpkg", layer="tent_blocks")
c = tb.geometry.representative_point()
sectors = {"NW": tb[(c.x < CX) & (c.y >= CY)], "NE": tb[(c.x >= CX) & (c.y >= CY)],
           "SW": tb[(c.x < CX) & (c.y < CY)], "SE": tb[(c.x >= CX) & (c.y < CY)]}
std = {"id": "id", "class": "class", "sub_class": "sub_class", "epoch": "epoch", "date": "date", "confidence": "confidence",
       "area_m2": "area_m2", "source_ref": "source_ref"}
for name, g in sectors.items():
    g = g.copy()
    if name == "NE":
        g = g.rename(columns={"class": "Class", "area_m2": "Area", "confidence": "Conf"})[["id", "Class", "epoch", "date", "Conf", "Area", "geometry"]]
    elif name == "SW":
        g["AREA_HA"] = (g["area_m2"] / 1e4).round(3)
        g = g.rename(columns={"class": "CLASS"})[["id", "CLASS", "epoch", "date", "confidence", "AREA_HA", "geometry"]]
    else:
        g = g[list(std) + ["geometry"]]
    g.to_file(OUT / f"tents_sector_{name}.shp")
    print(f"sector {name}: {len(g)} features, fields {[f for f in g.columns if f != 'geometry']}")


def run(alg, inputs):
    res = subprocess.run([QP, "run", alg, "-"], input=json.dumps({"inputs": inputs}), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{alg} failed:\n{res.stderr[-1500:]}\n{res.stdout[-1500:]}")
    return json.loads(res.stdout[res.stdout.index("{"):])["results"]


def fmap(expr):
    """Target schema for refactorfields: name -> (expression, type id)."""
    types = {"id": 10, "class": 10, "epoch": 10, "date": 10, "confidence": 10, "area_m2": 6}
    return [{"name": n, "type": t, "length": 0, "precision": 0, "expression": expr[n]} for n, t in types.items()]


MAPS = {
    "NW": fmap({"id": '"id"', "class": '"class"', "epoch": '"epoch"', "date": '"date"', "confidence": '"confidence"', "area_m2": '"area_m2"'}),
    "SE": fmap({"id": '"id"', "class": '"class"', "epoch": '"epoch"', "date": '"date"', "confidence": '"confidence"', "area_m2": '"area_m2"'}),
    "NE": fmap({"id": '"id"', "class": '"Class"', "epoch": '"epoch"', "date": '"date"', "confidence": '"Conf"', "area_m2": '"Area"'}),
    "SW": fmap({"id": '"id"', "class": '"CLASS"', "epoch": '"epoch"', "date": '"date"', "confidence": '"confidence"', "area_m2": '"AREA_HA" * 10000'}),
}
refactored = []
for name, m in MAPS.items():
    out = str(OUT / f"tents_sector_{name}_refactored.gpkg")
    run("native:refactorfields", {"INPUT": str(OUT / f"tents_sector_{name}.shp"), "FIELDS_MAPPING": m, "OUTPUT": out})
    refactored.append(out)
merged = str(OUT / "tents_merged_qgis.gpkg")
run("native:mergevectorlayers", {"LAYERS": refactored, "CRS": "EPSG:32644", "OUTPUT": merged})
dissolved = str(OUT / "tents_dissolved_by_class.gpkg")
run("native:dissolve", {"INPUT": merged, "FIELD": ["class"], "OUTPUT": dissolved})

# same merge with ogr2ogr: first sector creates the layer, the others -append with SQL field mapping
gdal_out = OUT / "tents_merged_ogr2ogr.gpkg"
if gdal_out.exists():
    gdal_out.unlink()
SQL = {"NW": 'SELECT id, class, epoch, date, confidence, area_m2 FROM "tents_sector_NW"',
       "SE": 'SELECT id, class, epoch, date, confidence, area_m2 FROM "tents_sector_SE"',
       "NE": 'SELECT id, Class AS class, epoch, date, Conf AS confidence, Area AS area_m2 FROM "tents_sector_NE"',
       "SW": 'SELECT id, CLASS AS class, epoch, date, confidence, AREA_HA * 10000 AS area_m2 FROM "tents_sector_SW"'}
for i, (name, sql) in enumerate(SQL.items()):
    cmd = [OGR, "-f", "GPKG", str(gdal_out), str(OUT / f"tents_sector_{name}.shp"), "-nln", "tents", "-sql", sql, "-dialect", "SQLITE"]
    if i:
        cmd[1:1] = ["-append", "-update"]
    subprocess.run(cmd, check=True, capture_output=True)

package = str(OUT / "tents_transfer_package.gpkg")
run("native:package", {"LAYERS": [merged, dissolved, str(ROOT / "06_vectors" / "kumbh_features.gpkg|layername=pontoon_bridges")],
                       "OUTPUT": package, "OVERWRITE": True, "SAVE_STYLES": True})

m1, m2, d = gpd.read_file(merged), gpd.read_file(gdal_out, layer="tents"), gpd.read_file(dissolved)
print(f"QGIS merge: {len(m1)} features, fields {[f for f in m1.columns if f != 'geometry']}")
print(f"ogr2ogr merge: {len(m2)} features, fields {[f for f in m2.columns if f != 'geometry']}")
print(f"area check: original {tb.area.sum() / 1e6:.3f} km2 | merged attr {m1.area_m2.sum() / 1e6:.3f} | merged geom {m1.area.sum() / 1e6:.3f}"
      f" | ogr2ogr attr {m2.area_m2.sum() / 1e6:.3f} | dissolved {d.area.sum() / 1e6:.3f} km2 ({len(d)} feature)")
print("NULL class after merge:", int(m1["class"].isna().sum()), "| ids unique:", m1["id"].is_unique)
