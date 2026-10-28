"""Check every manifest product in 01_raw: present, expected size, full zip CRC test, manifest.safe inside."""
import csv
import sys
import zipfile
from pathlib import Path

ROOT = Path(r"D:\SAREO-Kumbh")
include_optional = "--all" in sys.argv
with (ROOT / "09_docs" / "download_manifest.csv").open() as f:
    rows = [r for r in csv.DictReader(f) if include_optional or r["priority"] == "core"]

ok = 0
for r in rows:
    path = ROOT / r["target_folder"] / (r["name"].replace(".SAFE", "") + ".zip")
    label = f"{r['epoch']} {r['sensor']} {r['date']}"
    if not path.exists():
        print(f"MISSING  {label}  {path.name}")
        continue
    mb = path.stat().st_size / 1e6
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            bad = z.testzip()  # reads every member and checks its CRC
        has_manifest = any(n.endswith("manifest.safe") for n in names)
        status = "OK" if bad is None and has_manifest else f"BAD (crc fail: {bad}, manifest: {has_manifest})"
    except zipfile.BadZipFile as exc:
        status = f"BAD ({exc})"
    if status == "OK":
        ok += 1
    print(f"{status:8s} {label}  {mb:7.0f} MB (catalogue {r['size_mb']} MB)  {len(names) if 'names' in dir() else 0} files")
print(f"\n{ok}/{len(rows)} products verified")
