import json
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict

import cv2
import numpy as np
import tifffile
import xml.etree.ElementTree as XML_parser

from debugpy.launcher.debuggee import process

OFFSET = 55
U8_MAX = 255
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
        # print(dest)
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
        result = result.astype(dtype=np.float32)
        mmax = np.max(result)
        mmin = np.min(result)
        return (((result - mmin) / max(1, (mmax - mmin))) * U8_MAX).astype(dtype=np.uint8)



ro = ResultOrganizer()
ro.organize("C:\\Users\\vsado\\Downloads\\Git\\Detector\\data\\6768\\","C:\\Users\\vsado\\Downloads\\Git\\Detector\\results\\6768\\")


class ClusterDetector:
    @classmethod
    def process_sample(cls, res_dir, m, M):
        with open(res_dir+JSON_FILE, "r") as f:
            data_dicts = json.load(f)
        img_infos = [ImageInfo(**d) for d in data_dicts]
        files = [res_dir+ii.file for ii in img_infos]
        scales = [ii.scale for ii in img_infos]

        # process_list = zip(files, scales)
        for f in files:
            x = cls._preprocess(f)
            cv2.imwrite(f+"_d.png", x)

        # with ProcessPoolExecutor() as executor:
        #     # Step 1: Preprocessing
        #     prep = list(executor.map(cls._preprocess, process_list))
        #
        #     # Step 2: MSER Detection
        #     mser_args = ((img, scale, m, M) for (img, scale, _) in prep)
        #     results = list(executor.map(self._mser_process, mser_args))
        #
        #     # Step 3: Postprocessing
        #     # We generate unique CSV names based on index to avoid collision
        #     post_args = (
        #         (p[0], p[1], r, p[2], f"{out_dir}{idx}")
        #         for idx, (p, r) in enumerate(zip(prep, results))
        #     )
        #     lengths = list(executor.map(self.postprocess, post_args))
    @staticmethod
    def _preprocess(f):
        img = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        # denoised = cv2.GaussianBlur(img, (3,3), 0)
        denoised = cv2.bilateralFilter(img, 2, 25, 50)
        print(img.shape)
        return denoised


cd = ClusterDetector()
cd.process_sample("C:\\Users\\vsado\\Downloads\\Git\\Detector\\results\\6768\\", 1, 2)