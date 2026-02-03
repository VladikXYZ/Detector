import sys
import os
import json

import cv2
import numpy as np
import pandas as pd
import tifffile
import napari
from PyQt6.QtWidgets import QApplication

from detector2 import ImageInfo


# --- 1. DATA MANAGER (HANDLES CACHING & I/O) ---
class DataManager:
    def __init__(self, json_path):
        self.root_dir = os.path.dirname(json_path)
        with open(json_path, "r") as f:
            self.meta_list = [ImageInfo(**d) for d in json.load(f)]
        self.idx = 0
        self.total = len(self.meta_list)
        files = [ii.file for ii in self.meta_list]
        self.cache = []
        for f in files:
            img = cv2.imread(os.path.join(self.root_dir, f))
            raw_dets = pd.read_csv(os.path.join(self.root_dir, f.split(".")[0] + ".csv")).to_numpy()
            x = raw_dets[:, 0]
            y = raw_dets[:, 1]
            x2 = x + raw_dets[:, 2]
            y2 = y + raw_dets[:, 3]

            # 2. Stack into Napari format: (N, 2, 2) -> [[y, x], [y2, x2]]
            # Note: Napari uses (row, col) which corresponds to (y, x)
            p1 = np.stack([y, x], axis=1)  # Top-Left
            p2 = np.stack([y2, x2], axis=1)  # Bottom-Right

            dets = np.stack([p1, p2], axis=1)
            # print(dets.shape)
            self.cache.append((f, img, dets))


    @property
    def current_img(self):
        return self.cache[self.idx]

    def next(self):
        if self.idx < self.total - 1:
            self.idx += 1
            return True
        return False

    def prev(self):
        if self.idx > 0:
            self.idx -= 1
            return True
        return False


# --- 2. MAIN VIEWER LOGIC ---
def run_editor(json_path):
    session = DataManager(json_path)
    viewer = napari.Viewer(title="Detection Editor")

    def refresh_view():
        """Updates the viewer with data from the session."""
        f, img, dets = session.current_img

        # Update Image Layer
        if 'Image' in viewer.layers:
            viewer.layers['Image'].data = img
        else:
            viewer.add_image(img, name='Image')

        # Update Shapes Layer
        if 'Detections' in viewer.layers:
            viewer.layers['Detections'].data = dets
        else:
            viewer.add_shapes(
                dets,
                shape_type='rectangle',
                edge_color='red',
                face_color='transparent',
                edge_width=2,
                name='Detections'
            )

        viewer.status = f"Image {session.idx + 1}/{session.total}: {f}"


    # --- KEYBINDINGS ---
    @viewer.bind_key('Right')
    def next_image(v):
        if session.next():
            refresh_view()
        else:
            viewer.status = "End of experiment."

    @viewer.bind_key('Left')
    def prev_image(v):
        if session.prev():
            refresh_view()
        else:
            viewer.status = "Start of experiment."

    # --- START ---
    refresh_view()
    napari.run()


if __name__ == "__main__":
    # Usage: python edit.py path/to/experiment.json
    app = QApplication(sys.argv)  # Fix for some OS requiring Qt App

    path = sys.argv[1] if len(sys.argv) > 1 else "experiment.json"

    if os.path.exists(path):
        run_editor(path)
    else:
        print(f"Error: Could not find {path}")