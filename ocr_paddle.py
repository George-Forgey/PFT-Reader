import cv2
import numpy as np
import os
import csv
from paddleocr import PaddleOCR
import re

# ==================================
# 1. TABLE & OCR CONFIGURATIONS
# ==================================


column_titles = [
    "Variable",    # 0
    "Pre",         # 1
    "ZScore",      # 2
    "LLN",         # 3
    "%PredPre",    # 4
    "Post",        # 5
    "ZScorePost",  # 6
    "%PredPost",   # 7
    "%ChangePost"  # 8
]

num_columns = 9
num_rows = 30

row_titles = [
    "",             # 0
    "",             # 1 (empty row)
    "FVC",          # 2
    "FEV1",         # 3
    "FEV1/FVC",     # 4
    "FEF 25%",      # 5
    "FEF 75%",      # 6
    "FEF 25-75%",   # 7
    "FEF Max",      # 8
    "FIVC",         # 9
    "Test Grade",   #10
    "",             #11 (empty row)
    "",             #12 (empty row)
    "SVC",          #13
    "IC",           #14
    "ERV",          #15
    "",             #16 (empty row)
    "",             #17 (empty row)
    "TGV",          #18
    "RV Pleth",     #19
    "TLC Pleth",    #20
    "RV/TLC Pleth", #21
    "",             #22 (empty row)
    "",             #23 (empty row)
    "DLCOunc",      #24
    "DLCOcor",      #25
    "DL/VA",        #26
    "VA",           #27
    "Kco",          #28
    "ATS Grades"    #29
]

empty_rows = [1, 11, 12, 16, 17, 22, 23]
character_rows = [10, 29]   # Rows that contain text
columns_percent = [4, 7, 8] # Columns that store % values

# 2. PaddleOCR Initialization
ocr = PaddleOCR(
    use_angle_cls=False,
    lang='en',
    use_gpu=True
)

# 3. File / Directory Paths
cells_output_dir = os.path.join('output', 'cells')
csv_output_path = os.path.join('output', 'table_data_enhanced.csv')

# 4. Main Table-Reading Logic
with open(csv_output_path, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(column_titles)  # Write 9 column headers

    for row_idx in range(num_rows):
        row_data = []

        # Row title
        row_title = row_titles[row_idx] if row_idx < len(row_titles) else ""
        row_data.append(row_title)

        # If empty row, fill with blanks
        if row_idx in empty_rows:
            row_data.extend([""] * (num_columns - 1))
            csv_writer.writerow(row_data)
            continue

        # Check if this row should contain character data
        is_char_row = row_idx in character_rows

        # Temporary storage for columns in this row
        # We'll fill row_data fully, then fix signs afterwards
        numeric_values = ["" for _ in range(num_columns - 1)]  # we already placed row_title at index 0
        for col_idx in range(1, num_columns):
            cell_filename = f'cell_row{row_idx}_col{col_idx}.png'
            cell_path = os.path.join(cells_output_dir, cell_filename)

            # Read as grayscale
            cell_image = cv2.imread(cell_path, cv2.IMREAD_GRAYSCALE)
            if cell_image is None:
                print(f"Warning: Cell image not found at {cell_path}")
                numeric_values[col_idx - 1] = ""
                continue

            # Single-line OCR (no detection, no angle classification)
            result = ocr.ocr(cell_image, det=False, cls=False)
            cell_text = ""

            if result and len(result) > 0:
                raw_text_tuple = result[0][0]   # (text, confidence)
                raw_text = raw_text_tuple[0]   # just the text

                if not is_char_row:
                    # We want only digits for numeric columns
                    # ignoring signs and decimals for now
                    # e.g. "1234" => 12.34 eventually
                    matches = re.findall(r'\d+', raw_text)
                    if matches:
                        concatenated = "".join(matches)

                        # Attempt to convert to int and optionally shift decimal
                        try:
                            integer_val = int(concatenated)

                            # If this column is not a % column
                            if col_idx not in columns_percent:
                                # Insert decimal by dividing by 100
                                decimal_val = integer_val / 100.0
                                cell_text = f"{decimal_val:.2f}"
                            else:
                                # For % columns, keep as integer string
                                cell_text = str(integer_val)
                        except ValueError:
                            cell_text = ""
                else:
                    # If character row => keep entire recognized text
                    cell_text = raw_text

            numeric_values[col_idx - 1] = cell_text

        # Now, row_data = [row_title], numeric_values = [col1..col8]
        # Combine them
        row_data.extend(numeric_values)

        # 5. Determine signs for columns 2 (ZScore), 6 (ZScorePost), 8 (%ChangePost)
        # Only do this if row_data is numeric-based (not char_row)
        # But user wants sign logic even if not numeric row? => logic says no
        if not is_char_row:
            try:
                # a) Column 2 sign => based on col4 > 100
                # row_data indices: 0 is row_title, so col2 => row_data[2], col4 => row_data[4]
                zscore_val = row_data[2]
                percent_pre = row_data[4]  # e.g. 101 => sign = '+', else '-'
                if zscore_val and percent_pre:
                    # Convert percent_pre to float
                    pp_float = float(percent_pre)
                    z_float = float(zscore_val)
                    if pp_float > 100:
                        # Ensure zscore is positive
                        row_data[2] = f"+{abs(z_float):.2f}"
                    else:
                        # Ensure zscore is negative
                        row_data[2] = f"-{abs(z_float):.2f}"
            except ValueError:
                pass

            try:
                # b) Column 6 sign => based on col7 > 100
                # col6 => row_data[6], col7 => row_data[7]
                zscore_post_val = row_data[6]
                percent_post = row_data[7]
                if zscore_post_val and percent_post:
                    pp_float = float(percent_post)
                    z_float = float(zscore_post_val)
                    if pp_float > 100:
                        row_data[6] = f"+{abs(z_float):.2f}"
                    else:
                        row_data[6] = f"-{abs(z_float):.2f}"
            except ValueError:
                pass

            try:
                # c) Column 8 sign => based on post (col5) - pre (col1)
                # col8 => row_data[8], col5 => row_data[5], col1 => row_data[1]
                change_val = row_data[8]  # e.g. '12' or '12.34' from above logic
                pre_str = row_data[1]
                post_str = row_data[5]
                if change_val and pre_str and post_str:
                    pre_f = float(pre_str)
                    post_f = float(post_str)
                    # If post-pre > 0 => sign is '+', else '-'
                    change_f = float(change_val)
                    if (post_f - pre_f) > 0:
                        row_data[8] = f"+{abs(change_f):.2f}"
                    else:
                        row_data[8] = f"-{abs(change_f):.2f}"
            except ValueError:
                pass

        # Write final row_data
        csv_writer.writerow(row_data)

print(f"OCR results saved to {csv_output_path}")
