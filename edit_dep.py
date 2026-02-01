# import sys
# import os
# import json
# import numpy as np
# import pandas as pd
# import tifffile
# import napari
# from napari.utils.notifications import show_info
# from magicgui import magicgui
# from PyQt6.QtWidgets import QApplication, QFileDialog
#
#
# # --- 1. DATA MANAGEMENT LAYER ---
#
# class ExperimentSession:
#     def __init__(self, json_path):
#         self.json_path = json_path
#         self.root_dir = os.path.dirname(json_path)
#
#         with open(json_path, "r") as f:
#             self.images_meta = json.load(f)
#
#         self.total_images = len(self.images_meta)
#         self.current_idx = 0
#
#     def get_current_meta(self):
#         return self.images_meta[self.current_idx]
#
#     def load_current_data(self):
#         meta = self.get_current_meta()
#         img_path = os.path.join(self.root_dir, meta["filename"])
#         image_data = tifffile.imread(img_path)
#
#         csv_filename = meta["detections_csv_file"]
#         csv_path = os.path.join(self.root_dir, csv_filename)
#
#         if os.path.exists(csv_path):
#             df = pd.read_csv(csv_path)
#             rects = []
#             if not df.empty:
#                 for _, row in df.iterrows():
#                     lx, uy, rx, by = row["LX"], row["UY"], row["RX"], row["BY"]
#                     rects.append([[uy, lx], [by, rx]])
#             return image_data, np.array(rects), meta["scale"]
#
#         return image_data, np.empty((0, 2, 2)), meta["scale"]
#
#     def save_current_detections(self, napari_rects):
#         meta = self.get_current_meta()
#         csv_path = os.path.join(self.root_dir, meta["detections_csv_file"])
#         data_rows = []
#
#         for r in napari_rects:
#             ys = r[:, 0]
#             xs = r[:, 1]
#             uy, by = int(np.min(ys)), int(np.max(ys))
#             lx, rx = int(np.min(xs)), int(np.max(xs))
#
#             w = rx - lx
#             h = by - uy
#             length = np.sqrt(w ** 2 + h ** 2)
#
#             data_rows.append([lx, uy, rx, by, length])
#
#         df = pd.DataFrame(data_rows, columns=["LX", "UY", "RX", "BY", "Length"])
#         df.to_csv(csv_path, index=False)
#         print(f"Saved {len(df)} detections to {csv_path}")
#
#
# # --- 2. GUI LAYER (NAPARI) ---
#
# def restrict_controls(viewer, layer_name='Detections'):
#     """
#     Aggressively hides all tools except 'Select' and 'Rectangle'.
#     """
#     try:
#         layer = viewer.layers[layer_name]
#         qt_ctrl = viewer.window.qt_viewer.controls.widgets[layer]
#
#         # --- DEBUG: PRINT ALL AVAILABLE BUTTONS ---
#         # layer = viewer.layers['Detections']
#         # if hasattr(viewer.window, 'qt_viewer'):
#         #     qt_ctrl = viewer.window.qt_viewer.controls.widgets.get(layer)
#         #     if qt_ctrl:
#         #         print("\n--- FOUND CONTROLS ---")
#         #         for attr_name in dir(qt_ctrl):
#         #             # Filter for likely UI elements (buttons, checkboxes, spinboxes)
#         #             if "button" in attr_name:
#         #                 print(f"Found widget: {attr_name}")
#         #         print("----------------------\n")
#
#
#
#         for name in ['ellipse_button', 'line_button', 'path_button', 'polygon_button', 'transform_button',
#                      'vertex_insert_button', 'vertex_remove_button', 'direct_button','polygon_lasso_button',
#                      'move_front_button', 'move_back_button','polyline_button']:
#             if hasattr(qt_ctrl, name): getattr(qt_ctrl, name).setVisible(False)
#         if hasattr(qt_ctrl, 'button_grid'):
#             grid = qt_ctrl.button_grid.layout()
#             grid.addWidget(qt_ctrl.move_button, 0, 3)
#             grid.addWidget(qt_ctrl.select_button, 0, 4)
#             grid.addWidget(qt_ctrl.rectangle_button, 0, 5)
#             grid.addWidget(qt_ctrl.delete_button, 0, 6)
#
#
#     except Exception as e:
#         print(f"Could not restrict controls: {e}")
#
#
# def run_editor(json_path):
#     session = ExperimentSession(json_path)
#     viewer = napari.Viewer(title=f"Cluster Editor")
#
#     def refresh_view():
#         viewer.layers.clear()
#
#         img, rects, scale = session.load_current_data()
#         meta = session.get_current_meta()
#         fname = meta["filename"]
#         idx = session.current_idx + 1
#         total = session.total_images
#
#         # 1. Image Layer
#         viewer.add_image(img, name=f"{idx}/{total}: {fname}")
#
#         # 2. Shapes Layer
#         shapes_layer = viewer.add_shapes(
#             rects,
#             shape_type='rectangle',
#             edge_color='cyan',
#             face_color='transparent',
#             edge_width=2,
#             name='Detections'
#         )
#
#         # Default to SELECT mode (safe mode)
#         shapes_layer.mode = 'select'
#
#         # --- HIDE THE UNWANTED BUTTONS ---
#         restrict_controls(viewer, 'Detections')
#
#         show_info(f"Loaded {fname}. Shortcuts: [A]=Add Box, [S]=Select/Edit")
#
#     def save_current_step():
#         if 'Detections' in viewer.layers:
#             session.save_current_detections(viewer.layers['Detections'].data)
#
#     # -- KEY BINDINGS --
#
#     @viewer.bind_key('a')
#     def mode_add(viewer):
#         if 'Detections' in viewer.layers:
#             viewer.layers['Detections'].mode = 'add_rectangle'
#             show_info("Mode: ADD RECTANGLE")
#
#     @viewer.bind_key('s')
#     def mode_select(viewer):
#         if 'Detections' in viewer.layers:
#             viewer.layers['Detections'].mode = 'select'
#             show_info("Mode: SELECT / EDIT")
#
#     @viewer.bind_key('x')
#     def quick_delete(viewer):
#         if 'Detections' in viewer.layers:
#             viewer.layers['Detections'].remove_selected()
#             show_info("Deleted.")
#
#     @viewer.bind_key('Right')
#     def next_image_key(viewer):
#         save_current_step()
#         if session.current_idx < session.total_images - 1:
#             session.current_idx += 1
#             refresh_view()
#         else:
#             show_info("End of experiment.")
#
#     @viewer.bind_key('Left')
#     def prev_image_key(viewer):
#         save_current_step()
#         if session.current_idx > 0:
#             session.current_idx -= 1
#             refresh_view()
#         else:
#             show_info("Start of experiment.")
#
#     # -- SIDEBAR --
#     @magicgui(call_button="Save & Next >")
#     def next_btn():
#         next_image_key(viewer)
#
#     @magicgui(call_button="< Prev")
#     def prev_btn():
#         prev_image_key(viewer)
#
#     @magicgui(call_button="Save Now")
#     def save_btn():
#         save_current_step()
#         show_info("Saved!")
#
#     viewer.window.add_dock_widget(prev_btn, area='right')
#     viewer.window.add_dock_widget(next_btn, area='right')
#     viewer.window.add_dock_widget(save_btn, area='right')
#
#     refresh_view()
#     napari.run()
#
#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     fpath = "/home/vladikxyz/Downloads/git/Detector/results/6768/results.json"
#     if len(sys.argv) > 1:
#         fpath = sys.argv[1]
#
#     if not fpath:
#         fpath, _ = QFileDialog.getOpenFileName(None, "Select results.json", "", "JSON (*.json)")
#
#     if fpath:
#         run_editor(fpath)


