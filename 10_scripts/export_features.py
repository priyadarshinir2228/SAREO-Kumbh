"""Phase 10 (brief 4.2 fix + 4.6 export):
  * remove the duplicate OSM building geometries found by validate_features.py (native:deleteduplicategeometries)
  * export every layer of kumbh_features.gpkg to Shapefile, GeoJSON (WGS 84) and CSV with WKT geometry
Outputs: 07_analysis/exports/vectors/<format>/<layer>.*  and  09_docs/export_manifest.csv
"""
import json
import subprocess
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

ROOT = Path(r"D:\SAREO-Kumbh")
GPKG = ROOT / "06_vectors" / "kumbh_features.gpkg"
EXP = ROOT / "07_analysis" / "exports" / "vectors"
QP = r"C:\Program Files\QGIS 3.44.14\bin\qgis_process-qgis-ltr.bat"

tmp = ROOT / "06_vectors" / "merge_demo" / "_buildings_dedup.gpkg"
res = subprocess.run([QP, "run", "native:deleteduplicategeometries", "-"], capture_output=True, text=True,
                     input=json.dumps({"inputs": {"INPUT": f"{GPKG}|layername=permanent_buildings", "OUTPUT": str(tmp)}}))
r = json.loads(res.stdout[res.stdout.index("{"):])["results"]
gpd.read_file(tmp).to_file(GPKG, layer="permanent_buildings", driver="GPKG")
tmp.unlink()
print(f"permanent_buildings: removed {r['DUPLICATE_COUNT']} duplicates, kept {r['RETAINED_COUNT']}")

rows = []
for layer, _ in pyogrio.list_layers(GPKG):
    if layer == "layer_styles":
        continue
    g = gpd.read_file(GPKG, layer=layer)
    for fmt in ("shp", "geojson", "csv"):
        (EXP / fmt).mkdir(parents=True, exist_ok=True)
    shp = EXP / "shp" / f"{layer}.shp"
    g.to_file(shp)  # field names > 10 chars are not in the schema, so nothing is truncated
    g.to_crs("EPSG:4326").to_file(EXP / "geojson" / f"{layer}.geojson", driver="GeoJSON")
    csv = pd.DataFrame(g.drop(columns="geometry"))
    csv["wkt"] = g.geometry.to_wkt()
    csv.to_csv(EXP / "csv" / f"{layer}.csv", index=False)
    back = gpd.read_file(shp)
    rows.append({"layer": layer, "features": len(g), "shp_features": len(back),
                 "shp_fields_match": list(back.columns) == list(g.columns), "csv_rows": len(csv), "crs_gpkg_shp": "EPSG:32644",
                 "crs_geojson": "EPSG:4326"})
    print(rows[-1])
pd.DataFrame(rows).to_csv(ROOT / "09_docs" / "export_manifest.csv", index=False)
