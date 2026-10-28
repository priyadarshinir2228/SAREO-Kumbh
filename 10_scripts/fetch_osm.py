"""Download OpenStreetMap reference layers for the AOI (Overpass API) into 06_vectors/osm.gpkg (EPSG:32644)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Polygon

ROOT = Path(r"D:\SAREO-Kumbh")
aoi = gpd.read_file(ROOT / "06_vectors" / "AOI_Kumbh.gpkg")
w, s, e, n = aoi.to_crs("EPSG:4326").total_bounds
BB = f"{s},{w},{n},{e}"

LAYERS = {
    "roads": f'way["highway"]({BB});',
    "bridges": f'way["bridge"]["bridge"!="no"]({BB});',
    "rivers": f'way["waterway"~"river|canal|stream"]({BB});',
    "water_areas": f'(way["natural"="water"]({BB});way["waterway"="riverbank"]({BB}););',
    "buildings": f'way["building"]({BB});',
}
KEEP = ["osm_id", "name", "highway", "bridge", "waterway", "natural", "water", "building", "layer"]


SERVERS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def overpass(q):
    body = urllib.parse.urlencode({"data": f"[out:json][timeout:300];{q}out geom tags;"}).encode()
    for attempt in range(6):  # alternate servers, back off on 429/502/504
        url = SERVERS[attempt % len(SERVERS)]
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": "SAREO-Kumbh"})
            return json.load(urllib.request.urlopen(req, timeout=360))["elements"]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            print(f"  {url.split('/')[2]} failed ({exc}); retrying")
            time.sleep(15 * (attempt + 1))
    raise RuntimeError("Overpass unavailable")


out = ROOT / "06_vectors" / "osm.gpkg"
for layer, q in LAYERS.items():
    recs = []
    for el in overpass(q):
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
        if len(pts) < 2:
            continue
        closed = len(pts) >= 4 and pts[0] == pts[-1]
        polygonal = layer in ("water_areas", "buildings")
        geom = Polygon(pts) if (polygonal and closed) else LineString(pts)
        tags = el.get("tags", {})
        recs.append({"osm_id": el["id"], **{k: tags.get(k) for k in KEEP[1:]}, "geometry": geom})
    if not recs:
        print(f"{layer}: 0 features")
        continue
    gdf = gpd.GeoDataFrame(recs, crs="EPSG:4326").to_crs("EPSG:32644")
    gdf = gdf[gdf.geometry.is_valid]
    gdf = gpd.clip(gdf, aoi)
    gdf.to_file(out, layer=layer, driver="GPKG")
    print(f"{layer}: {len(gdf)} features")
print("saved", out)
