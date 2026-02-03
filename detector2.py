import json
import os
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
        with open(res_dir+JSON_FILE, "r") as f:
            data_dicts = json.load(f)
        img_infos = [ImageInfo(**d) for d in data_dicts]
        files = [res_dir+ii.file for ii in img_infos]
        scales = [ii.scale for ii in img_infos]

        with ProcessPoolExecutor() as executor:
            # Step 1: Preprocessing
            prep = list(executor.map(self._preprocess, files))
            for i, p in enumerate(prep):
                cv2.imwrite(res_dir+f"{i+1:02}"+"_prep.png", p)
            proc = list(executor.map(self._process, prep, scales))
            # for i,p in enumerate(proc):
            #     print(p.shape)
                # OUTPUT_FORMAT = ["X", "Y", "W", "H"]
                # df = pd.DataFrame(p, columns=OUTPUT_FORMAT)
                # df.to_csv(res_dir + f"{i + 1:02}_dets.csv", index=False)
            post = list(executor.map(self._postprocess, prep, proc, scales))
        for i,p in enumerate(post):
            # print(p.shape)
            OUTPUT_FORMAT = ["X", "Y", "W", "H"]
            df = pd.DataFrame(p, columns=OUTPUT_FORMAT)
            df.to_csv(res_dir + f"{i + 1:02}.csv", index=False)

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
        mser = cv2.MSER_create(min_area=ma, max_area=MA, delta=1, max_variation=2)
        _, bboxes = mser.detectRegions(img)

        if len(bboxes) == 0:
            y, x = np.unravel_index(np.argmin(img), img.shape)
            return np.asarray([[x, y, 1, 1]])
        return bboxes

    def _postprocess(self, img, detections, scale):
        valids = (detections[:, 0] >= 10) & (detections[:, 1] >= 10)
        detections= detections[valids]
        values, indices = np.unique(detections, return_index=True, axis=0)
        detections = detections[indices]
        # return detections
        binarized = np.zeros(img.shape, dtype=np.uint8)
        valids = np.zeros(detections.shape[0], dtype=np.bool)
        for i, rect in enumerate(detections):
            lx, uy, w, h = rect
            patch = img[uy:uy+h, lx:lx+w]
            if np.mean(patch) >= 220:
                valids[i] = True
                binarized[uy:uy+h, lx:lx+w] = np.where(patch >= 1, 255, 0)

        num_labels, labels, bboxes, centroids = cv2.connectedComponentsWithStats(binarized, connectivity=8)
        dets = bboxes[1:, :4]
        areas = bboxes[1:, 4]
        ma = max(1, int((self.m*scale / 2) ** 2 * np.pi))
        MA = max(1, int((self.M*scale / 2) ** 2 * np.pi))
        condition = (areas >= ma) & (areas <= MA)
        return detections[valids]

