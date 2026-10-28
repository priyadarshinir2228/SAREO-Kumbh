"""Training / validation samples for supervised classification (dzetsaka, SCP demos in Phase 11; Random Forest in Phase 13).

Polygons are drawn from the feature database: inner parts (buffer -20 m) of tent blocks, T1 water, T2 sand bars
(minus any ground within 30 m of a T1 tent block, so 'sand' is sand at T1 too),
vegetated fields and OSM building blocks (buildings dissolved within 15 m), sampled at random, then split 70 / 30 into
training and validation by polygon (so no polygon is used for both). Integer field 'code' for the classifiers.
Output: 06_vectors/training_samples.gpkg (layers: training, validation)
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(r"D:\SAREO-Kumbh")
DB = ROOT / "06_vectors" / "kumbh_features.gpkg"
OUT = ROOT / "06_vectors" / "training_samples.gpkg"
rng = np.random.default_rng(7)
CLASSES = [  # code, name, layer, inward buffer (m), polygons wanted
    (1, "water", "river_T1", -20, 40), (2, "tent_block", "tent_blocks", -20, 40), (3, "sand", "sand_bars", -20, 40),
    (4, "vegetation", "veg_fields", -10, 40), (5, "built_up", "permanent_buildings", None, 40),
]
parts = []
tents = gpd.read_file(DB, layer="tent_blocks").buffer(30).union_all()
for code, name, layer, buf, n in CLASSES:
    g = gpd.read_file(DB, layer=layer)
    if layer == "sand_bars":
        # sand bars were mapped at T2 (after clearing): remove ground that carried tents at T1, otherwise the 'sand'
        # samples contain tent pixels (label noise found in Phase 13: 50 % of sand validation pixels called tent)
        g = g.assign(geometry=g.geometry.difference(tents))
        g = g[~g.is_empty]
    if layer == "permanent_buildings":  # dense building blocks: merge footprints closer than 15 m, keep blocks >= 0.5 ha
        blocks = gpd.GeoDataFrame(geometry=[g.buffer(7.5).union_all().buffer(-7.5)], crs=g.crs).explode(index_parts=False)
        g = blocks[blocks.area >= 5000]
    else:
        g = gpd.GeoDataFrame(geometry=g.buffer(buf), crs=g.crs).explode(index_parts=False)
        g = g[~g.is_empty & (g.area >= 2000)]
    # split large polygons into 300 m tiles so samples spread over the AOI
    xmin, ymin, xmax, ymax = g.total_bounds
    tiles = gpd.GeoDataFrame(geometry=[gpd.points_from_xy([x], [y])[0].buffer(150, cap_style=3)
                                       for x in np.arange(xmin, xmax, 300) for y in np.arange(ymin, ymax, 300)], crs=g.crs)
    pieces = gpd.overlay(g, tiles, how="intersection")
    pieces = pieces[pieces.area >= 2000].explode(index_parts=False)
    pick = pieces.iloc[rng.permutation(len(pieces))[:n]].copy()
    pick["code"], pick["class"] = code, name
    pick["split"] = np.where(rng.random(len(pick)) < 0.7, "training", "validation")
    parts.append(pick[["code", "class", "split", "geometry"]])
    print(f"{code} {name:10s} candidates {len(pieces):5d} -> {len(pick)} polygons ({(pick.split == 'training').sum()} train)")
# (tried in Phase 13: a 6th 'bare_field' class sampled outside the floodplain -> only 2 candidate polygons, because the
#  fallow fields lie inside the 1.5 km floodplain envelope; dropped in favour of a temporal rule in classify_rf.py)
s = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
s["area_m2"] = s.area.round(0)
if OUT.exists():
    OUT.unlink()
for split in ("training", "validation"):
    s[s.split == split].drop(columns="split").to_file(OUT, layer=split, driver="GPKG")
print(s.groupby(["split", "class"]).size().unstack(0))
