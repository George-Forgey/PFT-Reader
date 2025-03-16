import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json
import pyautogui
import os
from PIL import Image, ImageTk

from table_detector import detect_table 
from cell_segmentation import segment_cells



##############################################################################
# Utility to load/save config
##############################################################################
def load_config():
    """
    Load the config.json if it exists, otherwise return default dictionary.
    """
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    else:
        return {
            "num_rows": 3,
            "num_columns": 3,
            "row_proportions": [],
            "column_proportions": [],
            "row_titles": [],
            "column_titles": []
        }


def save_config(config):
    """
    Write out the config dictionary to config.json
    """
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)


##############################################################################
# Main App
##############################################################################
class App:
    def __init__(self, master):
        self.master = master
        self.master.title("Main Window")

        # Main Buttons
        self.run_button = ttk.Button(master, text="Run", command=self.run_button_callback)
        self.run_button.pack(pady=5)

        self.config_button = ttk.Button(master, text="Configure", command=self.configure_table)
        self.config_button.pack(pady=5)

        # New "Titles" button
        self.titles_button = ttk.Button(master, text="Titles", command=self.open_titles_window)
        self.titles_button.pack(pady=5)

        # -- NEW "Technical" button
        self.technical_button = ttk.Button(master, text="Technical", command=self.open_technical_window)
        self.technical_button.pack(pady=5)
        
        self.read_button = ttk.Button(master, text="Read", command=self.read_button_callback)
        self.read_button.pack(pady=5)
    
    
    def run_button_callback(self):
        """
        Placeholder function for the "Run" button.
        (Not implemented per instructions.)
        """
        pass

    def configure_table(self):
        """
        1) Opens a full-screen overlay so the user can click-drag-release
           to capture a region. The captured region is saved to table_template.png.
        2) Launches the TableConfigWindow to allow customizing row/column lines.
        """
        overlay = BoundingBoxSelector(on_capture_callback=self.open_config_window)
        overlay.run_fullscreen()

    def open_config_window(self, bbox):
        """
        Once the bounding box is defined, take the screenshot and open the next window.
        """
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            # Ensure x1,y1 is top-left and x2,y2 is bottom-right
            left, top = int(min(x1, x2)), int(min(y1, y2))
            right, bottom = int(max(x1, x2)), int(max(y1, y2))

            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                print("Invalid region selected. Screenshot canceled.")
                return

            # Capture the screenshot
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot_path = "table_template.png"
            screenshot.save(screenshot_path)

            # Open the table config window
            TableConfigWindow(screenshot_path)
        else:
            print("No bounding box selected. Configuration canceled.")

    def open_titles_window(self):
        """
        Open the TitlesWindow so the user can edit row and column titles.
        """
        TitlesWindow()
        
    def open_technical_window(self):
        TechnicalWindow()
        
    def read_button_callback(self):
        """
        1) Take a screenshot of the current screen, name it table_target.png
        2) Call detect_table(...) to create cropped_table.png
        3) Open a new window that displays an empty table skeleton.
        """
        
        # Screenshot entire screen
        screenshot = pyautogui.screenshot()
        screenshot.save("table_target.png")
        print("Screenshot saved to table_target.png")

        # Call detect_table function
        success = detect_table("table_template.png", "table_target.png", output_dir="output", threshold=0.2)
        if success:
            print("Table detection successful. Cropped table saved.")
        else:
            print("Table detection failed.")
        
            # 3) segment cells => output/cells/...
        config_data = load_config()
        segment_cells(config_data, cropped_table_path="output/cropped_table.png")

        # Open the "ReadingWindow" to show the table skeleton
        ReadingWindow()


##############################################################################
# Full-screen bounding box selection overlay
##############################################################################
class BoundingBoxSelector:
    """
    Creates a full-screen overlay window to select a bounding box with the mouse.
    Returns the bounding box coordinates (x1, y1, x2, y2) when done.
    """
    def __init__(self, on_capture_callback):
        self.on_capture_callback = on_capture_callback
        
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)  # No window decorations
        self.root.attributes("-alpha", 0.3)  # Semi-transparent
        self.root.attributes("-topmost", True)

        # Manually set the window to fill the screen
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
        end_y = self.canvas.canvasx(event.y)  # <-- If you want consistent coords, but typically event.y
        # NOTE: The above might be a copy/paste slip. Usually we do:
        end_y = self.canvas.canvasy(event.y)
        self.root.destroy()
        self.on_capture_callback((self.start_x, self.start_y, end_x, end_y))


