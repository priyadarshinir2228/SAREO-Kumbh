"""Search the Copernicus Data Space catalogue (no login needed) for Sentinel-1/2 scenes over the AOI per epoch.

Writes 09_docs/scene_candidates.csv with one row per product.
"""
import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\SAREO-Kumbh")
WKT = (ROOT / "06_vectors" / "AOI_Kumbh_4326.wkt").read_text().strip()
ODATA = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

EPOCHS = {
    "T0": ("2024-10-01", "2024-12-15"),
    "T1": ("2025-01-13", "2025-02-26"),
    "T2": ("2025-03-25", "2025-05-10"),
    "T3": ("2025-08-01", "2025-09-30"),
}
SEARCHES = [  # (collection, productType, extra filter)
    ("SENTINEL-1", "IW_GRDH_1S", ""),
    ("SENTINEL-1", "IW_SLC__1S", ""),
    ("SENTINEL-2", "S2MSI2A", " and Attributes/OData.CSC.DoubleAttribute/any(a:a/Name eq 'cloudCover' and a/OData.CSC.DoubleAttribute/Value le 20.0)"),
]


def query(collection, ptype, start, end, extra):
    flt = (
        f"Collection/Name eq '{collection}'"
        f" and OData.CSC.Intersects(area=geography'SRID=4326;{WKT}')"
        f" and ContentDate/Start ge {start}T00:00:00.000Z and ContentDate/Start le {end}T23:59:59.999Z"
        f" and Attributes/OData.CSC.StringAttribute/any(a:a/Name eq 'productType' and a/OData.CSC.StringAttribute/Value eq '{ptype}')"
        f"{extra}"
    )
    url = ODATA + "?" + urllib.parse.urlencode(
        {"$filter": flt, "$expand": "Attributes", "$orderby": "ContentDate/Start asc", "$top": "200"}
    )
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SAREO-Kumbh"}), timeout=120) as r:
        return json.load(r)["value"]


rows = []
for epoch, (start, end) in EPOCHS.items():
    for collection, ptype, extra in SEARCHES:
        if ptype == "IW_SLC__1S" and epoch not in ("T0", "T1"):
            continue
        for p in query(collection, ptype, start, end, extra):
            att = {a["Name"]: a.get("Value") for a in p.get("Attributes", [])}
            if p["Name"].endswith("_COG.SAFE"):
                continue  # skip duplicate COG variants
            rows.append({
                "epoch": epoch,
                "product_type": ptype,
                "date": p["ContentDate"]["Start"][:10],
                "time_utc": p["ContentDate"]["Start"][11:19],
                "platform": att.get("platformShortName", "") + att.get("platformSerialIdentifier", ""),
                "relative_orbit": att.get("relativeOrbitNumber", ""),
                "pass": att.get("orbitDirection", ""),
                "polarisation": att.get("polarisationChannels", ""),
                "cloud_percent": round(att["cloudCover"], 2) if "cloudCover" in att else "",
                "tile": att.get("tileId", ""),
                "baseline": att.get("processorVersion", ""),
                "size_mb": round(p.get("ContentLength", 0) / 1e6),
                "online": p.get("Online"),
                "id": p["Id"],
                "name": p["Name"],
            })

out = ROOT / "09_docs" / "scene_candidates.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} products written to {out}")
