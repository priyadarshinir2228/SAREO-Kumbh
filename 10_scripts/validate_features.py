"""Phase 10 (brief 4.2 / 4.3): validate every layer of kumbh_features.gpkg.

Per layer: CRS, geometry validity (QGIS native:checkvalidity, GEOS), duplicate geometries (native:deleteduplicategeometries,
count only), NULLs in required fields, unique ids. Topology / spatial consistency: tent blocks overlapping each other,
tent blocks overlapping T1 water, bridges not crossing water, buildings inside tent blocks, road dangles.
Invalid geometries (if any) are repaired with native:fixgeometries and the layer replaced.
Output: 09_docs/validation_report.csv
"""
import json
import subprocess
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyogrio

ROOT = Path(r"D:\SAREO-Kumbh")
GPKG = ROOT / "06_vectors" / "kumbh_features.gpkg"
QP = r"C:\Program Files\QGIS 3.44.14\bin\qgis_process-qgis-ltr.bat"
TMP = ROOT / "06_vectors" / "merge_demo"
REQUIRED = ["id", "class", "epoch", "sensor", "method", "confidence"]


def run(alg, inputs):
    res = subprocess.run([QP, "run", alg, "-"], input=json.dumps({"inputs": inputs}), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{alg}: {res.stderr[-800:]}")
    return json.loads(res.stdout[res.stdout.index("{"):])["results"]


rows = []
layers = [l for l, _ in pyogrio.list_layers(GPKG) if l != "layer_styles"]
for layer in layers:
    src = f"{GPKG}|layername={layer}"
    g = gpd.read_file(GPKG, layer=layer)
    v = run("native:checkvalidity", {"INPUT_LAYER": src, "METHOD": 2, "VALID_OUTPUT": "TEMPORARY_OUTPUT",
                                      "INVALID_OUTPUT": "TEMPORARY_OUTPUT", "ERROR_OUTPUT": "TEMPORARY_OUTPUT"})
    dup = run("native:deleteduplicategeometries", {"INPUT": src, "OUTPUT": str(TMP / f"_dupcheck_{layer}.gpkg")})
    (TMP / f"_dupcheck_{layer}.gpkg").unlink(missing_ok=True)
    fixed = ""
    if int(v["INVALID_COUNT"]) > 0:
        out = str(TMP / f"_fixed_{layer}.gpkg")
        run("native:fixgeometries", {"INPUT": src, "METHOD": 1, "OUTPUT": out})
        gpd.read_file(out).to_file(GPKG, layer=layer, driver="GPKG")
        fixed = "repaired with native:fixgeometries (structure method)"
    nulls = {f: int(g[f].isna().sum()) for f in REQUIRED if f in g}
    rows.append({"layer": layer, "features": len(g), "crs": g.crs.to_string(), "invalid_geometries": int(v["INVALID_COUNT"]),
                 "duplicate_geometries": int(dup["DUPLICATE_COUNT"]), "null_required_fields": sum(nulls.values()),
                 "null_detail": ";".join(f"{k}={n}" for k, n in nulls.items() if n), "ids_unique": bool(g["id"].is_unique),
                 "action": fixed or "none needed"})
    print(rows[-1])

# ---- topology and spatial consistency ----
tb = gpd.read_file(GPKG, layer="tent_blocks")
w1 = gpd.read_file(GPKG, layer="river_T1")
br = gpd.read_file(GPKG, layer="pontoon_bridges")
bl = gpd.read_file(GPKG, layer="permanent_buildings")
rd = gpd.read_file(GPKG, layer="temp_roads")
pairs = gpd.sjoin(tb, tb, predicate="intersects")
pairs = pairs[pairs.index < pairs["index_right"]]
overlap = sum(tb.geometry[i].intersection(tb.geometry[j]).area for i, j in zip(pairs.index, pairs["index_right"]))
tw = gpd.overlay(tb, w1, how="intersection").area.sum()
br_water = [ln.intersection(w1.union_all()).length / ln.length for ln in br.geometry]
bl_in = gpd.sjoin(bl, tb, predicate="within").shape[0]
ends = [p for ln in rd.geometry.explode() for p in (ln.coords[0], ln.coords[-1])]
from collections import Counter
cnt = Counter((round(x, 1), round(y, 1)) for x, y in ends)
dangles = sum(1 for k, n in cnt.items() if n == 1)
topo = [
    ("tent_blocks", "tent blocks must not overlap each other", f"{overlap:.1f} m2 overlap in {len(pairs)} pairs"),
    ("tent_blocks", "tent blocks must not lie on T1 water", f"{tw:.0f} m2 ({100 * tw / tb.area.sum():.2f} % of tent area)"),
    ("pontoon_bridges", "bridges must cross T1 water", f"water fraction per bridge {', '.join(f'{f:.2f}' for f in br_water)}"),
    ("permanent_buildings", "no permanent building inside a tent block", f"{bl_in} buildings within tent blocks"),
    ("temp_roads", "road dangles (line ends touching no other line)", f"{dangles} of {len(cnt)} end points - expected: roads are clipped at tent-block edges"),
]
for layer, rule, result in topo:
    rows.append({"layer": layer, "check": rule, "result": result})
    print(f"{layer}: {rule}: {result}")
pd.DataFrame(rows).to_csv(ROOT / "09_docs" / "validation_report.csv", index=False)
