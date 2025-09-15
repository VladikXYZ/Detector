import os
import tkinter as tk
from tkinter import filedialog
from detector import Detector

class Window:
    def select_source(self):
        folder_path = filedialog.askdirectory(title="Select source directory",initialdir=os.getcwd())
        if folder_path:
            self.src_dir = folder_path
            print(self.src_dir)

    def select_destination(self):
        folder_path = filedialog.askdirectory(title="Select destination directory", initialdir=os.getcwd())
        if folder_path:
            self.dst_dir = folder_path
            print(self.dst_dir)

    def process_images(self):
        if self.src_dir is None:
            tk.messagebox.showinfo("Info Popup", "Please select source directory.")
        else:
            self.detector.process(self.src_dir)

    def __init__(self):
        self.src_dir = None
        self.dst_dir = None
        self.detector = Detector()
        root = tk.Tk()
        root.title("TEM Cluster Detector")
        root.geometry("500x400+200+100")
        root.configure(bg="#f0f0f0")

        button = tk.Button(root, text="Select source directory", bg='#4caf50', fg='white', font=('Arial', 12, 'bold'),
                           command=self.select_source)
        button.pack(padx=10, pady=0)
        button = tk.Button(root, text="Select destination directory", bg='#4caf50', fg='white', font=('Arial', 12, 'bold'),
                           command=self.select_destination)
        button.pack(padx=10, pady=0)
        button = tk.Button(root, text="Process", bg='#4caf50', fg='white', font=('Arial', 12, 'bold'),
                           command=self.process_images)
        button.pack(padx=0, pady=0)
        root.mainloop()