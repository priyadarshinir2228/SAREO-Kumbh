"""Run Segment Anything (ViT-B) with point prompts on prepared tiles. Kept free of GDAL/rasterio (OpenMP conflict).
Usage: python sam_worker.py tiles.npz checkpoint out.npz
tiles.npz holds, per tile i: img_i (H x W x 3 uint8), pts_i (N x 2, x/y in pixels), lab_i (N, 1 = inside, 0 = outside)."""
import sys
import time

import numpy as np
import torch
from segment_anything import SamPredictor, sam_model_registry

data = np.load(sys.argv[1])
sam = sam_model_registry["vit_b"](checkpoint=sys.argv[2])
sam.to("cpu").eval()
pred = SamPredictor(sam)
n = len([k for k in data.files if k.startswith("img_")])
out, times = {}, []
with torch.no_grad():
    for i in range(n):
        t0 = time.time()
        pred.set_image(data[f"img_{i}"])
        masks, scores, _ = pred.predict(point_coords=data[f"pts_{i}"].astype("float32"), point_labels=data[f"lab_{i}"],
                                        multimask_output=False)
        out[f"mask_{i}"] = masks[0]
        out[f"score_{i}"] = scores[0]
        times.append(time.time() - t0)
out["seconds"] = np.array(times)
np.savez_compressed(sys.argv[3], **out)
print(f"{n} tiles, {np.sum(times):.0f} s")
