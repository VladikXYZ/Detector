import tkinter as tk
from tkinter import filedialog


class Window:
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Experiment Folder")
        if folder_path: self.folder = folder_path
            # print("Selected folder:", folder_path)

    def __init__(self):
        root = tk.Tk()
        root.title("TEM Atom Detector")
        root.geometry("500x400+200+100")
        root.configure(bg="#f0f0f0")

        button = tk.Button(root, text="Select Folder", bg='#4caf50', fg='white', font=('Arial', 12, 'bold'),
                           command=self.select_folder)
        button.pack(padx=30, pady=100)
        root.mainloop()
        folder = None