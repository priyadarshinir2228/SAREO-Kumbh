"""Run OmniCloudMask on <in.npy> (3 x H x W: red, green, NIR reflectance) and save classes to <out.npy>.
Kept separate from GDAL/rasterio code: PyTorch's OpenMP runtime conflicts with the one loaded by the conda GDAL stack.
Usage: python ocm_worker.py in.npy out.npy model_dir"""
import sys
import time

import numpy as np
from omnicloudmask import predict_from_array

arr = np.load(sys.argv[1])
t0 = time.time()
pred = predict_from_array(arr, inference_device="cpu", destination_model_dir=sys.argv[3])
np.save(sys.argv[2], pred[0].astype("uint8"))
print(f"{time.time() - t0:.0f}")