import sys
import os
import json
import numpy as np
import pandas as pd
import tifffile
import napari
from napari.utils.notifications import show_info
from magicgui import magicgui
from magicgui.widgets import Container, PushButton
from PyQt6.QtWidgets import QApplication, QFileDialog


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
        img_path = os.path.join(self.root_dir, meta["filename"])
        img = tifffile.imread(img_path)

        csv_path = os.path.join(self.root_dir, meta["detections_csv_file"])
        rects = []
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                for _, r in df.iterrows():
                    rects.append([[r["UY"], r["LX"]], [r["BY"], r["RX"]]])

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

    # --- CUSTOM TOOLBAR (Public API Only) ---
    # Instead of hacking the native controls, we build our own clean toolbar.

    btn_add = PushButton(text="Add Box (A)", name="add_btn")
    btn_select = PushButton(text="Select / Edit (S)", name="select_btn")
    btn_delete = PushButton(text="Delete Selected (X)", name="delete_btn")

    # Functions to switch modes safely
    def set_add_mode():
        if 'Detections' in viewer.layers:
            viewer.layers['Detections'].mode = 'add_rectangle'
            show_info("Mode: ADD RECTANGLE")

    def set_select_mode():
        if 'Detections' in viewer.layers:
            viewer.layers['Detections'].mode = 'select'
            show_info("Mode: SELECT / EDIT")

    def delete_selection():
        if 'Detections' in viewer.layers:
            viewer.layers['Detections'].remove_selected()
            show_info("Deleted Selection")

    # Connect buttons
    btn_add.changed.connect(set_add_mode)
    btn_select.changed.connect(set_select_mode)
    btn_delete.changed.connect(delete_selection)

    # Create the container
    toolbar = Container(widgets=[btn_select, btn_add, btn_delete], layout="horizontal", labels=False)
    viewer.window.add_dock_widget(toolbar, name="Tools", area="top")

    # --- CORE LOGIC ---

    def refresh_view():
        img, rects, _ = session.load_current_data()
        meta = session.get_current_meta()

        # Update Window Title
        viewer.title = f"Editor - {session.current_idx + 1}/{session.total_images}: {meta['filename']}"

        # 1. Update Image Layer
        if 'Image' in viewer.layers:
            viewer.layers['Image'].data = img
        else:
            viewer.add_image(img, name='Image')

        # 2. Update Detections Layer
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

        # --- THE FIX FOR UNDO (CTRL+Z) ---
        # 1. Force the selection to be the Detections layer
        viewer.layers.selection.active = viewer.layers['Detections']

        # 2. Ensure we stay in "Select" mode so you can click/undo immediately
        viewer.layers['Detections'].mode = 'select'

        show_info(f"Loaded {meta['filename']}")

    def save():
        if 'Detections' in viewer.layers:
            session.save_current_detections(viewer.layers['Detections'].data)

    # --- NAVIGATION & SHORTCUTS ---

    @viewer.bind_key('a')
    def _key_add(v):
        set_add_mode()

    @viewer.bind_key('s')
    def _key_select(v):
        set_select_mode()

    @viewer.bind_key('x')
    def _key_delete(v):
        delete_selection()

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

    # Sidebar Navigation
    @magicgui(call_button="Save & Next >")
    def btn_next():
        next_img(viewer)

    @magicgui(call_button="< Prev")
    def btn_prev():
        prev_img(viewer)

    viewer.window.add_dock_widget(btn_prev, area='right')
    viewer.window.add_dock_widget(btn_next, area='right')

    # Start
    refresh_view()

    # Optional: You can manually close the built-in 'Layer controls' if it's annoying,
    # or just instruct users to minimize it. The custom toolbar above is the primary UI.

    napari.run()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # fpath = sys.argv[1] if len(sys.argv) > 1 else None
    fpath = "/home/vladikxyz/Downloads/git/Detector/results/6768/results.json"
    if not fpath:
        fpath, _ = QFileDialog.getOpenFileName(None, "Select results.json", "", "JSON (*.json)")
    if fpath:
        run_editor(fpath)