import os
import json
import numpy as np
import pandas as pd
import tifffile
import napari
from napari.utils.notifications import show_info
from magicgui import magicgui


# --- 1. DATA MANAGEMENT LAYER ---

class ExperimentSession:
    """
    Handles reading the JSON manifest and loading/saving specific files.
    """

    def __init__(self, json_path):
        self.json_path = json_path
        self.root_dir = os.path.dirname(json_path)

        with open(json_path, "r") as f:
            # The JSON is a direct list of image objects
            self.images_meta = json.load(f)

        self.total_images = len(self.images_meta)
        self.current_idx = 0

    def get_current_meta(self):
        return self.images_meta[self.current_idx]

    def load_current_data(self):
        meta = self.get_current_meta()

        # 1. Load Image
        img_path = os.path.join(self.root_dir, meta["filename"])
        # reading with tifffile is often safer for scientific tiffs than cv2
        image_data = tifffile.imread(img_path)

        # 2. Load Detections (CSV)
        # JSON key is 'detections_csv_file' based on your upload
        csv_filename = meta["detections_csv_file"]
        csv_path = os.path.join(self.root_dir, csv_filename)

        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            # Format: LX, UY, RX, BY, Length
            # Napari expects: [[y1, x1], [y2, x2]] (top-left, bottom-right)
            rects = []
            if not df.empty:
                for _, row in df.iterrows():
                    lx, uy, rx, by = row["LX"], row["UY"], row["RX"], row["BY"]
                    # Napari format: [ [min_y, min_x], [max_y, max_x] ]
                    rects.append([[uy, lx], [by, rx]])

            return image_data, np.array(rects), meta["scale"]

        return image_data, np.empty((0, 2, 2)), meta["scale"]

    def save_current_detections(self, napari_rects):
        """
        Converts Napari rectangles back to your CSV format and saves.
        """
        meta = self.get_current_meta()
        csv_path = os.path.join(self.root_dir, meta["detections_csv_file"])

        data_rows = []

        for r in napari_rects:
            # Napari returns 4 corners. We simplify to min/max.
            # r shape is usually (4, 2) => [[y, x], ...]
            ys = r[:, 0]
            xs = r[:, 1]
            uy, by = int(np.min(ys)), int(np.max(ys))
            lx, rx = int(np.min(xs)), int(np.max(xs))

            # Recalculate Length (using simple Euclidean for now)
            # Note: Ideally, you would reuse the NM_PXL constant from your config here
            # for a truly accurate length recalculation.
            w = rx - lx
            h = by - uy
            length = np.sqrt(w ** 2 + h ** 2)

            data_rows.append([lx, uy, rx, by, length])

        df = pd.DataFrame(data_rows, columns=["LX", "UY", "RX", "BY", "Length"])
        df.to_csv(csv_path, index=False)
        print(f"Saved {len(df)} detections to {csv_path}")


# --- 2. GUI LAYER (NAPARI) ---

def run_editor(json_path):
    session = ExperimentSession(json_path)
    viewer = napari.Viewer(title=f"Cluster Editor - {os.path.basename(json_path)}")

    # -- Helper to refresh view --
    def refresh_view():
        viewer.layers.clear()

        # Load data
        img, rects, scale = session.load_current_data()
        meta = session.get_current_meta()
        fname = meta["filename"]
        idx = session.current_idx + 1
        total = session.total_images

        # 1. Add Image Layer
        viewer.add_image(img, name=f"{idx}/{total}: {fname}")

        # 2. Add Shapes Layer (for Bounding Boxes)
        # Edge color cyan, face color transparent for easy viewing
        viewer.add_shapes(
            rects,
            shape_type='rectangle',
            edge_color='cyan',
            face_color='transparent',
            edge_width=2,
            name='Detections'
        )
        show_info(f"Loaded {fname} ({len(rects)} clusters)")

    # -- GUI Controls --

    @magicgui(call_button="< Previous")
    def prev_image():
        save_changes()  # Auto-save before moving
        if session.current_idx > 0:
            session.current_idx -= 1
            refresh_view()
        else:
            show_info("Already at first image.")

    @magicgui(call_button="Next >")
    def next_image():
        save_changes()  # Auto-save before moving
        if session.current_idx < session.total_images - 1:
            session.current_idx += 1
            refresh_view()
        else:
            show_info("Already at last image.")

    @magicgui(call_button="Save Changes")
    def save_changes():
        # Get the shapes layer
        if 'Detections' in viewer.layers:
            layer = viewer.layers['Detections']
            # data contains the coordinates
            session.save_current_detections(layer.data)
            show_info("Saved successfully.")

    # Add buttons to the viewer window
    viewer.window.add_dock_widget(prev_image, area='right')
    viewer.window.add_dock_widget(next_image, area='right')
    viewer.window.add_dock_widget(save_changes, area='right')

    # Initial load
    refresh_view()

    # Start app
    napari.run()


if __name__ == "__main__":
    # Simple file dialog to start
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    print("Please select the results.json file...")
    fpath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])

    if fpath:
        run_editor(fpath)