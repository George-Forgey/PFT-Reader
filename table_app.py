import tkinter as tk
from tkinter import ttk, messagebox
import json
import pyautogui
import os
import shutil
import csv
from PIL import Image, ImageTk

from table_detector import detect_table 
from cell_segmentation import segment_cells
from ocr_paddle import perform_ocr  # Import the OCR function
from interpretation import interpret_pft  # Import the interpretation function

##############################################################################
# Utility to load/save config
##############################################################################
def load_config():
    """
    Load the config.json if it exists, otherwise return a default dictionary.
    (Note: Only numeric table configuration is needed now.)
    """
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    else:
        return {
            "num_rows": 30,
            "num_columns": 8,
            "row_proportions": [],
            "column_proportions": [],
            "decimal_precision": 2,
            "column_titles": [],
            "row_titles": []
        }

def save_config(config):
    """
    Write out the config dictionary to config.json.
    """
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

##############################################################################
# Main App
##############################################################################
class App:
    def __init__(self, master):
        self.master = master
        self.master.title("Table OCR App")
        self.master.geometry("800x600")  # Larger initial window size

        # Main Buttons
        self.run_button = ttk.Button(master, text="Run", command=self.run_button_callback)
        self.run_button.pack(pady=10)

        self.config_button = ttk.Button(master, text="Configure", command=self.configure_table)
        self.config_button.pack(pady=10)

    def run_button_callback(self):
        """
        Full pipeline triggered by the Run button:
         1) Delete existing output folder and table_target.png.
         2) Screenshot the entire screen (saved as table_target.png).
         3) Detect the table using the template (table_template.png).
         4) Segment the cropped table into cells.
         5) Run OCR on the segmented cells and generate CSV.
         6) Interpret the OCR results.
         7) Display the interpretation in a new window with a Copy button.
        """
        # 1) Clean up old files/folders.
        if os.path.exists("output"):
            shutil.rmtree("output")
            print("Old output folder deleted.")
        if os.path.exists("table_target.png"):
            os.remove("table_target.png")
            print("Old table_target.png deleted.")

        # 2) Screenshot of entire screen.
        screenshot = pyautogui.screenshot()
        screenshot.save("table_target.png")
        print("Screenshot saved to table_target.png")

        # 3) Detect table.
        success = detect_table("table_template.png", "table_target.png", output_dir="output", threshold=0.2)
        if success:
            print("Table detection successful. Cropped table saved.")
        else:
            messagebox.showerror("Error", "Table detection failed.")
            return
        
        # 4) Segment cells.
        config_data = load_config()
        segment_cells(config_data, cropped_table_path="output/cropped_table.png")
        print("Cell segmentation completed.")

        # 5) Run OCR.
        ocr_csv_path = perform_ocr()
        print(f"OCR completed. CSV saved at {ocr_csv_path}")
        
        ResultsWindow(self.master, ocr_csv_path)


        # 6) Interpret the OCR results.
        interpretation_text = interpret_pft(ocr_csv_path)
        print("Interpretation complete.")

        # 7) Display the interpretation.
        InterpretationWindow(self.master, interpretation_text)

    def configure_table(self):
        """
        Opens a full-screen overlay for the user to capture a region.
        The captured region is saved as table_template.png, then the TableConfigWindow is launched.
        """
        overlay = BoundingBoxSelector(on_capture_callback=self.open_config_window)
        overlay.run_fullscreen()

    def open_config_window(self, bbox):
        """
        Once a bounding box is defined, capture that region and launch the configuration window.
        """
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            left, top = int(min(x1, x2)), int(min(y1, y2))
            right, bottom = int(max(x1, x2)), int(max(y1, y2))
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                print("Invalid region selected. Screenshot canceled.")
                return
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot_path = "table_template.png"
            screenshot.save(screenshot_path)
            TableConfigWindow(screenshot_path)
        else:
            print("No bounding box selected. Configuration canceled.")

