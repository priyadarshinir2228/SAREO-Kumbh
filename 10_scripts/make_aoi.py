"""Build the SAREO-Kumbh AOI: a UTM 44N rectangle snapped to a 100 m grid, plus WGS 84 copies for portals and SNAP."""
from datetime import date
from math import ceil, floor
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "06_vectors"
WEST, SOUTH, EAST, NORTH = 81.82, 25.38, 81.96, 25.503  # north edge raised from 25.49 after the T1 extent check
SNAP = 100  # metres; multiple of the 10 m processing grid

# 1. Project the geographic box to UTM 44N and snap its envelope outward to the 100 m grid.
geo = gpd.GeoSeries([box(WEST, SOUTH, EAST, NORTH)], crs="EPSG:4326")
xmin, ymin, xmax, ymax = geo.to_crs("EPSG:32644").total_bounds
xmin, ymin = floor(xmin / SNAP) * SNAP, floor(ymin / SNAP) * SNAP
xmax, ymax = ceil(xmax / SNAP) * SNAP, ceil(ymax / SNAP) * SNAP
utm_rect = box(xmin, ymin, xmax, ymax)

attrs = {
    "id": 1,
    "name": "AOI_Kumbh",
    "description": "Maha Kumbh 2025 Mela area, Triveni Sangam, Prayagraj (both banks + city strip)",
    "epsg": 32644,
    "width_km": round((xmax - xmin) / 1000, 2),
    "height_km": round((ymax - ymin) / 1000, 2),
    "area_km2": round(utm_rect.area / 1e6, 2),
    "created": date.today().isoformat(),
    "source": "Extent 81.82-81.96 E, 25.38-25.503 N; landmarks checked in OSM; north edge checked on S2 2025-02-11; snapped to 100 m UTM grid",
}
aoi = gpd.GeoDataFrame([attrs], geometry=[utm_rect], crs="EPSG:32644")

# 2. Write outputs.
gpkg = OUT / "AOI_Kumbh.gpkg"
aoi.to_file(gpkg, layer="aoi", driver="GPKG")
aoi_wgs = aoi.to_crs("EPSG:4326")
aoi_wgs.to_file(OUT / "AOI_Kumbh_4326.geojson", driver="GeoJSON")
wkt = aoi_wgs.geometry.iloc[0].wkt
(OUT / "AOI_Kumbh_4326.wkt").write_text(wkt + "\n")

b = aoi_wgs.total_bounds
print(f"UTM 44N bounds (m): {xmin:.0f} {ymin:.0f} {xmax:.0f} {ymax:.0f}")
print(f"Size: {attrs['width_km']} x {attrs['height_km']} km = {attrs['area_km2']} km2")
print(f"WGS 84 bounds: W {b[0]:.5f}  S {b[1]:.5f}  E {b[2]:.5f}  N {b[3]:.5f}")
print(f"gdalwarp -te {xmin:.0f} {ymin:.0f} {xmax:.0f} {ymax:.0f} -tr 10 10 -tap")
print("WKT (SNAP Subset geoRegion):", wkt)