##############################################################################
# Table Configuration Window
##############################################################################
class TableConfigWindow:
    """
    Window that displays the screenshot, allows user to specify
    number of columns/rows, and interactively drag lines.
    Also saves num_rows and num_columns to config.json.
    """
    def __init__(self, image_path):
        self.image_path = image_path

        self.win = tk.Toplevel()
        self.win.title("Configure Table Template")

        # Top frame for entries
        top_frame = tk.Frame(self.win)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(top_frame, text="Columns:").pack(side=tk.LEFT, padx=5)
        self.col_var = tk.IntVar(value=3)
        # Spinbox up to 100 - enough for large tables
        self.col_entry = ttk.Spinbox(top_frame, from_=1, to=100, textvariable=self.col_var, width=5)
        self.col_entry.pack(side=tk.LEFT)

        tk.Label(top_frame, text="Rows:").pack(side=tk.LEFT, padx=5)
        self.row_var = tk.IntVar(value=3)
        # Spinbox up to 100 - enough for large tables
        self.row_entry = ttk.Spinbox(top_frame, from_=1, to=100, textvariable=self.row_var, width=5)
        self.row_entry.pack(side=tk.LEFT)

        self.update_btn = ttk.Button(top_frame, text="Update Grid", command=self.update_grid)
        self.update_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = ttk.Button(top_frame, text="Save Config", command=self.save_config)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # Load and display the image in a Canvas
        self.canvas_frame = tk.Frame(self.win)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.original_image = Image.open(self.image_path)
        self.img_width, self.img_height = self.original_image.size

        self.canvas = tk.Canvas(self.canvas_frame, width=self.img_width, height=self.img_height)
        self.canvas.pack()

        self.tk_image = ImageTk.PhotoImage(self.original_image)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        # Store lines (vertical & horizontal) as lists of canvas line IDs
        self.vertical_lines = []
        self.horizontal_lines = []

        # Current line being dragged
        self.dragging_line = None
        self.dragging_line_orientation = None

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_line_click)
        self.canvas.bind("<B1-Motion>", self.on_line_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_line_release)

        # Initially draw default grid
        self.update_grid()

    def update_grid(self):
        """
        Draw vertical and horizontal lines based on user-defined columns/rows.
        Spread them evenly at first.
        """
        # Remove existing lines
        for line_id in self.vertical_lines + self.horizontal_lines:
            self.canvas.delete(line_id)
        self.vertical_lines.clear()
        self.horizontal_lines.clear()

        cols = self.col_var.get()
        rows = self.row_var.get()

        # Evenly spaced proportions
        if cols > 1:
            for i in range(1, cols):
                proportion = i / cols
                x = self.img_width * proportion
                line_id = self.canvas.create_line(
                    x, 0, x, self.img_height, fill="blue", width=2
                )
                self.vertical_lines.append(line_id)

        if rows > 1:
            for j in range(1, rows):
                proportion = j / rows
                y = self.img_height * proportion
                line_id = self.canvas.create_line(
                    0, y, self.img_width, y, fill="blue", width=2
                )
                self.horizontal_lines.append(line_id)

    def on_line_click(self, event):
        """
        If the user clicks near a line, select that line for dragging.
        """
        item = self.canvas.find_closest(event.x, event.y)
        if item:
            if item[0] in self.vertical_lines:
                self.dragging_line = item[0]
                self.dragging_line_orientation = 'vertical'
            elif item[0] in self.horizontal_lines:
                self.dragging_line = item[0]
                self.dragging_line_orientation = 'horizontal'

    def on_line_drag(self, event):
        """
        Drag the currently selected line.
        """
        if self.dragging_line is not None:
            if self.dragging_line_orientation == 'vertical':
                new_x = max(0, min(event.x, self.img_width))
                self.canvas.coords(
                    self.dragging_line,
                    new_x, 0, new_x, self.img_height
                )
            else:
                new_y = max(0, min(event.y, self.img_height))
                self.canvas.coords(
                    self.dragging_line,
                    0, new_y, self.img_width, new_y
                )

    def on_line_release(self, event):
        """
        Release the line.
        """
        self.dragging_line = None
        self.dragging_line_orientation = None

    def save_config(self):
        """
        Save column/row line proportions PLUS the number of rows/columns.
        """
        column_proportions = []
        row_proportions = []

        # Retrieve line positions for columns
        for line_id in self.vertical_lines:
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            proportion = x1 / self.img_width  # x1 == x2
            column_proportions.append(proportion)

        # Retrieve line positions for rows
        for line_id in self.horizontal_lines:
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            proportion = y1 / self.img_height  # y1 == y2
            row_proportions.append(proportion)

        column_proportions.sort()
        row_proportions.sort()
        
        column_proportions.insert(0,0.00)
        column_proportions.append(0.9999)
        
        row_proportions.insert(0,0.00)
        row_proportions.append(0.9999)
        
        
        config_data = load_config()

        cols = self.col_var.get()
        rows = self.row_var.get()

        # Update relevant entries
        config_data["column_proportions"] = column_proportions
        config_data["row_proportions"] = row_proportions
        config_data["num_columns"] = cols
        config_data["num_rows"] = rows

        save_config(config_data)
        print("Configuration saved to config.json")


