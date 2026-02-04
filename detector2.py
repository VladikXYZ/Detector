import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict

import cv2
import numpy as np
import pandas as pd
import tifffile
import xml.etree.ElementTree as XML_parser

OFFSET = 55
U8_MAX = 255
GAMMA = 0.5
CLAHE_LIM = 2.5
JSON_FILE = "metadata.json"


@dataclass
class ImageInfo:
    file: str
    scale: float   # nm/pixel
    org_file: str  # Original filename

    # Helper to load from JSON
    @staticmethod
    def from_dict(d):
        return ImageInfo(**d)


class ResultOrganizer:
    @classmethod
    def organize(cls, src, dest):
        files = [x for x in os.listdir(src) if x.endswith(".tif")]
        scales = [cls._parse_scale(src+f) for f in files]
        pngs = [cls._convert_tif(src+f) for f in files]
        comp_params = [cv2.IMWRITE_PNG_COMPRESSION, 1]

        json_info = []
        for i, (scale, png, file) in enumerate(zip(scales, pngs, files)):
            file_name = f"{i+1:02}.png"
            new_info = ImageInfo(file_name, scale, file)
            json_info.append(asdict(new_info))
            cv2.imwrite(dest+file_name, png, comp_params)

        json.dump(json_info, open(dest+JSON_FILE, "w"),indent=1)

    @staticmethod
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
                # scale = NM_PXL / nm_pxl
                return nm_pxl
        raise Exception(f"{path} is not a .tif file")

    @staticmethod
    def _convert_tif(path):
        result = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if result is None:
            raise Exception(f"Cannot found file: {path}")
        mmin, mmax = np.percentile(result, (0.1, 99.9))
        result = result.astype(dtype=np.float32)
        np.clip(result, mmin, mmax, out=result)

        return (((result - mmin) / max(1, (mmax - mmin))) * U8_MAX).astype(dtype=np.uint8)


