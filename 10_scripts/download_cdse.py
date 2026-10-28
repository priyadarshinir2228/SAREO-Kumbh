"""Download the products in 09_docs/download_manifest.csv from the Copernicus Data Space Ecosystem.

Run it yourself in a terminal (it asks for YOUR Copernicus login; nothing is stored):
    . D:\\SAREO-Kumbh\\10_scripts\\sareo_env.ps1
    & $env:SAREO_PY D:\\SAREO-Kumbh\\10_scripts\\download_cdse.py            # core products only
    & $env:SAREO_PY D:\\SAREO-Kumbh\\10_scripts\\download_cdse.py --all      # core + optional (adds ~33 GB)

Files land in 01_raw/S1 or 01_raw/S2 as <name>.zip; finished downloads are skipped on re-run,
and each completed file is appended to 09_docs/download_log.csv.
"""
import csv
import getpass
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import requests

ROOT = Path(r"D:\SAREO-Kumbh")
MANIFEST = ROOT / "09_docs" / "download_manifest.csv"
LOG = ROOT / "09_docs" / "download_log.csv"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products({id})/$value"


def get_token(user=None, password=None, refresh=None):
    data = {"client_id": "cdse-public"}
    if refresh:
        data.update(grant_type="refresh_token", refresh_token=refresh)
    else:
        data.update(grant_type="password", username=user, password=password)
    r = requests.post(TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    j = r.json()
    return j["access_token"], j.get("refresh_token")


def download_once(session, url, token, part):
    """One attempt; resumes from an existing .part file with an HTTP Range request.
    Redirects are followed by hand so the Authorization header is kept on every hop."""
    have = part.stat().st_size if part.exists() else 0
    headers = {"Authorization": f"Bearer {token}"}
    if have:
        headers["Range"] = f"bytes={have}-"
    for _ in range(5):
        r = session.get(url, headers=headers, stream=True, allow_redirects=False, timeout=120)
        if r.status_code in (301, 302, 303, 307, 308):
            url = r.headers["Location"]
            continue
        if r.status_code == 416:  # range past the end: the .part is already complete
            return
        r.raise_for_status()
        if have and r.status_code != 206:  # server ignored the range: start again
            print("  server does not support resume; restarting this file")
            have = 0
        total = have + int(r.headers.get("Content-Length", 0))
        done, t0 = have, time.time()
        with part.open("ab" if have else "wb") as f:
            for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                rate = (done - have) / 1e6 / max(time.time() - t0, 1e-3)
                print(f"\r  {done / 1e6:8.0f} / {total / 1e6:.0f} MB  ({rate:.1f} MB/s)", end="", flush=True)
        print()
        if done != total:
            raise IOError(f"incomplete: {done} of {total} bytes")
        return
    raise IOError("too many redirects")


def download(session, url, get_fresh_token, dest, attempts=10):
    part = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, attempts + 1):
        try:
            download_once(session, url, get_fresh_token(), part)
            with zipfile.ZipFile(part) as z:  # quick integrity check: readable zip with a manifest
                if not any(n.endswith("manifest.safe") for n in z.namelist()):
                    raise IOError("zip has no manifest.safe")
            part.replace(dest)
            return
        except zipfile.BadZipFile:
            print("  downloaded file is not a valid zip; deleting and retrying from scratch")
            part.unlink(missing_ok=True)
        except (requests.RequestException, IOError) as exc:
            print(f"\n  attempt {attempt}/{attempts} failed: {str(exc)[:120]}")
        time.sleep(min(10 * attempt, 60))
    raise IOError(f"giving up on {dest.name} after {attempts} attempts (re-run later to resume)")


def main():
    include_optional = "--all" in sys.argv
    with MANIFEST.open() as f:
        rows = [r for r in csv.DictReader(f) if include_optional or r["priority"] == "core"]
    print(f"{len(rows)} products, about {sum(int(r['size_mb']) for r in rows) / 1000:.1f} GB")

    user = input("Copernicus Data Space username (email): ").strip()
    token, refresh = get_token(user, getpass.getpass("Password (hidden): "))
    nonlocal_state = {"token": token, "refresh": refresh}
    session = requests.Session()

    for i, r in enumerate(rows, 1):
        dest = ROOT / r["target_folder"] / (r["name"].replace(".SAFE", "") + ".zip")
        if dest.exists():
            print(f"[{i}/{len(rows)}] skip (exists) {dest.name}")
            continue
        print(f"[{i}/{len(rows)}] {r['epoch']} {r['product_type']} {r['date']} -> {dest.name}")

        def fresh_token():  # tokens expire after ~10 min, so get a new one for every attempt
            nonlocal_state["token"], nonlocal_state["refresh"] = get_token(refresh=nonlocal_state["refresh"])
            return nonlocal_state["token"]

        try:
            download(session, DOWNLOAD_URL.format(id=r["id"]), fresh_token, dest)
        except IOError as exc:
            print(f"  SKIPPED for now: {exc}")
            continue
        with LOG.open("a", newline="") as f:
            csv.writer(f).writerow([
                r["name"], r["sensor"], r["product_type"], r["epoch"], r["date"], r["relative_orbit"], r["pass"],
                "VV+VH" if r["sensor"].startswith("S1") else "", "", "T44RNP" if r["sensor"].startswith("S2") else "",
                "", "Copernicus Data Space Ecosystem", DOWNLOAD_URL.format(id=r["id"]),
                "Copernicus Sentinel data, free and open (Copernicus licence)",
                str(dest.relative_to(ROOT)), date.today().isoformat(), r["purpose"],
            ])
    missing = [r["name"] for r in rows
               if not (ROOT / r["target_folder"] / (r["name"].replace(".SAFE", "") + ".zip")).exists()]
    print("All done." if not missing else f"{len(missing)} not finished - run the script again to resume them.")


if __name__ == "__main__":
    main()
