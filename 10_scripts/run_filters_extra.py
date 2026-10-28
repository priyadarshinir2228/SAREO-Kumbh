"""Phase 6 extra filters, all ending on the same AOI grid as the SNAP filters:

  kuan3/5/7   OTB Despeckle (Kuan, radius 1/2/3, 4 looks) in radar geometry -> injected into a copy of the
              T1 subset -> SNAP 'None' filter + terrain correction (S1_filter_tc.xml) -> crop
  sar2sar     deepdespeckling SAR2SAR (Sentinel-1 GRD weights) on amplitude in radar geometry -> same route
  mt_quegan   Quegan & Yu (2001) multi-temporal filter on the three T1 dates (Phase 5 terrain-corrected linear
              rasters, 5x5 local means): J_k = <I_k>/N * sum_i I_i/<I_i>

Usage: python run_filters_extra.py [kuan] [sar2sar] [mt]   (no argument = all)
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

ROOT = Path(r"D:\SAREO-Kumbh")
OUT = ROOT / "03_enhanced" / "S1_filters"
WORK = OUT / "work"
BASE = WORK / "T1_cal_subset"
GPT = r"D:\esa-snap\bin\gpt.exe"
OTB_CLI = r"D:\OTB\bin\otbApplicationLauncherCommandLine.exe"
PY = sys.executable
BANDS = ["Sigma0_VH", "Sigma0_VV"]
K_AMP = 500.0  # scale sigma0 to a GRD-like amplitude range for SAR2SAR: A = K * sqrt(sigma0)
steps = set(sys.argv[1:]) or {"kuan", "sar2sar", "mt"}
timing = []


def read_envi(dim_dir, band):
    with rasterio.open(dim_dir / f"{band}.img") as src:
        return src.read(1).astype("float64")


def inject(tag, arrays):
    """Copy the T1 subset product and overwrite its band files with filtered sigma0 (linear)."""
    dst = WORK / f"T1_{tag}_subset"
    shutil.copy(BASE.with_suffix(".dim"), dst.with_suffix(".dim"))
    data_dir = dst.with_suffix(".data")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(BASE.with_suffix(".data"), data_dir)
    # the .dim references the .data folder by name -> rewrite it
    dim = dst.with_suffix(".dim")
    dim.write_text(dim.read_text().replace("T1_cal_subset.data", data_dir.name))
    for band, arr in arrays.items():
        with rasterio.open(data_dir / f"{band}.img", "r+") as ds:
            ds.write(np.nan_to_num(arr, nan=0.0).astype("float32"), 1)
    return dim


def terrain_correct(tag, dim):
    tc = WORK / f"T1_{tag}_tc"
    subprocess.run([GPT, str(ROOT / "09_docs" / "snap_graphs" / "S1_filter_tc.xml"), f"-Pinput={dim}",
                    "-Pfilter=None", "-Psize=3", "-PlsWindow=7x7", "-Penl=4.4", "-Plooks=4", f"-Poutput={tc}",
                    "-q", "8", "-c", "4G"],
                   check=True, capture_output=True)
    subprocess.run([PY, "-I", str(ROOT / "10_scripts" / "finalize_s1.py"), f"{tc}.tif", str(OUT / f"T1_{tag}_lin.tif")],
                   check=True, capture_output=True)
    Path(f"{tc}.tif").unlink()
    shutil.rmtree(dim.with_suffix(".data"))
    dim.unlink()


if "kuan" in steps:
    for rad in (1, 2, 3):
        tag = f"kuan{2 * rad + 1}"
        if (OUT / f"T1_{tag}_lin.tif").exists():
            continue
        t0 = time.time()
        arrays = {}
        for band in BANDS:
            src = BASE.with_suffix(".data") / f"{band}.img"
            tmp = WORK / f"{tag}_{band}.tif"
            subprocess.run([OTB_CLI, "Despeckle", r"D:\OTB\lib\otb\applications", "-in", str(src), "-out", str(tmp), "float",
                            "-filter", "kuan", "-filter.kuan.rad", str(rad), "-filter.kuan.nblooks", "4"],
                           check=True, capture_output=True)
            with rasterio.open(tmp) as ds:
                arrays[band] = ds.read(1)
            tmp.unlink()
        terrain_correct(tag, inject(tag, arrays))
        timing.append((tag, round(time.time() - t0)))
        print(tag, "done", timing[-1][1], "s")

if "sar2sar" in steps and not (OUT / "T1_sar2sar_lin.tif").exists():
    import torch
    from deepdespeckling.sar2sar.sar2sar_denoiser import Sar2SarDenoiser
    # PyTorch >= 2.6 loads weights with weights_only=True; the SAR2SAR checkpoint stores numpy scalars, so allow
    # exactly those types (keeps the safe loader instead of disabling it)
    torch.serialization.add_safe_globals([(np._core.multiarray.scalar, "numpy.core.multiarray.scalar"), np.dtype,
                                          type(np.dtype("float64")),
                                          type(np.dtype("float32")), type(np.dtype("int64"))])
    t0 = time.time()
    den = Sar2SarDenoiser()
    arrays = {}
    for band in BANDS:
        s0 = read_envi(BASE.with_suffix(".data"), band)
        valid = s0 > 0
        amp = K_AMP * np.sqrt(np.clip(s0, 1e-6, None))
        h, w = amp.shape
        res = den.denoise_image(amp, patch_size=256, stride_size=64)["denoised"]
        s0_hat = (res[:h, :w] / K_AMP) ** 2
        s0_hat[~valid] = 0
        arrays[band] = s0_hat
        print(band, "sar2sar median ratio filtered/original:", float(np.median(s0_hat[valid] / s0[valid])))
    terrain_correct("sar2sar", inject("sar2sar", arrays))
    timing.append(("sar2sar", round(time.time() - t0)))
    print("sar2sar done", timing[-1][1], "s")

if "mt" in steps and not (OUT / "T1_mtquegan_lin.tif").exists():
    t0 = time.time()
    dates = ["20250123", "20250204", "20250216"]  # target = last (T1)
    srcs = [rasterio.open(ROOT / "02_preproc" / "S1" / f"S1A_{d}_Sig0_nofilter_lin.tif") for d in dates]
    profile = srcs[-1].profile
    out = np.zeros((2,) + srcs[-1].shape, dtype="float32")
    for b in (1, 2):
        stack = [np.nan_to_num(s.read(b).astype("float64"), nan=0.0) for s in srcs]
        means = [uniform_filter(a, 5) for a in stack]
        ratio = sum(a / np.where(m > 0, m, np.nan) for a, m in zip(stack, means)) / len(stack)
        out[b - 1] = (means[-1] * ratio).astype("float32")
        out[b - 1][~np.isfinite(out[b - 1]) | (stack[-1] == 0)] = np.nan
    with rasterio.open(OUT / "T1_mtquegan_lin.tif", "w", **profile) as dst:
        dst.write(out)
        for i, name in enumerate(BANDS, 1):
            dst.set_band_description(i, name)
    for s in srcs:
        s.close()
    timing.append(("mtquegan", round(time.time() - t0)))
    print("mt_quegan done", timing[-1][1], "s")

with (OUT / "extra_filter_timing.csv").open("a") as f:
    for tag, sec in timing:
        f.write(f"{tag},{sec}\n")
