import sys
import os
import json

import cv2
import numpy as np
import pandas as pd
import napari
from PyQt6.QtWidgets import QApplication, QMessageBox

ACTIONS = set(["changed", "added", "removed", "init"])

class DataManager:
    def __init__(self, json_path, viewer):
        self.root_dir = os.path.dirname(json_path)
        self.viewer = viewer
        with open(json_path, "r") as f:
            self.meta = json.load(f)
        self.idx = 0
        self.total = len(self.meta)
        # files = [i["file"] for i in self.meta_list]
        self.cache = []
        imgs = []
        for file in self.meta["pngs"]:
            imgs.append(cv2.imread(str(os.path.join(self.root_dir, file))))
        raw_dets = pd.read_csv(str(os.path.join(self.root_dir, "all.csv"))).to_numpy()
        x = raw_dets[:, 0]
        y = raw_dets[:, 1]
        x2 = x + raw_dets[:, 2]
        y2 = y + raw_dets[:, 3]
        p1 = np.stack([y, x], axis=1)  # Top-Left
        p2 = np.stack([y2, x2], axis=1)  # Bottom-Right
        det = np.stack([p1, p2], axis=1)
        dets = []

        prev = 0
        for ct in self.meta["counts"]:
            cur = det[prev:prev+ct]
            # print(len(cur))
            # print(cur)
            dets.append(cur)
            prev+=ct
        self.stacks = []
        for f, i, d in zip(self.meta["pngs"], imgs, dets):
            # d = [np.copy(box) for box in d]
            # d = d[:4]
            self.cache.append([f, i, d])
            self.stacks.append([d])


    @property
    def current_img(self):
        return self.cache[self.idx]
    @property
    def current_stack(self):
        return self.stacks[self.idx]

    def next(self):
        if self.idx < self.total - 1:
            self.cache[self.idx][2] = self.viewer.layers["Detections"].data
            self.idx += 1
            return True
        return False

    def prev(self):
        if self.idx > 0:
            self.cache[self.idx][2] = self.viewer.layers["Detections"].data
            self.idx -= 1
            return True
        return False


def run_editor(json_path):
    viewer = napari.Viewer(title="Detection Editor")
    session = DataManager(json_path, viewer)

    # --- UNDO SYSTEM VARIABLES ---
    # undo_stack = session.current_stack
    # print(undo_stack)
    is_undoing = False

    def push_state(event=None):
        """Saves the current state of the bounding boxes to the history stack."""
        nonlocal is_undoing
        if is_undoing or 'Detections' not in viewer.layers or event.action not in ACTIONS: return

        undo_stack = session.current_stack
        # print(len(undo_stack))
        # print(event.action)
        # Make a deep copy of the current bounding boxes
        layer_data = viewer.layers['Detections'].data
        current_data = [np.copy(box) for box in layer_data]
        undo_stack.append(current_data)

        # Limit history to the last 30 actions to prevent memory bloat
        if len(undo_stack) > 16:
            undo_stack.pop(0)

    def refresh_view():
        f, img, dets = session.current_img
        # print([ len(x) for x in session.stacks])
        undo_stack = session.current_stack
        # print(undo_stack)
        if 'Image' in viewer.layers:
            viewer.layers['Image'].data = img
        else:
            viewer.add_image(img, name='Image')

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

            # --- UNDO SYSTEM HOOK ---
            # undo_stack.clear()
            is_undoing = False

            det_layer = viewer.layers['Detections']
            # Listen for any changes (add, delete, move) and push to stack
            if push_state not in det_layer.events.data.callbacks:
                det_layer.events.data.connect(push_state)

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

    @viewer.bind_key('Control-Z')
    def custom_undo(v):
        nonlocal is_undoing
        undo_stack = session.current_stack
        print(len(undo_stack))
        # We need at least 2 states to undo (the current one, and the previous one)
        if len(undo_stack) > 1:

            is_undoing = True

            # Pop (remove) the current messed-up state
            undo_stack.pop()

            # Grab the previous state and apply it
            prev_data = [np.copy(box) for box in undo_stack[-1]]
            viewer.layers['Detections'].data = prev_data

            is_undoing = False
            viewer.status = "Undo applied."
        else:
            viewer.status = "Nothing to undo on this image."

    def setup_close_handler():
        main_window = viewer.window._qt_window
        # original_close_event = main_window.closeEvent

        def custom_close_event(event):
            msg = QMessageBox(main_window)
            msg.setWindowTitle("Save Changes?")
            msg.setText("Do you want to save changes to disk before quitting?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            msg.setDefaultButton(QMessageBox.Yes)

            reply = msg.exec_()

            if reply == QMessageBox.Cancel:
                event.ignore()
                return

            if reply == QMessageBox.Yes:
                print("Saving...")
                dets = []
                for i,c in enumerate(session.cache):
                    print(c[2][:4].flatten().reshape(-1, 4))
                    # print(m)
                    det = np.asarray(c[2]).flatten().reshape(-1, 4)
                    n = len(det)
                    length = np.sqrt(det[:,2]*det[:,3])
                    scale = np.ones(n)*session.meta["scales"][i]
                    fr = np.ones(n)*i
                    session.meta["counts"][i] = n
                    dets.append(np.column_stack((det,length, scale, fr)))

                dets = np.concat(dets)
                dets[:, [0, 1, 2, 3]] = dets[:, [1, 0, 3, 2]]
                dets[:, 2] -= dets[:, 0]
                dets[:, 3] -= dets[:, 1]
                df = pd.DataFrame(dets, columns=['x', 'y', 'w', 'h', "length", "scale", "from"])
                # print(i["raw"])
                df.to_csv(str(os.path.join(session.root_dir,"all.csv")), index=False)
                # raw_dets = pd.read_csv(str(os.path.join(self.root_dir, "all.csv"))).to_numpy()
                print("Saved!")


        main_window.closeEvent = custom_close_event

    setup_close_handler()

    refresh_view()
    napari.run()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    path = sys.argv[1]
    if os.path.exists(path):
        run_editor(path)
    else:
        print(f"Error: Could not find {path}")