##############################################################################
# Titles Window (with scrolling + top-left cell fix)
##############################################################################
# --- Below is the revised TitlesWindow class. The key change:
# 1) Remove "self.row_titles[0] = ''"
# 2) Insert an empty string at the start of row_titles so the user’s first named row stays "1".
# 3) Loop over all row_titles (including the inserted one) when building entries.

class TitlesWindow:
    """
    Allows the user to specify a title/name for each row and column.
    For a table with num_rows in config, one of those rows is the top-left
    "header row" shared with columns. Therefore, we only display (num_rows - 1)
    editable row title fields. When saving, we insert "" at index 0 to keep
    that hidden top-left cell in row_titles[0].
    """
    def __init__(self):
        self.win = tk.Toplevel()
        self.win.title("Set Table Titles")

        # Load config
        self.config_data = load_config()

        self.num_rows = self.config_data.get("num_rows", 3)
        self.num_cols = self.config_data.get("num_columns", 3)

        # Existing titles, or placeholders
        self.row_titles = self.config_data.get("row_titles", [])
        self.column_titles = self.config_data.get("column_titles", [])

        # If row_titles[0] = "", remove it (the hidden top-left entry),
        # so we can let the user see only num_rows-1 editable titles.
        if self.row_titles and self.row_titles[0] == "":
            self.row_titles.pop(0)  # remove hidden blank

        # Now, we ONLY need (num_rows - 1) actual row titles for the user to edit
        needed = max(self.num_rows - 1, 0)  # guard if num_rows < 1
        if len(self.row_titles) < needed:
            # extend with placeholders if too short
            self.row_titles += [f"Row {i+1}" for i in range(len(self.row_titles), needed)]
        self.row_titles = self.row_titles[:needed]  # truncate if too long

        # Ensure column_titles has exactly num_cols items
        if len(self.column_titles) < self.num_cols:
            self.column_titles += [f"Col {j+1}" for j in range(len(self.column_titles), self.num_cols)]
        self.column_titles = self.column_titles[: self.num_cols]

        # Build a scrollable frame
        container = tk.Frame(self.win)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(self.win, orient="horizontal", command=canvas.xview)
        scrollbar_x.pack(side="bottom", fill="x")

        self.scrollable_frame = tk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Management frame (Rows/Columns spinboxes + Refresh)
        self.manage_frame = tk.Frame(self.scrollable_frame)
        self.manage_frame.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        tk.Label(self.manage_frame, text="Rows:").pack(side=tk.LEFT, padx=5)
        self.entry_rows_var = tk.IntVar(value=self.num_rows)
        row_spin = ttk.Spinbox(self.manage_frame, from_=1, to=999, textvariable=self.entry_rows_var, width=5)
        row_spin.pack(side=tk.LEFT)

        tk.Label(self.manage_frame, text="Columns:").pack(side=tk.LEFT, padx=5)
        self.entry_cols_var = tk.IntVar(value=self.num_cols)
        col_spin = ttk.Spinbox(self.manage_frame, from_=1, to=999, textvariable=self.entry_cols_var, width=5)
        col_spin.pack(side=tk.LEFT)

        refresh_btn = ttk.Button(self.manage_frame, text="Refresh", command=self.refresh_titles)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # Column Titles
        col_label = tk.Label(self.scrollable_frame, text="Column Titles:")
        col_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.column_entries = []
        for c in range(self.num_cols):
            entry_var = tk.StringVar(value=self.column_titles[c])
            entry = ttk.Entry(self.scrollable_frame, textvariable=entry_var, width=20)
            entry.grid(row=2, column=c, padx=5, pady=5)
            self.column_entries.append(entry)

        # Row Titles
        row_label = tk.Label(self.scrollable_frame, text="Row Titles:")
        row_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.row_entries = []
        for i, row_title in enumerate(self.row_titles):
            entry_var = tk.StringVar(value=row_title)
            entry = ttk.Entry(self.scrollable_frame, textvariable=entry_var, width=20)
            # row=4+i ensures these appear below the label
            entry.grid(row=4 + i, column=0, padx=5, pady=5, sticky="w")
            self.row_entries.append(entry)

        # Save button
        save_btn = ttk.Button(self.win, text="Save Titles", command=self.save_titles)
        save_btn.pack(pady=5)

    def refresh_titles(self):
        # Remove any existing entry widgets
        for w in self.column_entries + self.row_entries:
            w.destroy()
        self.column_entries.clear()
        self.row_entries.clear()

        # Update num_rows/num_cols from the spinboxes
        self.num_rows = self.entry_rows_var.get()
        self.num_cols = self.entry_cols_var.get()

        # Remove hidden blank if present (index 0)
        if self.row_titles and self.row_titles[0] == "":
            self.row_titles.pop(0)

        # We want exactly (num_rows - 1) user-rows
        needed = max(self.num_rows - 1, 0)
        if len(self.row_titles) < needed:
            self.row_titles += [f"Row {i+1}" for i in range(len(self.row_titles), needed)]
        self.row_titles = self.row_titles[:needed]

        # Ensure column_titles is length num_cols
        if len(self.column_titles) < self.num_cols:
            self.column_titles += [f"Col {j+1}" for j in range(len(self.column_titles), self.num_cols)]
        self.column_titles = self.column_titles[: self.num_cols]

        # Rebuild "Column Titles" label + entries
        col_label = tk.Label(self.scrollable_frame, text="Column Titles:")
        col_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        for c in range(self.num_cols):
            entry_var = tk.StringVar(value=self.column_titles[c])
            entry = ttk.Entry(self.scrollable_frame, textvariable=entry_var, width=20)
            entry.grid(row=2, column=c, padx=5, pady=5)
            self.column_entries.append(entry)

        # Rebuild "Row Titles" label + entries
        row_label = tk.Label(self.scrollable_frame, text="Row Titles:")
        row_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        for i, row_title in enumerate(self.row_titles):
            entry_var = tk.StringVar(value=row_title)
            entry = ttk.Entry(self.scrollable_frame, textvariable=entry_var, width=20)
            entry.grid(row=4 + i, column=0, padx=5, pady=5, sticky="w")
            self.row_entries.append(entry)

    def save_titles(self):
        """
        Save column_titles and row_titles into config.json.
        We'll insert "" at the beginning of the row_titles list
        to account for the top-left "header" cell that belongs to both a row & a column.
        """
        new_column_titles = [e.get() for e in self.column_entries]
        user_rows = [e.get() for e in self.row_entries]

        # Insert hidden blank at front
        new_row_titles = [""]
        new_row_titles.extend(user_rows)

        # Update config and save
        self.config_data["column_titles"] = new_column_titles
        self.config_data["row_titles"] = new_row_titles

        save_config(self.config_data)
        print("Titles saved to config.json")
        self.win.destroy()
        
