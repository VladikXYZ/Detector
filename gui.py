import sys
import os
import json
import threading
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QGridLayout, QFileDialog, QDoubleSpinBox, QMessageBox)
from PyQt6.QtCore import QTimer, Qt

# Import the manager from your backend
from gemini import ClusterDetector

STATE_FILE = "directories.json"


class DetectorWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Cluster Detector")
        self.resize(550, 200)  # Slightly wider to fit buttons
        self.thread = None

        # Load previous paths
        last_dirs = self.load_last_dirs()
        self.source_dir = last_dirs.get("source", None)
        self.output_dir = last_dirs.get("output", None)

        # --- Layout Setup ---
        layout = QGridLayout()

        # 1. Source Directory UI
        layout.addWidget(QLabel("Source Directory:"), 0, 0)
        self.lbl_source = QLabel(self.source_dir if self.source_dir else "Not Selected")
        self.lbl_source.setStyleSheet("color: gray; border: 1px solid #ccc; padding: 4px;")
        layout.addWidget(self.lbl_source, 0, 1)

        btn_source = QPushButton("Select")
        btn_source.clicked.connect(self.select_source)
        layout.addWidget(btn_source, 0, 2)

        # 2. Output Directory UI
        layout.addWidget(QLabel("Output Directory:"), 1, 0)
        self.lbl_output = QLabel(self.output_dir if self.output_dir else "Not Selected")
        self.lbl_output.setStyleSheet("color: gray; border: 1px solid #ccc; padding: 4px;")
        layout.addWidget(self.lbl_output, 1, 1)

        btn_output = QPushButton("Select")
        btn_output.clicked.connect(self.select_output)
        layout.addWidget(btn_output, 1, 2)

        # 3. Min Size Row + PROCESS Button
        layout.addWidget(QLabel("Minimal size (nm):"), 2, 0)

        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(0.1, 50.0)
        self.spin_min.setSingleStep(0.1)
        self.spin_min.setValue(1.0)
        layout.addWidget(self.spin_min, 2, 1)

        self.btn_process = QPushButton("Process")
        self.btn_process.clicked.connect(self.start_processing)
        layout.addWidget(self.btn_process, 2, 2)

        # 4. Max Size Row + EDIT Button
        layout.addWidget(QLabel("Maximal size (nm):"), 3, 0)

        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(0.1, 50.0)
        self.spin_max.setSingleStep(0.1)
        self.spin_max.setValue(10.0)
        layout.addWidget(self.spin_max, 3, 1)

        self.btn_edit = QPushButton("Edit Results")
        self.btn_edit.clicked.connect(self.start_editor)
        layout.addWidget(self.btn_edit, 3, 2)

        self.setLayout(layout)

        # Timer to check thread status
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_thread)

    def select_source(self):
        d = QFileDialog.getExistingDirectory(self, "Select Source Directory", self.source_dir or "")
        if d:
            self.source_dir = d
            self.lbl_source.setText(d)

    def select_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir or "")
        if d:
            self.output_dir = d
            self.lbl_output.setText(d)

    def start_processing(self):
        if not self.source_dir or self.source_dir == "Not Selected":
            QMessageBox.warning(self, "Error", "Please select a source directory.")
            return
        if not self.output_dir or self.output_dir == "Not Selected":
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return

        m = self.spin_min.value()
        M = self.spin_max.value()

        if m >= M:
            QMessageBox.warning(self, "Error", "Minimal size must be smaller than maximal size.")
            return

        # UI updates
        self.btn_process.setEnabled(False)
        self.btn_process.setText("Running...")
        self.save_last_dirs()

        # Instantiate Manager
        manager = ClusterDetector()

        # Start Thread
        self.thread = threading.Thread(
            target=manager.process_sample,
            args=(self.source_dir, self.output_dir, m, M),
            daemon=False
        )
        self.thread.start()

        # Start checking the thread every 100ms
        self.timer.start(100)

    def start_editor(self):
        # 1. Ask user for the results.json file
        start_dir = self.output_dir if self.output_dir else ""
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Select results.json to Edit",
            start_dir,
            "JSON files (*.json)"
        )

        if fpath:
            # 2. Launch the editor as a separate process
            # This keeps the detector GUI responsive while editing
            try:
                subprocess.Popen([sys.executable, "edit.py", fpath])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not launch editor:\n{e}")

    def check_thread(self):
        # print("check")
        if self.thread and not self.thread.is_alive():
            self.timer.stop()
            self.btn_process.setEnabled(True)
            self.btn_process.setText("Process")
            QMessageBox.information(self, "Done", "Processing Finished Successfully!")
            self.thread = None

    def load_last_dirs(self):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except: return {}

    def save_last_dirs(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"source": self.source_dir, "output": self.output_dir}, f)


# --- Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DetectorWindow()
    window.show()
    sys.exit(app.exec())