import os
import time
import tkinter
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
import cv2
import numpy as np
import tifffile
import xml.etree.ElementTree as XML_parser

from postprocessing import postprocess
from preprocessing import preprocess

NM_PXL = 64
OFFSET = 55
DET_FILE = "_dets.csv"
ALL_DETS = "all_dets.csv"
DELTA = 1
MAX_VAR = 100

def process_sample(src, out, m, M):

    experiment = (os.path.basename(src)).split(".")[-1]
    # print(f"Processing {experiment} directory")
    src = src + "/"
    out = out + "/" + experiment + "/"
    os.makedirs(out, exist_ok=True)
    files = [x for x in os.listdir(src) if x.endswith(".tif")]
    paths = [src + x for x in files]
    scales = [_parse_scale(x) for x in paths]
    process = sorted(list(zip(paths, scales)), key=lambda x: x[1])
    total = len(process)
    ma = ((NM_PXL * m) / 2) ** 2 * np.pi
    MA = ((NM_PXL * M) / 2) ** 2 * np.pi

    start = time.time()
    with ProcessPoolExecutor() as executor:
        prep = list(executor.map(preprocess, process))
        sp_end = time.time()
        mser_args = ((img, scale, ma, MA) for (img, scale, _) in prep)

        results = list(executor.map(_mser_process, mser_args))
        pr_end = time.time()
        post_args = (
            (p[0], p[1], r, p[2], f"{out}{idx}")
            for idx, (p, r) in enumerate(zip(prep, results))
        )
        lengths = list(executor.map(postprocess, post_args))

    all_lengths = np.concatenate(lengths)
    df = pd.DataFrame(all_lengths, columns=["Lengths"])
    df.to_csv(out+"all_dets.csv", index=False)

    end = time.time()
    print(f"It took {end - start:.3f} and {total} files were processed.")
    print(f"Total detections: {len(all_lengths)}")
    print(f"Preprocessing:  {sp_end - start}")
    print(f"Processing:     {pr_end - sp_end:.3f}")
    print(f"Postprocessing: {end - pr_end:.3f}")

    # return end - start, sp_end - start, pr_end - sp_end, end - pr_end, len(lengths)

def _parse_scale(path):
    if path.endswith(".tif"):
        with tifffile.TiffFile(path) as tif:
            text = tif.pages.first.tags["ImageDescription"].value
            cut = XML_parser.fromstring(text).find('.//DrawObject')
            x = float(cut.find('.//Location//X').text)
            w = float(cut.find('.//ImageSize//Width').text)
            unit = cut.find('.//MicronbarMeasureUint').text
            nm = float(cut.find('.//MicronbarValue').text)
            if unit == 'Micrometer': nm *= 1000
            nm_pxl = (w - x - OFFSET) / nm
            scale = NM_PXL / nm_pxl
            return scale
    raise Exception(f"{path} is not a tif file")

def _mser_process(args):
    img, scale, ma, MA = args
    den = 1/(scale**2)
    ma = max(1, int(ma*den))
    MA = max(1, int(MA*den))
    mser = cv2.MSER_create(min_area=ma, max_area=MA, delta=DELTA, max_variation=MAX_VAR)
    _, bboxes = mser.detectRegions(img)
    # fallback detection if nothing is detected
    if len(bboxes) == 0:
        y, x = np.unravel_index(np.argmin(img), img.shape)
        return np.asarray([[x, y, 1, 1]])
    return bboxes