##############################################################################
# Full-screen bounding box selection overlay
##############################################################################
class BoundingBoxSelector:
    def __init__(self, on_capture_callback):
        self.on_capture_callback = on_capture_callback
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.3)
        self.root.attributes("-topmost", True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.canvas = tk.Canvas(self.root, bg="gray", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def run_fullscreen(self):
        self.root.mainloop()

    def on_mouse_down(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = None

    def on_mouse_drag(self, event):
        if self.start_x is not None and self.start_y is not None:
            current_x = self.canvas.canvasx(event.x)
            current_y = self.canvas.canvasy(event.y)
            if self.rect_id is not None:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y,
                current_x, current_y,
                outline="red", width=2, fill=""
            )

    def on_mouse_up(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.root.destroy()
        self.on_capture_callback((self.start_x, self.start_y, end_x, end_y))

##############################################################################
# Table Configuration Window
##############################################################################
class TableConfigWindow:
    def __init__(self, image_path):
        self.image_path = image_path
        self.win = tk.Toplevel()
        self.win.title("Configure Table Template")
        top_frame = tk.Frame(self.win)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(top_frame, text="Columns:").pack(side=tk.LEFT, padx=5)
        self.col_var = tk.IntVar(value=8)
        self.col_entry = ttk.Spinbox(top_frame, from_=1, to=100, textvariable=self.col_var, width=5)
        self.col_entry.pack(side=tk.LEFT)
        tk.Label(top_frame, text="Rows:").pack(side=tk.LEFT, padx=5)
        self.row_var = tk.IntVar(value=30)
        self.row_entry = ttk.Spinbox(top_frame, from_=1, to=100, textvariable=self.row_var, width=5)
        self.row_entry.pack(side=tk.LEFT)
        self.update_btn = ttk.Button(top_frame, text="Update Grid", command=self.update_grid)
        self.update_btn.pack(side=tk.LEFT, padx=5)
        self.save_btn = ttk.Button(top_frame, text="Save Config", command=self.save_config)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.canvas_frame = tk.Frame(self.win)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.original_image = Image.open(self.image_path)
        self.img_width, self.img_height = self.original_image.size
        self.canvas = tk.Canvas(self.canvas_frame, width=self.img_width, height=self.img_height)
        self.canvas.pack()
        self.tk_image = ImageTk.PhotoImage(self.original_image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.vertical_lines = []
        self.horizontal_lines = []
        self.dragging_line = None
        self.dragging_line_orientation = None
        self.canvas.bind("<ButtonPress-1>", self.on_line_click)
        self.canvas.bind("<B1-Motion>", self.on_line_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_line_release)
        self.update_grid()

    def update_grid(self):
        for line_id in self.vertical_lines + self.horizontal_lines:
            self.canvas.delete(line_id)
        self.vertical_lines.clear()
        self.horizontal_lines.clear()
        cols = self.col_var.get()
        rows = self.row_var.get()
        if cols > 1:
            for i in range(1, cols):
                proportion = i / cols
                x = self.img_width * proportion
                line_id = self.canvas.create_line(x, 0, x, self.img_height, fill="blue", width=2)
                self.vertical_lines.append(line_id)
        if rows > 1:
            for j in range(1, rows):
                proportion = j / rows
                y = self.img_height * proportion
                line_id = self.canvas.create_line(0, y, self.img_width, y, fill="blue", width=2)
                self.horizontal_lines.append(line_id)

    def on_line_click(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            if item[0] in self.vertical_lines:
                self.dragging_line = item[0]
                self.dragging_line_orientation = 'vertical'
            elif item[0] in self.horizontal_lines:
                self.dragging_line = item[0]
                self.dragging_line_orientation = 'horizontal'

    def on_line_drag(self, event):
        if self.dragging_line is not None:
            if self.dragging_line_orientation == 'vertical':
                new_x = max(0, min(event.x, self.img_width))
                self.canvas.coords(self.dragging_line, new_x, 0, new_x, self.img_height)
            else:
                new_y = max(0, min(event.y, self.img_height))
                self.canvas.coords(self.dragging_line, 0, new_y, self.img_width, new_y)

    def on_line_release(self, event):
        self.dragging_line = None
        self.dragging_line_orientation = None

    def save_config(self):
        column_proportions = []
        row_proportions = []
        for line_id in self.vertical_lines:
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            proportion = x1 / self.img_width
            column_proportions.append(proportion)
        for line_id in self.horizontal_lines:
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            proportion = y1 / self.img_height
            row_proportions.append(proportion)
        column_proportions.sort()
        row_proportions.sort()
        column_proportions.insert(0, 0.00)
        column_proportions.append(0.9999)
        row_proportions.insert(0, 0.00)
        row_proportions.append(0.9999)
        config_data = load_config()
        cols = self.col_var.get()
        rows = self.row_var.get()
        config_data["column_proportions"] = column_proportions
        config_data["row_proportions"] = row_proportions
        config_data["num_columns"] = cols
        config_data["num_rows"] = rows
        save_config(config_data)
        print("Configuration saved to config.json")

##############################################################################
# Interpretation Window (Display OCR Interpretation)
##############################################################################
class InterpretationWindow:
    def __init__(self, master, interpretation_text):
        self.win = tk.Toplevel(master)
        self.win.title("PFT Interpretation")
        self.win.geometry("600x400")
        
        # Create a Text widget with scrollbar.
        frame = tk.Frame(self.win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        self.text_box = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set)
        self.text_box.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_box.yview)
        
        # Insert interpretation text.
        self.text_box.insert("1.0", interpretation_text)
        self.text_box.config(state="disabled")
        
        # Copy Button.
        copy_btn = ttk.Button(self.win, text="Copy Text", command=self.copy_text)
        copy_btn.pack(pady=5)
    
    def copy_text(self):
        text = self.text_box.get("1.0", "end-1c")
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        messagebox.showinfo("Copied", "Interpretation text copied to clipboard.")
        
class ResultsWindow:
    def __init__(self, master, csv_path):
        self.win = tk.Toplevel(master)
        self.win.title("OCR Results")
        # Create a frame for the treeview and scrollbar.
        frame = tk.Frame(self.win)
        frame.pack(fill="both", expand=True)
        
        # Create the Treeview widget.
        self.tree = ttk.Treeview(frame, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Add vertical scrollbar.
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Read CSV data.
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            data = list(reader)
        
        if not data:
            tk.Label(self.win, text="No data found in CSV.").pack(padx=10, pady=10)
            return
        
        # Set up the columns based on the header row.
        headers = data[0]
        self.tree["columns"] = headers
        for header in headers:
            self.tree.heading(header, text=header)
            self.tree.column(header, width=100, anchor="center")
        
        # Insert remaining rows.
        for row in data[1:]:
            self.tree.insert("", "end", values=row)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
