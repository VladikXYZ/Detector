from time import sleep
import cv2
import numpy as np
# from config import CLAHE_LIM, KERNEL, U8_MAX

CLAHE_LIM = 2.5
KERNEL = (40, 40)
U8_MAX = 255

def preprocess(args) -> tuple:
    f, scale = args
    img = load_uint(f)
    img = scaled_blur(img, scale, cv2.INTER_LINEAR)
    img = clahe(img)
    img = invert(img)
    inv, bth = otsu(img)
    return (inv, scale, bth)

# loading image in np.uint8 format
def load_uint(path: str):
    result = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if result is None:
        raise Exception(f"Cannot found file: {path}")

    result = result.astype(dtype=np.float32)
    mmax = np.max(result)
    mmin = np.min(result)
    return (((result - mmin) / max(1, (mmax - mmin)))*U8_MAX).astype(dtype=np.uint8)

# scaling image
def scale_image(img, scale, inter=cv2.INTER_NEAREST):
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=inter)

# upscaling image, blurring image and downscaling back to original size
def scaled_blur(img, scale, inter=cv2.INTER_NEAREST):
    img = scale_image(img, scale, inter)
    img = cv2.blur(img, KERNEL)
    return scale_image(img, 1 / scale, inter)

# otsu thresholding for image
def otsu(img):
    if img.dtype == np.uint8:
        th, mask = cv2.threshold(img, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = mask*img # background pixels are zeroed, foreground pixels stays the same
        bth = result.sum()/mask.sum() # calculating average intensity among pixels in foreground
        return result, bth
    raise Exception(f"Unknown dtype = {img.dtype}")

# image inversion
def invert(img):
    if img.dtype == np.uint8:
        return U8_MAX - img
    raise Exception(f"Unknown dtype = {img.dtype}")

# histogram equalization using CLAHE
def clahe(img):
    if img.dtype == np.uint8:
        clahe_obj = cv2.createCLAHE(clipLimit=CLAHE_LIM)
        return clahe_obj.apply(img.astype(dtype=np.uint8))
    raise Exception(f"Unknown dtype = {img.dtype}")

# conversion from np.uint8 to np.float16 (used for LoG, DoG and DoH)
def to_float(img):
    if img.dtype == np.uint8:
        return (img.astype(dtype=np.float16))/U8_MAX
    raise Exception(f"Unknown dtype = {img.dtype}")