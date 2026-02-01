import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from gemini import  ClusterDetector

STATE_FILE = "directories.json"

class Window:
    def __init__(self, root):
        self.root = root
        self.thread = None
        self.det = ClusterDetector()
        # Create main application window
        root.title('Cluster detector')

        last = load_last_dirs()

        # source directory
        tk.Label(root, text='Source Directory:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.source_label_var = tk.StringVar(value=last["source"])
        source_label = tk.Label(root, textvariable=self.source_label_var, width=50, anchor='w')
        source_label.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text='Select', command=self.select_source_dir).grid(row=0, column=2, padx=5, pady=5)


        # output directory
        tk.Label(root, text='Output Directory:').grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.output_label_var = tk.StringVar(value=last["output"])
        output_label = tk.Label(root, textvariable=self.output_label_var, width=50, anchor='w')
        output_label.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(root, text='Select', command=self.select_output_dir).grid(row=1, column=2, padx=5, pady=5)

        # Register validation command
        vcmd = (root.register(self.validate_spinbox), '%P')

        # Minimal cluster size label + spinbox
        tk.Label(root, text="Minimal size:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.min_var = tk.StringVar(value="1")
        self.min_spinbox = tk.Spinbox(root, from_=0.2, to=50, increment=0.1, textvariable=self.min_var,
                                      validate="key", validatecommand=vcmd)
        self.min_spinbox.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        # Maximal cluster size label + spinbox
        tk.Label(root, text="Maximal size:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.max_var = tk.StringVar(value="10")
        self.max_spinbox = tk.Spinbox(root, from_=0.2, to=50, increment=0.1, textvariable=self.max_var,
                                      validate="key", validatecommand=vcmd)
        self.max_spinbox.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        self.process_button = tk.Button(root, text='Process', command=self.process_directories)
        self.process_button.grid(row=2, column=2, rowspan=2, pady=10)

        self.process_button = tk.Button(root, text='Edit', command=self.process_directories)
        self.process_button.grid(row=4, column=1, rowspan=2, pady=10)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.mainloop()

    def process_directories(self):
        source = self.source_label_var.get()
        output = self.output_label_var.get()

        if source == "None":
            messagebox.showerror("No source", "Please select source directory")
            return
        if output == "None":
            messagebox.showerror("No output", "Please select output directory")
            return
        min_val = self.min_var.get()
        max_val = self.max_var.get()
        m = float(min_val)
        M = float(max_val)
        if m > M:
            messagebox.showerror("Error", "Minimal size must be smaller than maximal size.")
            return
        self.process_button.config(state="disabled")
        self.thread = threading.Thread(target=self.det.process_sample, args=(source, output, m, M), daemon=True)
        self.thread.start()
        self.check_thread()

    def check_thread(self):
        # print("checking")
        if not self.thread.is_alive():
            self.process_button.config(state="normal")
            print("Finished")
        else:
            self.root.after(100, self.check_thread)


    def select_source_dir(self):
        dirname = filedialog.askdirectory()
        if dirname: self.source_label_var.set(dirname)

    def select_output_dir(self):
        dirname = filedialog.askdirectory()
        if dirname: self.output_label_var.set(dirname)

    def on_close(self):
        save_last_dirs(self.source_label_var.get(), self.output_label_var.get())
        self.root.destroy()

    def validate_spinbox(self, new_val):
        return new_val.isdigit() or new_val == ""

def load_last_dirs():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"source": "None", "output": "None"}

def save_last_dirs(source, output):
    with open(STATE_FILE, "w") as f:
        json.dump({"source": source, "output": output}, f)