class ClusterDetector:

    def process_sample(self, res_dir, m, M):
        self.m = m
        self.M = M

        # 1. Start Total Timer
        total_start_time = time.time()

        with open(res_dir + JSON_FILE, "r") as f:
            data_dicts = json.load(f)
        img_infos = [ImageInfo(**d) for d in data_dicts]
        files = [res_dir + ii.file for ii in img_infos]
        scales = [ii.scale for ii in img_infos]

        cv2.setNumThreads(1)  # Good practice for multiprocessing

        with ProcessPoolExecutor() as executor:
            # --- Preprocessing ---
            print("Starting Preprocessing...")
            t0 = time.time()
            prep = list(executor.map(self._preprocess, files))
            t_prep = time.time() - t0
            print(f"Preprocessing done: {t_prep:.2f} seconds")

            # Save debug images (Optional to time this, but usually fast)
            for i, p in enumerate(prep):
                cv2.imwrite(res_dir + f"{i + 1:02}" + "_prep.png", p)

            # --- Processing (MSER) ---
            print("Starting Processing...")
            t0 = time.time()
            proc = list(executor.map(self._process, prep, scales))
            t_proc = time.time() - t0
            print(f"Processing done: {t_proc:.2f} seconds")
            # --- Postprocessing (Filtering/Cleaning) ---
            print("Starting Postprocessing...")
            t0 = time.time()
            # Note: Ensure _postprocess accepts (prep, proc, scales) arguments correctly
            post = list(executor.map(self._postprocess, prep, proc, scales, range(len(scales))))
            t_post = time.time() - t0
            t_post = time.time() - t0
            print(f"Postprocessing done: {t_post:.2f} seconds")

        # --- Saving Results ---
        print("Saving CSVs...")
        t0 = time.time()
        for i, p in enumerate(post):
            OUTPUT_FORMAT = ["x", "y", "w", "h"]  # Use lowercase to match standard
            df = pd.DataFrame(p, columns=OUTPUT_FORMAT)
            df.to_csv(res_dir + f"{i + 1:02}.csv", index=False)
        t_save = time.time() - t0
        print(f"Saving done: {t_save:.2f} seconds")

        # --- Final Report ---
        total_time = time.time() - total_start_time
        print("-" * 30)
        print(f"PIPELINE SUMMARY")
        print(f"Preprocessing:  {t_prep:6.2f}s")
        print(f"Processing:     {t_proc:6.2f}s")
        print(f"Postprocessing: {t_post:6.2f}s")
        print(f"Saving:         {t_save:6.2f}s")
        print(f"TOTAL TIME:     {total_time:6.2f}s")
        print("-" * 30)

    @staticmethod
    def _preprocess(f):
        img = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        denoised = cv2.bilateralFilter(img, 2, 25, 30)
        clahe_obj = cv2.createCLAHE(clipLimit=CLAHE_LIM)
        clahed =  clahe_obj.apply(denoised.astype(dtype=np.uint8))
        inverted = U8_MAX - denoised
        th, mask = cv2.threshold(inverted, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = mask * inverted
        return result

    def _process(self, img, scale):
        ma = max(1, int((self.m*scale / 2) ** 2 * np.pi))
        MA = max(1, int((self.M*scale / 2) ** 2 * np.pi))
        mser = cv2.MSER_create(min_area=ma, max_area=MA, delta=1, max_variation=1.5)
        locs, bboxes = mser.detectRegions(img)

        if len(bboxes) == 0:
            return np.asarray([[0, 0, 1, 1]]), [[[0,0]]]
        return bboxes, np.asarray(locs, dtype=object)

    def _postprocess(self, img, processed, scale, idx):
        lx, uy = 5, 5
        rx, by = img.shape[1] - lx, img.shape[0] - uy
        detections, locs = processed
        rxs = detections[:, 0] + detections[:, 2]
        bys = detections[:, 1] + detections[:, 3]
        valids = (rxs <= rx) & (bys <= by) & (detections[:, 0] >= lx) & (detections[:, 1] >= uy)

        detections= detections[valids]
        locs = locs[valids]
        values, indices = np.unique(detections, return_index=True, axis=0)
        detections = detections[indices]
        locs = locs[indices]
        valids = np.zeros(detections.shape[0], dtype=np.bool)
        for i, rect in enumerate(detections):
            lx, uy, w, h = rect
            if (max(w/h, h/w) <= 1.5):
                patch = img[uy:uy+h, lx:lx+w]
                # valids[i] = True
                valids[i] = shape_filter(patch)
            else: valids[i] = False
        detections = detections[valids]
        locs = locs[valids]
        binarized = np.zeros(img.shape, dtype=np.uint8)
        for loc in locs:
            xs = loc[:, 0]
            ys = loc[:, 1]

            # Set those pixels to white
            binarized[ys, xs] = 255
            # break

        # print(binarized)
        cv2.imwrite(f"binarized{idx}.png", binarized)
        # return binarized, locs
        num_labels, labels, bboxes, centroids = cv2.connectedComponentsWithStats(binarized, connectivity=8)
        detections = bboxes[1:, :4]
        areas = bboxes[1:, 4]
        ma = max(1, int((self.m*scale / 2) ** 2 * np.pi))
        MA = max(1, int((self.M*scale / 2) ** 2 * np.pi))
        condition = (areas >= ma) & (areas <= MA)
        detections = detections[condition]
        return detections

def shape_filter(patch, threshold = 0.6):
    ph, pw = patch.shape
    # 2. Generate Gaussian Template (Thesis Logic)
    # We calculate this fresh for every single box
    cx, cy = pw // 2, ph // 2
    sx, sy = pw / 3.0, ph / 3.0  # Sigma is 1/3 of the size

    # Create the grid
    mx, my = np.meshgrid(np.arange(pw) - cx, np.arange(ph) - cy)

    # Calculate Gaussian formula
    gaussian = np.exp(-(mx ** 2 / (2 * sx ** 2) + my ** 2 / (2 * sy ** 2)))

    # 3. Prepare for Correlation (Zero-Center & Normalize)
    # Flatten arrays to 1D vectors
    p_vec = patch.flatten().astype(np.float32)
    g_vec = gaussian.flatten()

    # Subtract Mean (This removes "brightness" so we only check SHAPE)
    p_vec = p_vec - np.mean(p_vec)
    g_vec = g_vec - np.mean(g_vec)

    # Calculate Vector Magnitude (Norm)
    p_norm = np.linalg.norm(p_vec)
    g_norm = np.linalg.norm(g_vec)

    # 4. Calculate Correlation Score (Cosine Similarity)
    # Formula: (A . B) / (|A| * |B|)
    score = np.dot(p_vec, g_vec) / (p_norm * g_norm)

    # 5. Filter
    return score >= threshold
