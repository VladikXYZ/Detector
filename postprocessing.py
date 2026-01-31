import cv2
import numpy as np
import pandas as pd

ABOVE_AI_TH = 0.5
MIN_LENGTH_TH = 1
from config import NM_PXL, OUTPUT_FORMAT

# postprocess (and merge patches)
def postprocess(args) -> np.ndarray:
    """
    Method for converting and postprocessing detections

    :param args: image for filtering, scale of image,
        detections from patches,
        average intensity in foreground, where to write results
        and if detections are circles
    :type args: tuple[np.ndarray, float, np.ndarray, str, bool]
    :return: np.ndarray
    """
    img, scale, detections, bth, to_write = args
    # it is output in circles, it will be converted to rectangles
    rects = bboxes_to_rects(detections)
    # removing rectangles which are same or has zero area
    rects = remove_invalid(rects)
    # removing small detections
    rects = size_filtering(rects, scale)
    # removing rectangles with to many dark pixels
    rects = intensity_filtering(img, rects, bth)
    # removing detections with blob not alike shape
    # rects = shape_filtering(img, rects, bth)
    # removing overlapping rectangles
    rects = merge_overlapping(img, rects, bth)
    # removing small detections that could
    # emerge from merging overlapping
    rects = size_filtering(rects, scale)
    ws = rects[:, 2] - rects[:, 0]
    hs = rects[:, 3] - rects[:, 1]
    # converting length to nanometers
    rescale = scale / NM_PXL
    lengths = np.sqrt(ws * ws + hs * hs) * rescale
    lengths = lengths.astype(dtype=np.float32)
    lengths =  lengths.reshape((ws.shape[0], 1))
    # writing into config specified file
    all_data = np.concatenate((rects, lengths), axis=1)
    df = pd.DataFrame(all_data, columns=OUTPUT_FORMAT)
    df.to_csv(to_write+"_dets.csv", index=False)
    return lengths

# converting circles to squares
# def circles_to_rects(circles, max_dims) -> np.ndarray:
#     cy, cx, rs = circles[:, 0], circles[:, 1], circles[:, 2]
#     lx = (cx - rs).astype(dtype=np.int32)
#     uy = (cy - rs).astype(dtype=np.int32)
#     a = (2 * rs).astype(dtype=np.int32)
#     rx = lx + a
#     by = uy + a
#     lx = np.where(lx <= 0, 0, lx)
#     uy = np.where(uy <= 0, 0, uy)
#
#     maxy, maxx = max_dims
#     rx = np.where(rx >= maxx, maxx, rx)
#     by = np.where(by >= maxy, maxy, by)
#     merged = np.stack((lx, uy, rx, by), dtype=np.int32, axis=1)
#     return merged

# converting bounding boxes to rectangles
# (defined by left upper corner and right bottom corner)
def bboxes_to_rects(bboxes) -> np.ndarray:
    lx = bboxes[:, 0]
    uy = bboxes[:, 1]
    hs = bboxes[:, 3]
    ws = bboxes[:, 2]

    rx = lx + ws
    by = uy + hs
    rects = np.stack((lx, uy, rx, by), axis=1, dtype=np.int32)
    return rects

# removing same and zero area rectangles
def remove_invalid(rects):
    valid = (rects[:, 0] != rects[:, 2]) & (rects[:, 1] != rects[:, 3])
    rects =  rects[valid]
    values, indices = np.unique(rects, return_index=True, axis=0)
    indices.sort()
    rects = rects[indices]
    return rects

# removing detections with too many dark pixels
# (pixels below average intensity of foreground pixels)
def intensity_filtering(img, rects, avg_intensity):
    above_bth = np.ones(len(rects), dtype=np.float32)
    for i, rect in enumerate(rects):
        lx, uy, rx, by = rect
        patch = img[uy:by, lx:rx]
        if patch.size == 0:
            pass
        above_bth[i] = (patch >= avg_intensity).sum() / patch.size
    return rects[(above_bth >= ABOVE_AI_TH)]

# # removing blobs that are not shaped like 2D Gauss distribution
# def shape_filtering(img, rects, avg_intensity):
#     n = len(rects)
#     gauss_means = np.ones(n, dtype=np.float32)
#     ws = rects[:, 2] - rects[:, 0]
#     hs = rects[:, 3] - rects[:, 1]
#
#     for i, rect in enumerate(rects):
#         lx, uy, rx, by = rect
#         patch = img[uy:by, lx:rx]
#         gauss_means[i] = gauss_mean(patch, ws[i], hs[i])
#
#     return rects[(gauss_means >= avg_intensity)]
#
# # calculating Gauss weighted mean
# def gauss_mean(patch, w, h):
#     cx, cy = w // 2, h // 2
#     sx, sy = w / 3, h / 3
#     mx, my = np.meshgrid(np.arange(w) - cx, np.arange(h) - cy)
#     weights = np.exp(-(mx ** 2 / (2 * sx ** 2) + my ** 2 / (2 * sy ** 2)))
#     weights = weights / np.sum(weights)
#     result = (patch * weights).sum()
#     return result

# removing overlapping detections
def merge_overlapping(img, rects, bth):
    binarized = np.zeros(img.shape, dtype=np.uint8)
    for rect in rects:
        lx, uy, rx, by = rect
        patch = img[uy:by, lx:rx]
        # only pixels with intensity higher than average foreground intensity will be saved
        binarized[uy:by, lx:rx] = np.where(patch >= bth, 255, 0)
    # finds connected components in binary image
    num_labels, labels, bboxes, centroids = cv2.connectedComponentsWithStats(binarized, connectivity=8)
    return bboxes_to_rects(bboxes[1:, :4])

def size_filtering(rects, scale):
    ws = rects[:, 2] - rects[:, 0]
    hs = rects[:, 3] - rects[:, 1]
    length = np.sqrt((ws*ws)+(hs*hs))
    valid = np.where(length >= MIN_LENGTH_TH/scale, True, False)
    return rects[valid]