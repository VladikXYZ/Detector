import numpy as np

# PREPROCESSING CONSTANTS
# CLAHE_LIM = 2.5 # clip limit for CLAHE
# KERNEL = (40, 40) # kernel for image blurring
# U8_MAX = 255 # maximum value of np.uint8

# DETECTION SETUP
NM_PXL = 64 # default scale factor (64 pixels = 1 nm)
# minimal desired detection (in nanometers)
# for LoG, DoG and DoH it should not exceed 1 nanometer
# for large values use MIN_LENGTH variable for
# size filtering in postprocessing
# MIN_DET = 0.25
# MIN_DET_PXL = NM_PXL*MIN_DET # minimal desired detection (in pixels)
# MAX_DET = 40 # maximal desired detection (in nanometers)
# # maximal desired detection  (in pixels)
# MAX_DET_PXL = NM_PXL*MAX_DET

# for LoG, DoG and DoH
# precision of intermediate detections (in nanometers)
# PRECISION = 0.25
# # list of all detection sizes
# NMS = np.arange(MIN_DET, MAX_DET+PRECISION, PRECISION)

# POSTPROCESSING CONSTANTS
# how many pixels in detection should be
# above average pixel intensity of foreground
# ABOVE_AI_TH = 0.5
# MIN_LENGTH = 1 # minimum length of detection
# # calculating minimum length in pixels
# MIN_LENGTH_TH = NM_PXL*MIN_LENGTH

# OUTPUTS AND PLOTTING
# how many detection images will be plotted
# PLOT_NUM = 4 # must be at least 2!!!
# DET_FILE = "dets.csv" # per image detection file end
# # format of per image detection file
OUTPUT_FORMAT = ["LX", "UY", "RX", "BY", "Length"]
# ALL_DETS = "all_dets.csv" # whole sample detection file end
# RES_DIR = "results/" # directory for results
#
# # dictionary for algorithms names for plotting results
# NAME = { "log": "LoG",
#     "dog": "DoG", "doh": "DoH",
#     "mser": "MSER", "contours": "Contours"}

