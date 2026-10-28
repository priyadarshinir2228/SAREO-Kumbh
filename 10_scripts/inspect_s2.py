"""Print band files, BOA offsets, quantification value, baseline and cloud cover of each Sentinel-2 L2A zip."""
import re
import zipfile
from pathlib import Path

for z in sorted(Path(r"D:\SAREO-Kumbh\01_raw\S2").glob("*.zip")):
    names = zipfile.ZipFile(z).namelist()
    x = zipfile.ZipFile(z).read(next(n for n in names if n.endswith("MTD_MSIL2A.xml"))).decode()
    jp2 = [n for n in names if n.endswith(".jp2") and "/IMG_DATA/" in n]
    print(z.name[:60])
    print("  BOA_ADD_OFFSET:", sorted(set(re.findall(r'BOA_ADD_OFFSET band_id="\d+">(-?\d+)<', x))),
          " quantification:", re.findall(r"<BOA_QUANTIFICATION_VALUE[^>]*>(\d+)<", x),
          " baseline:", re.findall(r"<PROCESSING_BASELINE>([\d.]+)<", x))
    print("  cloud %:", re.findall(r"<Cloud_Coverage_Assessment>([\d.]+)<", x),
          " R10m:", sorted(n.split("_")[-2] for n in jp2 if "/R10m/" in n),
          " R20m:", sorted(n.split("_")[-2] for n in jp2 if "/R20m/" in n))
print("example path:", next(n for n in jp2 if "B04_10m" in n))
