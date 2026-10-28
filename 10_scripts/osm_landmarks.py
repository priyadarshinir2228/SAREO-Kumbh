"""Query OpenStreetMap (Overpass) for landmarks around the Sangam to check the AOI covers the Mela area."""
import json
import urllib.parse
import urllib.request

BBOX = (25.33, 81.76, 25.52, 82.02)  # south, west, north, east (search window, wider than the AOI)
QUERY = f"""
[out:json][timeout:60];
(
  node["place"]["name"~"Sangam|Jhunsi|Arail|Naini|Daraganj|Jhusi",i]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["bridge"="yes"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  nwr["name"~"Sangam|Triveni|Kumbh|Mela|Parade Ground",i]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""

req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": QUERY}).encode(),
    headers={"User-Agent": "SAREO-Kumbh-AOI-check"},
)
data = json.load(urllib.request.urlopen(req, timeout=120))

seen = set()
for el in data["elements"]:
    name = el.get("tags", {}).get("name")
    lat = el.get("lat", el.get("center", {}).get("lat"))
    lon = el.get("lon", el.get("center", {}).get("lon"))
    if not name or lat is None or name in seen:
        continue
    seen.add(name)
    kind = "bridge" if el.get("tags", {}).get("bridge") == "yes" else el.get("tags", {}).get("place", el["type"])
    print(f"{lat:9.4f} {lon:9.4f}  {kind:10s} {name}")
