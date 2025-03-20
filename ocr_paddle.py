import os
import json
import csv
import cv2
from paddleocr import PaddleOCR

def perform_ocr(config_path="config.json",
                cells_output_dir=os.path.join('output', 'cells'),
                csv_output_path=os.path.join('output', 'table_data.csv')):
    """
    Loops over the cells folder, performs OCR on non-title cells,
    post-processes the numeric values, applies sign corrections, and
    writes the complete table (including the title row and column) to a CSV.
    
    Assumptions:
      - The cells folder contains the entire grid (including title row (row 0)
        and title column (column 0)).
      - OCR is not run on title cells; these are provided via config.
      - The CSV's first row is the column_titles list.
      - For each subsequent row, the first cell is taken from row_titles.
      - The top-left cell (0,0) is the first entry from column_titles.
      
    Post-processing:
      1. Decimal formatting:
         - For most cells: remove any existing decimal point and then insert a new decimal point
           two characters from the end (to yield two-decimal precision).
         - Exception: cells at (row 10, col 1) and (row 29, col 1) are left unmodified.
         - Exception: cells in columns 4, 7, and 8 (1-indexed) are percent values and should have
           no decimals (simply remove any periods).
      
      2. Sign correction for signed-data:
         - For column 2 (i.e. CSV index 2): examine the corresponding cell in column 4 (index 4);
           if that value is >= 100, prefix a '+' to the cell in column 2; otherwise, prefix a '-'.
         - For column 6 (index 6): examine the corresponding cell in column 7 (index 7);
           if that value is >= 100, prefix a '+'; else, '-'.
         - For column 8 (index 8): compare the values in column 5 (index 5) and column 1 (index 1);
           if (value in col5 - value in col1) is >= 0, prefix a '+', else prefix a '-'.
    """
    # Load configuration.
    with open(config_path, "r") as f:
        config = json.load(f)
    
    total_rows = config.get("num_rows", 0)         # Total rows (including title row)
    total_columns = config.get("num_columns", 0)     # Total columns (including title column)
    column_titles = config.get("column_titles", [])
    row_titles = config.get("row_titles", [])
    
    # Initialize OCR engine.
    ocr = PaddleOCR(use_angle_cls=False, lang='en', use_gpu=True)
    
    # Prepare CSV data as a 2D list.
    # First row: use the column_titles list.
    csv_data = [column_titles]
    
    # Process each non-title row.
    for i in range(1, total_rows):
        row_data = []
        # First cell of each row: row title.
        row_data.append(row_titles[i] if i < len(row_titles) else "")
        # Process OCR for each non-title cell.
        for j in range(1, total_columns):
            cell_filename = f"cell_row{i}_col{j}.png"
            cell_path = os.path.join(cells_output_dir, cell_filename)
            cell_image = cv2.imread(cell_path, cv2.IMREAD_GRAYSCALE)
            if cell_image is None:
                print(f"Warning: Cell image not found at {cell_path}")
                row_data.append("")
                continue
            result = ocr.ocr(cell_image, det=False, cls=False)
            text = result[0][0][0] if result and len(result) > 0 else ""
            
            # --- Decimal post-processing ---
            # Exceptions: do not modify cell if it is at (row 10, col 1) or (row 29, col 1)
            # (Note: i and j are the grid indices where i>=1 and j>=1)
            if text != "":
                if (i == 10 and j == 1) or (i == 29 and j == 1):
                    processed = text
                # For percent-value cells (columns 4, 7, 8; i.e. j in {4, 7, 8}), remove any decimals.
                elif j in {4, 7, 8}:
                    processed = text.replace('.', '')
                else:
                    # Remove any existing decimal point.
                    digits = text.replace('.', '')
                    # Ensure there are at least three digits to allow a decimal insertion.
                    if len(digits) < 3:
                        digits = digits.zfill(3)
                    processed = digits[:-2] + '.' + digits[-2:]
            else:
                processed = ""
            row_data.append(processed)
        csv_data.append(row_data)
    
    # --- Sign correction ---
    # The signed-data columns are 2, 6, 8 (1-indexed), which correspond to indices 2, 6, 8 in each data row.
    # Process each data row (skip header row).
    for r in range(1, len(csv_data)):
        row = csv_data[r]
        # For column 2: check column 4.
        try:
            cell_val = row[2]
            ref_val = row[4]
            if cell_val and ref_val:
                # Remove any existing sign.
                cell_val = cell_val.lstrip("+-")
                num_cell = float(cell_val)
                num_ref = float(ref_val)
                if num_ref >= 100:
                    row[2] = f"+{num_cell:.2f}"
                else:
                    row[2] = f"-{num_cell:.2f}"
        except Exception:
            pass
        
        # For column 6: check column 7.
        try:
            cell_val = row[6]
            ref_val = row[7]
            if cell_val and ref_val:
                cell_val = cell_val.lstrip("+-")
                num_cell = float(cell_val)
                num_ref = float(ref_val)
                if num_ref >= 100:
                    row[6] = f"+{num_cell:.2f}"
                else:
                    row[6] = f"-{num_cell:.2f}"
        except Exception:
            pass
        
        # For column 8: compare column 5 and column 1.
        try:
            cell_val = row[8]
            pre_val = row[1]
            post_val = row[5]
            if cell_val and pre_val and post_val:
                cell_val = cell_val.lstrip("+-")
                num_cell = float(cell_val)
                num_pre = float(pre_val)
                num_post = float(post_val)
                if (num_post - num_pre) >= 0:
                    row[8] = f"+{num_cell:.2f}"
                else:
                    row[8] = f"-{num_cell:.2f}"
        except Exception:
            pass

    # Write the complete CSV data to file.
    with open(csv_output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(csv_data)
    
    print(f"OCR results with post-processing, sign corrections, and titles saved to {csv_output_path}")
    return csv_output_path
