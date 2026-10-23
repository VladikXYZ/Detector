# Cluster Detector

Cluster Detector is an automated image analysis tool designed to identify, measure, and manually verify nanoparticle clusters in `.tif` microscopy images. It features a PyQt6-based graphical interface for batch processing and integrates the Napari viewer for interactive quality control.

## ✨ Features

* **Automated Detection:** Uses MSER (Maximally Stable Extremal Regions) and bilateral filtering to accurately isolate clusters.
* **Physical Scaling:** Automatically extracts pixel-to-nanometer scale metadata directly from `.tif` files.
* **Size Filtering:** Filter detections based on user-defined minimum and maximum physical sizes (in nanometers).
* **Interactive Editor:** Seamlessly opens processed results in **Napari**, allowing users to visually inspect, add, or delete bounding boxes.
* **Data Export:** Outputs clean CSV files containing the `x`, `y`, `width`, `height`, and `length` of every validated cluster.

## 🚀 How to Use (Executable version)

1. Double-click **`ClusterDetector.exe`** to launch the application.
2. Click **Select** next to *Source Directory* to choose the folder containing your raw `.tif` images.
3. Click **Select** next to *Output Directory* to choose where the results will be saved.
4. Adjust the **Minimal size (nm)** and **Maximal size (nm)** thresholds.
5. Click **Process**. The tool will run the detection algorithm in the background.
6. Once processing is finished, click **Edit Results** to review the detections.

## ⌨️ Editor Controls (Napari)

When the Editor is open, use the following controls to navigate and modify your results:

* **Right Arrow (`→`)**: Save current image and go to the Next Image.
* **Left Arrow (`←`)**: Save current image and go to the Previous Image.
* **Napari Tools**: Use the standard Napari shape tools on the left panel to draw new rectangles or delete false positives.
* **Closing:** Simply close the window when you are done. It will prompt you to save your manual corrections back to the CSV files.

## 🛠️ Running from Source

If you are running the Python scripts directly instead of the executable, ensure you have the required dependencies installed:

```bash
pip install PyQt6 opencv-python numpy pandas napari tifffile

```

Then run:

```bash
python gui.py

```
