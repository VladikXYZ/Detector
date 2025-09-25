import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import tifffile
import xml.etree.ElementTree as XML_parser
from preprocessing import preprocess

NM_PXL = 64
OFFSET = 55
DET_FILE = "_dets.csv"
ALL_DETS = "all_dets.csv"

class RedirectStdout:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert("end", s)
        self.text_widget.see("end")

    def last_line(self):
        return int(self.text_widget.index('end-1c').split('.')[0])

    def delete_line(self, index):
        self.text_widget.delete(f"{index}.0", f"{index+1}.0")

    def flush(self):
        pass
def process_sample(src_dir, res_dir, stdout, verbose=False):
    src_dir = src_dir+"/"
    if not os.path.exists(src_dir):
        raise Exception(f"Invalid source directory: {src_dir}")
    res_dir = res_dir+"/"
    os.makedirs(res_dir, exist_ok=True)
    files = [x for x in os.listdir(src_dir) if x.endswith(".tif")]
    paths = [src_dir + x for x in files]
    scales = [_parse_scale(x) for x in paths]
    process = sorted(list(zip(paths, scales)), key=lambda x: x[1])
    prep = []
    start = time.time()
    total = len(process)
    last_line = stdout.last_line()
    print(f"Preprocessing progress: {0}/{total}")

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(preprocess, p) for p in process]
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            stdout.delete_line(last_line)
            print(f"Preprocessing progress: {completed}/{total}")
            prep.append(result)
    sp_end = time.time()

    # results = []
    # with ProcessPoolExecutor() as executor:
    #     futures = [executor.submit(mser_process, p) for p in prep]
    #     completed = 0
    #     for future in as_completed(futures):
    #         result = future.result()
    #         completed += 1
    #         stdout.delete_line(last_line)
    #         print(f"Preprocessing progress: {completed}/{total}")
    #         results.append(result)


    pr_end = time.time()

    # print(f"It took {end - start:.3f} and {len(process)} files were processed.")
    # print(f"Total detections: {len(experiment)}")
    print(f"Preprocessing:  {sp_end - start}")
    # print(f"Processing:     {pr_end - sp_end:.3f}")
    # print(f"Postprocessing: {end - pr_end:.3f}")


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

# def mser_process(args):
#     img, scale = args
#     mina = max(1, int(MIN_AREA / (scale ** 2)))
#     maxa= max(1, int(MAX_AREA / (scale ** 2)))
#     mser = cv2.MSER_create(min_area=mina, max_area=maxa,
#                            delta=DELTA, max_variation=MAX_VAR)
#     _, bboxes = mser.detectRegions(img)
#     # fallback detection if nothing is detected
#     if len(bboxes) == 0:
#         y, x = np.unravel_index(np.argmin(img), img.shape)
#         return np.asarray([[x, y, 1, 1]])
#     return bboxes
