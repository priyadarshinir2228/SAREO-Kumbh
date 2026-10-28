"""Phase 10 (brief 4.1): build 06_vectors/kumbh_features.gpkg with one common attribute schema for every layer.

Schema: id (text, unique, e.g. TB-T1-0007), class, sub_class, epoch, date (ISO), sensor, source_ref, method,
        confidence (high / medium / low), area_m2, length_m, remarks
Layers: tent_blocks, pontoon_bridges, river_T0 / river_T1 / river_T2, sand_bars, veg_fields  (from extracted_raw.gpkg)
        temp_roads          OSM roads (2026 extract) inside the T1 tent city, confidence low (today's map, not 2025)
        permanent_buildings OSM buildings outside the tent city
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(r"D:\SAREO-Kumbh")
RAW = ROOT / "06_vectors" / "extracted_raw.gpkg"
OSM = ROOT / "06_vectors" / "osm.gpkg"
OUT = ROOT / "06_vectors" / "kumbh_features.gpkg"
FIELDS = ["id", "class", "sub_class", "epoch", "date", "sensor", "source_ref", "method", "confidence", "area_m2", "length_m", "remarks"]
SRC = {"S1A + S2": "Sentinel-1A GRD orbit 92 (Lee 7x7) + Sentinel-2 L2A T44RNP; 05_fused/fused_stack_<epoch>",
       "S1A (T0/T1/T2) + S2": "Sentinel-1A GRD 2024-11-12 / 2025-02-16 / 2025-04-17 + Sentinel-2 L2A; 05_fused",
       "S1A": "Sentinel-1A GRD 2025-02-16 orbit 92 (Lee 7x7); 02_preproc/S1",
       "S2": "Sentinel-2 L2A T44RNP 2025-02-16; 03_enhanced/S2 NDVI"}
PREFIX = {"tent_blocks": "TB", "pontoon_bridges": "PB", "water_T0": "RV", "water_T1": "RV", "water_T2": "RV",
          "sand_bars": "SB", "veg_fields": "VG", "temp_roads": "TR", "permanent_buildings": "BL"}


def finish(gdf, layer):
    gdf = gdf.copy()
    polys = gdf.geom_type.str.endswith("Polygon")
    gdf["area_m2"] = gdf.area.where(polys).round(1)
    gdf["length_m"] = gdf.length.where(~polys).round(1)
    if "source_ref" not in gdf or gdf["source_ref"].isna().all():
        gdf["source_ref"] = gdf["sensor"].map(SRC)
    ep = gdf["epoch"].fillna("NA").astype(str)
    gdf["id"] = [f"{PREFIX[layer]}-{e}-{i + 1:04d}" for i, e in enumerate(ep)]
    gdf["remarks"] = gdf.get("remarks", pd.Series([None] * len(gdf)))
    for f in FIELDS:
        if f not in gdf:
            gdf[f] = None
    keep = FIELDS + [c for c in gdf.columns if c.startswith("present_")]
    return gdf[keep + ["geometry"]]


if OUT.exists():
    OUT.unlink()
layers = {}
for raw_name, out_name in [("tent_blocks", "tent_blocks"), ("pontoon_bridges", "pontoon_bridges"), ("water_T0", "river_T0"),
                           ("water_T1", "river_T1"), ("water_T2", "river_T2"), ("sand_bars", "sand_bars"), ("veg_fields", "veg_fields")]:
    g = gpd.read_file(RAW, layer=raw_name)
    if raw_name == "pontoon_bridges":
        g["remarks"] = g.apply(lambda r: "also visible at " + ", ".join(e for e in ("T0", "T2") if r[f"present_{e}"])
                               if (r.present_T0 or r.present_T2) else "T1 only", axis=1)
    layers[out_name] = finish(g, raw_name)

tents = layers["tent_blocks"].union_all()
roads = gpd.read_file(OSM, layer="roads")
inside = roads[roads.intersects(tents)].copy()
inside["geometry"] = inside.intersection(tents)
inside = inside[~inside.is_empty & inside.geom_type.isin(["LineString", "MultiLineString"])]
layers["temp_roads"] = finish(gpd.GeoDataFrame({
    "class": "temp_road", "sub_class": inside["highway"].fillna("unclassified"), "epoch": "T1", "date": "2025-02-16",
    "sensor": "OSM", "source_ref": "OpenStreetMap via Overpass (extract 2026-10-22), roads clipped to T1 tent blocks",
    "method": "OSM roads intersected with extracted tent blocks", "confidence": "low",
    "remarks": "today's OSM map, may not match the 2025 Mela lanes; check against S2 2025-02-16"}, geometry=inside.geometry, crs=roads.crs),
    "temp_roads")

bld = gpd.read_file(OSM, layer="buildings")
bld = bld[bld.geom_type.isin(["Polygon", "MultiPolygon"])]  # GeoPackage stores them as MultiPolygon
bld = bld[~bld.intersects(tents)]
layers["permanent_buildings"] = finish(gpd.GeoDataFrame({
    "class": "permanent_building", "sub_class": bld["building"].fillna("yes"), "epoch": "static", "date": None,
    "sensor": "OSM", "source_ref": "OpenStreetMap via Overpass (extract 2026-10-22), outside the T1 tent city",
    "method": "OSM building footprints", "confidence": "medium", "remarks": None}, geometry=bld.geometry, crs=bld.crs),
    "permanent_buildings")

for name, g in layers.items():
    g.to_file(OUT, layer=name, driver="GPKG")
    print(f"{name:20s} {len(g):6d} features  fields: {len(g.columns) - 1}")
