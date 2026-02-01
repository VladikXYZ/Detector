import os
import time
import shutil
import json
import numpy as np
import pandas as pd
import cv2
import tifffile
import xml.etree.ElementTree as XML_parser
from concurrent.futures import ProcessPoolExecutor

# --- CONSTANTS ---
NM_PXL = 64  # default scale factor (64 pixels = 1 nm)
OUTPUT_FORMAT = ["LX", "UY", "RX", "BY", "Length"]

# Preprocessing constants
CLAHE_LIM = 2.5
KERNEL = (5, 5)
U8_MAX = 255

# Postprocessing constants
ABOVE_AI_TH = 0.5
# MIN_LENGTH_TH = 1

# Detection constants
OFFSET = 55
DET_FILE = "_dets.csv"
ALL_DETS = "all_dets.csv"
DELTA = 1
MAX_VAR = 100


class ClusterDetector:
    """
    Main class for detecting clusters in TEM images.
    Encapsulates the pipeline steps: Preprocessing -> MSER -> Postprocessing.
    """

    def process_sample(self, src, out, m, M):
        """
        Main entry point to process a directory of images.
        Copies images to output, processes them, and generates a JSON result map.
        """
        experiment = (os.path.basename(src)).split(".")[-1]
        if not src.endswith("/"): src = src + "/"
        if not out.endswith("/"): out = out + "/"

        # Create experiment output sub-folder
        out_dir = out + experiment + "/"
        os.makedirs(out_dir, exist_ok=True)

        # Prepare file list
        files = [x for x in os.listdir(src) if x.endswith(".tif")]
        paths = [src + x for x in files]
        scales = [_parse_scale(x) for x in paths]

        # process list: [(full_path, scale), ...] sorted by scale
        process_list = sorted(list(zip(paths, scales)), key=lambda x: x[1])
        total = len(process_list)

        # Copy images to the result folder
        print("Copying files to output directory...")
        output_filenames = []
        for p, s in process_list:
            fname = os.path.basename(p)
            dst = os.path.join(out_dir, fname)
            shutil.copy2(p, dst)
            output_filenames.append(fname)

        # Calculate area constraints
        # ma = ((NM_PXL * m) / 2) ** 2 * np.pi
        # MA = ((NM_PXL * M) / 2) ** 2 * np.pi

        start = time.time()

        # Use a single executor for the whole pipeline
        with ProcessPoolExecutor() as executor:
            # Step 1: Preprocessing
            prep = list(executor.map(self.preprocess, process_list))
            sp_end = time.time()

            # Step 2: MSER Detection
            mser_args = ((img, scale, m, M) for (img, scale, _) in prep)
            results = list(executor.map(self._mser_process, mser_args))
            pr_end = time.time()

            # Step 3: Postprocessing
            # We generate unique CSV names based on index to avoid collision
            post_args = (
                (p[0], p[1], r, p[2], f"{out_dir}{idx}")
                for idx, (p, r) in enumerate(zip(prep, results))
            )
            lengths = list(executor.map(self.postprocess, post_args))

        # Save aggregated results CSV
        all_lengths = np.concatenate(lengths)
        df = pd.DataFrame(all_lengths, columns=["Lengths"])
        df.to_csv(out_dir + "all_dets.csv", index=False)

        # --- Create JSON Result Structure ---
        json_results = []
        for idx, (path_info, length_arr) in enumerate(zip(process_list, lengths)):
            # path_info is (original_full_path, scale)
            # length_arr is the numpy array of detection lengths

            entry = {
                "id": idx,
                "filename": output_filenames[idx],
                "scale": path_info[1],
                "detections_count": len(length_arr),
                "detections_csv_file": f"{idx}_dets.csv",
                "selected_pixels_file": None  # Placeholder for future app
            }
            json_results.append(entry)

        # Save JSON to file
        json_path = os.path.join(out_dir, "results.json")
        with open(json_path, "w") as f:
            json.dump(json_results, f, indent=4)

        end = time.time()
        print(f"It took {end - start:.3f} s. Processed {total} files.")
        print(f"Results saved to: {json_path}")
        print(f"Total detections: {len(all_lengths)}")
        print(f"Preprocessing:  {sp_end - start:.3f} s")
        print(f"Processing:     {pr_end - sp_end:.3f} s")
        print(f"Postprocessing: {end - pr_end:.3f} s")

    # --- Pipeline Steps (Inside Class) ---

    @staticmethod
    def preprocess(args) -> tuple:
        """
        Applies scaling, blurring, CLAHE, inversion and Otsu thresholding.
        """
        f, scale = args
        img = load_uint(f)
        img = scaled_blur(img, 1, cv2.INTER_LINEAR)
        img = clahe(img)
        img = invert(img)
        inv, bth = otsu(img)
        return (inv, scale, bth)

    @staticmethod
    def _mser_process(args):
        """
        Runs MSER algorithm to find regions.
        """
        img, scale, m, M = args
        ma = (m / 2) ** 2 * np.pi
        MA = (M / 2) ** 2 * np.pi
        # den = 1 / (scale ** 2)
        ma = max(1, int(ma))
        MA = max(1, int(MA))
        mser = cv2.MSER_create(min_area=ma, max_area=MA, delta=DELTA, max_variation=MAX_VAR)
        _, bboxes = mser.detectRegions(img)

        if len(bboxes) == 0:
            y, x = np.unravel_index(np.argmin(img), img.shape)
            return np.asarray([[x, y, 1, 1]])
        return bboxes

    @staticmethod
    def postprocess(args) -> np.ndarray:
        """
        Converts bounding boxes, filters them, and calculates real-world size.
        """
        img, scale, detections, bth, to_write = args
        rects = bboxes_to_rects(detections)
        rects = remove_invalid(rects)
        rects = size_filtering(rects, scale)
        rects = intensity_filtering(img, rects, bth)
        rects = merge_overlapping(img, rects, bth)
        rects = size_filtering(rects, scale)

        ws = rects[:, 2] - rects[:, 0]
        hs = rects[:, 3] - rects[:, 1]

        lengths = np.sqrt(ws * ws + hs * hs) * scale
        lengths = lengths.astype(dtype=np.float32)
        lengths = lengths.reshape((ws.shape[0], 1))

        all_data = np.concatenate((rects, lengths), axis=1)
        df = pd.DataFrame(all_data, columns=OUTPUT_FORMAT)
        df.to_csv(to_write + "_dets.csv", index=False)
        return lengths


