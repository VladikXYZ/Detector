import sys
import os
import json

import cv2
import numpy as np
import pandas as pd
import napari
from PyQt6.QtWidgets import QApplication, QMessageBox

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
            dets.append(det[prev:prev+ct])
            prev+=ct

        for f, i, d in zip(self.meta["pngs"], imgs, dets):
            self.cache.append([f, i, d])


    @property
    def current_img(self):
        return self.cache[self.idx]

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



    def refresh_view():
        f, img, dets = session.current_img
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
                for c,i in zip(session.cache, session.meta):
                    dets.append(np.asarray(c[2]).flatten().reshape(-1, 4))

                dets[:, 2] -= dets[:, 0]
                dets[:, 3] -= dets[:, 1]
                # df = pd.DataFrame(det, columns=['x', 'y', 'w', 'h'])
                # df.to_csv(str(os.path.join(session.root_dir,i["raw"])), index=False)
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