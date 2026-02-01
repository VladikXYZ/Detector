import sys
import os
import json
import warnings
import numpy as np
import pandas as pd
import tifffile
import napari
from napari.utils.notifications import show_info
from magicgui import magicgui
from PyQt6.QtWidgets import QApplication, QFileDialog

# --- SILENCE WARNINGS ---
# This ensures the console remains clean when we access the viewer internals
# warnings.filterwarnings("ignore", category=FutureWarning, module="napari")


# --- 1. DATA MANAGEMENT ---
class ExperimentSession:
    def __init__(self, json_path):
        self.json_path = json_path
        self.root_dir = os.path.dirname(json_path)
        with open(json_path, "r") as f:
            self.images_meta = json.load(f)
        self.total_images = len(self.images_meta)
        self.current_idx = 0

    def get_current_meta(self):
        return self.images_meta[self.current_idx]

    def load_current_data(self):
        meta = self.get_current_meta()
        img = tifffile.imread(os.path.join(self.root_dir, meta["filename"]))

        csv_path = os.path.join(self.root_dir, meta["detections_csv_file"])
        rects = []
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                for _, r in df.iterrows():
                    rects.append([[r["UY"], r["LX"]], [r["BY"], r["RX"]]])

        # Always return valid numpy array, even if empty
        if not rects:
            return img, np.empty((0, 2, 2)), meta["scale"]

        return img, np.array(rects), meta["scale"]

    def save_current_detections(self, rects):
        csv_path = os.path.join(self.root_dir, self.get_current_meta()["detections_csv_file"])
        data = []
        for r in rects:
            ys, xs = r[:, 0], r[:, 1]
            uy, by, lx, rx = int(np.min(ys)), int(np.max(ys)), int(np.min(xs)), int(np.max(xs))
            length = np.sqrt((rx - lx) ** 2 + (by - uy) ** 2)
            data.append([lx, uy, rx, by, length])

        pd.DataFrame(data, columns=["LX", "UY", "RX", "BY", "Length"]).to_csv(csv_path, index=False)
        print(f"Saved to {csv_path}")


# --- 2. GUI LAYER ---
def run_editor(json_path):
    session = ExperimentSession(json_path)
    viewer = napari.Viewer(title="Cluster Editor")

    def refresh_view():
        img, rects, _ = session.load_current_data()
        meta = session.get_current_meta()

        # Update Window Title
        viewer.title = f"Editor - {session.current_idx + 1}/{session.total_images}: {meta['filename']}"

        # 1. Update Image (Preserve Layer to keep settings)
        if 'Image' in viewer.layers:
            viewer.layers['Image'].data = img
        else:
            viewer.add_image(img, name='Image')

        # 2. Update Detections (Preserve Layer to keep styles like edge width/color)
        if 'Detections' in viewer.layers:
            viewer.layers['Detections'].data = rects
        else:
            shapes = viewer.add_shapes(
                rects,
                shape_type='rectangle',
                edge_color='cyan',
                face_color='transparent',
                edge_width=2,
                name='Detections'
            )
            shapes.mode = 'select'

        # --- FIX FOR UNDO (CTRL+Z) ---
        # 1. Ensure the Detections layer is selected
        viewer.layers.selection.active = viewer.layers['Detections']

        # 2. IMPORTANT: Force focus back to the canvas.
        # This prevents the "Next" button from stealing the keyboard shortcuts.
        try:
            viewer.window.qt_viewer.canvas.setFocus()
        except Exception:
            pass

        show_info(f"Loaded {meta['filename']}")

    def save():
        if 'Detections' in viewer.layers:
            session.save_current_detections(viewer.layers['Detections'].data)

    # --- NAVIGATION ---

    @viewer.bind_key('Right')
    def next_img(v):
        save()
        if session.current_idx < session.total_images - 1:
            session.current_idx += 1
            refresh_view()
        else:
            show_info("End of Experiment")

    @viewer.bind_key('Left')
    def prev_img(v):
        save()
        if session.current_idx > 0:
            session.current_idx -= 1
            refresh_view()
        else:
            show_info("Start of Experiment")

    refresh_view()
    napari.run()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    fpath = sys.argv[1] if len(sys.argv) > 1 else None
    if not fpath:
        fpath, _ = QFileDialog.getOpenFileName(None, "Select results.json", "", "JSON (*.json)")
    if fpath:
        run_editor(fpath)