# --- Helper Functions (Outside Class) ---

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
    raise Exception(f"{path} is not a tif file")


def load_uint(path: str):
    result = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if result is None:
        raise Exception(f"Cannot found file: {path}")
    result = result.astype(dtype=np.float32)
    mmax = np.max(result)
    mmin = np.min(result)
    return (((result - mmin) / max(1, (mmax - mmin))) * U8_MAX).astype(dtype=np.uint8)


def scale_image(img, scale, inter=cv2.INTER_NEAREST):
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=inter)


def scaled_blur(img, scale, inter=cv2.INTER_NEAREST):
    img = scale_image(img, scale, inter)
    img = cv2.blur(img, KERNEL)
    return scale_image(img, 1 / scale, inter)


def otsu(img):
    if img.dtype == np.uint8:
        th, mask = cv2.threshold(img, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = mask * img
        bth = result.sum() / mask.sum()
        return result, bth
    raise Exception(f"Unknown dtype = {img.dtype}")


def invert(img):
    if img.dtype == np.uint8:
        return U8_MAX - img
    raise Exception(f"Unknown dtype = {img.dtype}")


def clahe(img):
    if img.dtype == np.uint8:
        clahe_obj = cv2.createCLAHE(clipLimit=CLAHE_LIM)
        return clahe_obj.apply(img.astype(dtype=np.uint8))
    raise Exception(f"Unknown dtype = {img.dtype}")


def bboxes_to_rects(bboxes) -> np.ndarray:
    lx = bboxes[:, 0]
    uy = bboxes[:, 1]
    hs = bboxes[:, 3]
    ws = bboxes[:, 2]
    rx = lx + ws
    by = uy + hs
    rects = np.stack((lx, uy, rx, by), axis=1, dtype=np.int32)
    return rects


def remove_invalid(rects):
    valid = (rects[:, 0] != rects[:, 2]) & (rects[:, 1] != rects[:, 3])
    rects = rects[valid]
    values, indices = np.unique(rects, return_index=True, axis=0)
    indices.sort()
    rects = rects[indices]
    return rects


def intensity_filtering(img, rects, avg_intensity):
    above_bth = np.ones(len(rects), dtype=np.float32)
    for i, rect in enumerate(rects):
        lx, uy, rx, by = rect
        patch = img[uy:by, lx:rx]
        if patch.size == 0:
            pass
        else:
            above_bth[i] = (patch >= avg_intensity).sum() / patch.size
    return rects[(above_bth >= ABOVE_AI_TH)]


def merge_overlapping(img, rects, bth):
    binarized = np.zeros(img.shape, dtype=np.uint8)
    for rect in rects:
        lx, uy, rx, by = rect
        patch = img[uy:by, lx:rx]
        binarized[uy:by, lx:rx] = np.where(patch >= bth, 255, 0)

    num_labels, labels, bboxes, centroids = cv2.connectedComponentsWithStats(binarized, connectivity=8)
    return bboxes_to_rects(bboxes[1:, :4])


def size_filtering(rects, scale):
    ws = rects[:, 2] - rects[:, 0]
    hs = rects[:, 3] - rects[:, 1]
    length = np.sqrt((ws * ws) + (hs * hs))
    valid = np.where(length >= scale, True, False)
    return rects[valid]