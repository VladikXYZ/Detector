# import json
# import os
# import tkinter as tk
# from tkinter import filedialog
#
#
# STATE_FILE = "directories.json"
#
#
# class Window:
#     def __init__(self):
#     # Create main application window
#         self.root = tk.Tk()
#         root = self.root
#         root.title('Directory Selector GUI')
#
#         # Callback functions to select directories
#
#         last = load_last_dirs()
#         # StringVars to update label text
#         tk.Label(root, text='Source Directory:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
#         self.source_label_var = tk.StringVar(value=last["source"])
#         source_label = tk.Label(root, textvariable=self.source_label_var, width=50, anchor='w')
#         source_label.grid(row=0, column=1, padx=5, pady=5)
#         tk.Button(root, text='Select', command=self.select_source_dir).grid(row=0, column=2, padx=5, pady=5)
#
#         # Output directory row
#         tk.Label(root, text='Output Directory:').grid(row=1, column=0, padx=5, pady=5, sticky='w')
#         self.output_label_var = tk.StringVar(value=last["output"])
#         output_label = tk.Label(root, textvariable=self.output_label_var, width=50, anchor='w')
#         output_label.grid(row=1, column=1, padx=5, pady=5)
#         tk.Button(root, text='Select', command=self.select_output_dir).grid(row=1, column=2, padx=5, pady=5)
#
#         vcmd = (root.register(self.validate_spinbox), '%P')
#
#         tk.Label(root, text="Minimal size:")
#         min_var = tk.StringVar(value="1")
#         min_spinbox = tk.Spinbox(root, from_=1, to=100, textvariable=min_var, validate="key", validatecommand=vcmd)
#
#         tk.Label(root, text="Maximal size:")
#         max_var = tk.StringVar(value="10")
#         max_spinbox = tk.Spinbox(root, from_=1, to=100, textvariable=max_var, validate="key", validatecommand=vcmd)
#
#         tk.Button(root, text='Process', command=self.process_directories).grid(row=4, column=0, columnspan=3, pady=10)
#
#         # Start the GUI loop
#
#         root.protocol("WM_DELETE_WINDOW", self.on_close)
#         root.mainloop()
#
#     def process_directories(self):
#         source = self.source_label_var.get()
#         output = self.output_label_var.get()
#         print(f"Process source: {source}")
#         print(f"Process output: {output}")
#
#     def select_source_dir(self):
#         dirname = filedialog.askdirectory()
#         if dirname:
#             self.source_label_var.set(dirname)
#
#     def select_output_dir(self):
#         dirname = filedialog.askdirectory()
#         if dirname:
#             self.output_label_var.set(dirname)
#
#     def on_close(self):
#         # Save the last directories when closing
#         save_last_dirs(self.source_label_var.get(), self.output_label_var.get())
#         self.root.destroy()
#
#     def validate_spinbox(new_val):
#         return new_val.isdigit() or new_val == ""
#
# def load_last_dirs():
#     if os.path.exists(STATE_FILE):
#         with open(STATE_FILE, "r") as f:
#             return json.load(f)
#     return {"source": "None", "output": "None"}
#
# def save_last_dirs(source, output):
#     with open(STATE_FILE, "w") as f:
#         json.dump({"source": source, "output": output}, f)
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

STATE_FILE = "directories.json"

class Window:
    def __init__(self):
        # Create main application window
        self.root = tk.Tk()
        root = self.root
        root.title('Directory Selector GUI')

        last = load_last_dirs()

        tk.Label(root, text='Source Directory:').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.source_label_var = tk.StringVar(value=last["source"])
        source_label = tk.Label(root, textvariable=self.source_label_var, width=50, anchor='w')
        source_label.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text='Select', command=self.select_source_dir).grid(row=0, column=2, padx=5, pady=5)

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
        self.min_spinbox = tk.Spinbox(root, from_=1, to=100, increment=0.1, textvariable=self.min_var,
                                      validate="key", validatecommand=vcmd)
        self.min_spinbox.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        # Maximal cluster size label + spinbox
        tk.Label(root, text="Maximal size:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.max_var = tk.StringVar(value="10")
        self.max_spinbox = tk.Spinbox(root, from_=1, to=100, increment=0.1, textvariable=self.max_var,
                                      validate="key", validatecommand=vcmd)
        self.max_spinbox.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        tk.Button(root, text='Process', command=self.process_directories).grid(row=4, column=0, columnspan=3, pady=10)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.mainloop()

    def process_directories(self):
        source = self.source_label_var.get()
        output = self.output_label_var.get()

        min_val = self.min_var.get()
        max_val = self.max_var.get()

        if source == "None":
            messagebox.showerror("No source", "Please select source directory")
            return
        if output == "None":
            messagebox.showerror("No output", "Please select output directory")
            return
        if float(min_val) > float(max_val):
            messagebox.showerror("Error", "Minimal size must be smaller than maximal size.")
            return

        print(f"Process source: {source}")
        print(f"Process output: {output}")
        print(f"Minimal size: {min_val}")
        print(f"Maximal size: {max_val}")

    def select_source_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.source_label_var.set(dirname)

    def select_output_dir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.output_label_var.set(dirname)

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

if __name__ == "__main__":
    Window()
