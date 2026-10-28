"""Print versions of every package the SAREO-Kumbh workflow needs."""
import importlib
import sys

PACKAGES = [
    ("osgeo.gdal", "GDAL"),
    ("rasterio", "rasterio"),
    ("geopandas", "geopandas"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("skimage", "scikit-image"),
    ("sklearn", "scikit-learn"),
    ("arosics", "arosics"),
    ("torch", "PyTorch"),
    ("omnicloudmask", "OmniCloudMask"),
    ("deepdespeckling", "deepdespeckling"),
]

print(f"Python {sys.version.split()[0]} at {sys.executable}")
missing = []
for module, name in PACKAGES:
    try:
        mod = importlib.import_module(module)
        version = getattr(mod, "__version__", None) or getattr(mod, "VersionInfo", lambda: "?")()
        print(f"  OK   {name:16s} {version}")
    except Exception as exc:  # report and keep going
        print(f"  MISS {name:16s} {type(exc).__name__}: {exc}")
        missing.append(name)

print("All packages present." if not missing else f"Missing: {', '.join(missing)}")
