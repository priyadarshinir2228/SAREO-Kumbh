"""Phase 14: find a partly cloudy Sentinel-2 L2A scene over the AOI (monsoon 2025) for a real cloud-mask test.
Searches Earth Search (AWS, no login), then reads only the AOI window of each scene's SCL and reports AOI cloud %."""
import json
import urllib.request

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

AOI = (582400, 2807200, 596600, 2821000)
body = {"collections": ["sentinel-2-l2a"],
        "query": {"mgrs:utm_zone": {"eq": 44}, "mgrs:latitude_band": {"eq": "R"}, "mgrs:grid_square": {"eq": "NP"},
                  "eo:cloud_cover": {"gte": 10, "lte": 80}},
        "datetime": "2025-06-15T00:00:00Z/2025-10-31T23:59:59Z", "limit": 50}
req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", data=json.dumps(body).encode(),
                            headers={"Content-Type": "application/json"})
feats = json.load(urllib.request.urlopen(req, timeout=60))["features"]
for f in sorted(feats, key=lambda f: f["properties"]["datetime"]):
    with rasterio.open(f["assets"]["scl"]["href"]) as s:
        scl = s.read(1, window=from_bounds(*AOI, s.transform), out_shape=(690, 710), resampling=Resampling.nearest)
    cloud = np.isin(scl, [8, 9, 10]).mean() * 100
    shadow = (scl == 3).mean() * 100
    print(f"{f['properties']['datetime'][:10]}  tile {f['properties']['eo:cloud_cover']:5.1f}%  AOI cloud {cloud:5.1f}%  "
          f"shadow {shadow:4.1f}%  nodata {(scl == 0).mean() * 100:4.1f}%  id {f['id']}")