##############################################################################
# TechnicalWindow: For OCR-related preferences
##############################################################################
class TechnicalWindow:
    def __init__(self):
        self.win = tk.Toplevel()
        self.win.title("Technical OCR Settings")

        self.config_data = load_config()

        # Existing (or default) config values
        self.empty_rows = self.config_data.get("empty_rows", [1, 11, 12, 16, 17, 22, 23])
        self.character_rows = self.config_data.get("character_rows", [10, 29])
        self.columns_percent = self.config_data.get("columns_percent", [4, 7, 8])
        self.decimal_precision = self.config_data.get("decimal_precision", 2)

        # -- NEW: rows_percent
        self.rows_percent = self.config_data.get("rows_percent", [2, 5, 9])  # default examples
        rows_percent_str = ",".join(map(str, self.rows_percent))

        # Convert existing lists to comma-separated strings for display
        empty_rows_str = ",".join(map(str, self.empty_rows))
        char_rows_str = ",".join(map(str, self.character_rows))
        percent_cols_str = ",".join(map(str, self.columns_percent))

        # Label + Entry: empty_rows
        tk.Label(self.win, text="Empty Rows (comma-separated):").pack(anchor="w", padx=5, pady=2)
        self.empty_rows_var = tk.StringVar(value=empty_rows_str)
        ttk.Entry(self.win, textvariable=self.empty_rows_var, width=40).pack(padx=10, pady=2)

        # Label + Entry: character_rows
        tk.Label(self.win, text="Character Rows (comma-separated):").pack(anchor="w", padx=5, pady=2)
        self.character_rows_var = tk.StringVar(value=char_rows_str)
        ttk.Entry(self.win, textvariable=self.character_rows_var, width=40).pack(padx=10, pady=2)

        # Label + Entry: columns_percent
        tk.Label(self.win, text="Columns for % values (comma-separated):").pack(anchor="w", padx=5, pady=2)
        self.columns_percent_var = tk.StringVar(value=percent_cols_str)
        ttk.Entry(self.win, textvariable=self.columns_percent_var, width=40).pack(padx=10, pady=2)

        # Label + Entry: rows_percent  (NEW)
        tk.Label(self.win, text="Rows for % values (comma-separated):").pack(anchor="w", padx=5, pady=2)
        self.rows_percent_var = tk.StringVar(value=rows_percent_str)
        ttk.Entry(self.win, textvariable=self.rows_percent_var, width=40).pack(padx=10, pady=2)

        # Spinbox: decimal_precision
        tk.Label(self.win, text="Decimal Precision:").pack(anchor="w", padx=5, pady=2)
        self.decimal_precision_var = tk.IntVar(value=self.decimal_precision)
        ttk.Spinbox(self.win, from_=0, to=10, textvariable=self.decimal_precision_var, width=5).pack(padx=10, pady=2)

        # Save button
        save_btn = ttk.Button(self.win, text="Save Technical Settings", command=self.save_technical_settings)
        save_btn.pack(pady=10)

    def save_technical_settings(self):
        """
        Parse user input, update config, and save to config.json
        """
        def parse_int_list(s):
            if not s.strip():
                return []
            return [int(x.strip()) for x in s.split(",") if x.strip().isdigit()]

        # Parse each comma-separated string
        new_empty_rows = parse_int_list(self.empty_rows_var.get())
        new_char_rows = parse_int_list(self.character_rows_var.get())
        new_percent_cols = parse_int_list(self.columns_percent_var.get())
        new_rows_percent = parse_int_list(self.rows_percent_var.get())  # NEW
        new_decimal_precision = self.decimal_precision_var.get()

        self.config_data["empty_rows"] = new_empty_rows
        self.config_data["character_rows"] = new_char_rows
        self.config_data["columns_percent"] = new_percent_cols
        self.config_data["rows_percent"] = new_rows_percent  # Store new field
        self.config_data["decimal_precision"] = new_decimal_precision

        save_config(self.config_data)
        print("Technical settings saved to config.json")

        self.win.destroy()


##############################################################################
# 3) Add a new class ReadingWindow to display the table skeleton
##############################################################################

class ReadingWindow:
    """
    Creates a new window that displays an empty table of size
    num_rows x num_columns, as stored in config.json.
    """
    def __init__(self):
        self.config_data = load_config()
        self.num_rows = self.config_data.get("num_rows", 3)
        self.num_cols = self.config_data.get("num_columns", 3)

        self.win = tk.Toplevel()
        self.win.title("Table Reading Results (Skeleton)")

        # Create a frame to hold the table
        table_frame = tk.Frame(self.win)
        table_frame.pack(padx=10, pady=10)

        # Build a simple table skeleton of labels
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                cell_label = tk.Label(table_frame, text=f"R{r}C{c}", borderwidth=1, relief="solid", width=10)
                cell_label.grid(row=r, column=c, padx=1, pady=1)




##############################################################################
# Run the application
##############################################################################
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
