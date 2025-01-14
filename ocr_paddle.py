import cv2
import numpy as np
import os
import csv
from paddleocr import PaddleOCR
import re

# Initialize the PaddleOCR model with default settings
ocr = PaddleOCR(
    use_angle_cls=False,
    lang='en',
    use_gpu=True
)

# Path to the directory containing segmented cell images
cells_output_dir = os.path.join('output', 'cells')

# Output file for OCR results
csv_output_path = os.path.join('output', 'table_data_enhanced.csv')

# Define the number of rows and columns
num_rows = 28
num_columns = 8

# Preset titles for columns
column_titles = ["Variable", "Pre", "Pred", "% Pred-Pre", "LLN", "Post", "% Pred-Post", "% Change Post"]

# Adjusted 'row_titles' to include empty strings for empty rows
row_titles = [
    "",             # 0 (Variable already in column titles)
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
    "VA"            #27
]

# List of known empty rows for visual gaps (indices of empty rows)
empty_rows = [1, 11, 12, 16, 17, 22, 23]

# Cells to target with number OCR config (0-based indexing as above)
number_ocr_cells = set()

# Update ranges to only include numeric
number_ocr_cells.update([(2, col) for col in range(1, 7)])   # FVC
number_ocr_cells.update([(3, col) for col in range(1, 7)])   # FEV1
number_ocr_cells.update([(4, col) for col in range(1, 7)])   # FEV1/FVC
number_ocr_cells.update([(5, col) for col in range(1, 7)])   # FEF 25%
number_ocr_cells.update([(6, col) for col in range(1, 7)])   # FEF 75%
number_ocr_cells.update([(7, col) for col in range(1, 7)])   # FEF 25-75%
number_ocr_cells.update([(8, col) for col in range(1, 7)])   # FEF Max
number_ocr_cells.update([(9, 1), (9, 5), (9, 7)])            # FIVC
number_ocr_cells.update([(13, col) for col in range(1, 5)])  # SVC
number_ocr_cells.update([(14, col) for col in range(1, 5)])  # IC
number_ocr_cells.update([(15, col) for col in range(1, 5)])  # ERV
number_ocr_cells.update([(18, col) for col in range(1, 5)])  # TGV
number_ocr_cells.update([(19, col) for col in range(1, 5)])  # RV Pleth
number_ocr_cells.update([(20, col) for col in range(1, 5)])  # TLC Pleth
number_ocr_cells.update([(21, col) for col in range(1, 5)])  # RV/TLC Pleth
number_ocr_cells.update([(24, col) for col in range(1, 5)])  # DLCOunc
number_ocr_cells.update([(25, col) for col in range(1, 5)])  # DLCOcor
number_ocr_cells.update([(26, col) for col in range(1, 4)])  # DL/VA
number_ocr_cells.update([(27, col) for col in range(1, 4)])  # VA

# Cells to target with character OCR (0-based indexing aswell)
character_ocr_cells = set([
    (10, col) for col in range(1, 8)  # Test Grade row, columns 1 to 7
])

# Open the CSV file to store the extracted text
with open(csv_output_path, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(column_titles)  # Write header row

    # Loop through each row starting from index 0
    for row_idx in range(num_rows):
        # Build the row data
        row_data = []

        # Get the row title
        row_title = row_titles[row_idx] if row_idx < len(row_titles) else ""
        row_data.append(row_title)

        # Check if the row is an empty row
        if row_idx in empty_rows:
            # Append empty strings for the columns
            row_data.extend([""] * (num_columns - 1))
            csv_writer.writerow(row_data)
            continue

        # Loop through columns (excluding the first column for row titles)
        for col_idx in range(1, num_columns):
            # Determine if OCR should be applied
            if (row_idx, col_idx) in number_ocr_cells:
                # Apply number OCR using PaddleOCR
                cell_filename = f'cell_row{row_idx}_col{col_idx}.png'
                cell_path = os.path.join(cells_output_dir, cell_filename)

                # Load the cell image
                cell_image = cv2.imread(cell_path, cv2.IMREAD_COLOR)
                if cell_image is None:
                    print(f"Warning: Cell image not found at {cell_path}")
                    cell_text = ''
                    row_data.append(cell_text)
                    continue

                # Perform OCR using PaddleOCR
                result = ocr.ocr(cell_image, cls=False)
                cell_text = ''
                if result:
                    text_list = []
                    for res in result:
                        if res is not None:
                            for line in res:
                                if line is not None and len(line) > 1:
                                    text = line[1][0]
                                    text_list.append(text)
                    if text_list:
                        full_text = ' '.join(text_list)
                        # Extract numbers including + and - using regex
                        numbers = re.findall(r'[+-]?\d*\.\d+|[+-]?\d+', full_text)
                        # Join extracted numbers (if multiple numbers detected)
                        cell_text = ' '.join(numbers)

                # Process the cell_text to adjust missing decimal points
                if cell_text:
                    # Skip columns 3 and 6 (% Pred-Pre and % Pred-Post)
                    if col_idx not in [3, 6]:
                        if '.' not in cell_text:
                            try:
                                # Convert to float, divide by 100, format to two decimals
                                num_value = float(cell_text) / 100
                                cell_text = f"{num_value:.2f}"
                            except ValueError:
                                pass  # Keep the original cell_text if conversion fails

                row_data.append(cell_text)

            elif (row_idx, col_idx) in character_ocr_cells:
                # Apply character OCR using PaddleOCR
                cell_filename = f'cell_row{row_idx}_col{col_idx}.png'
                cell_path = os.path.join(cells_output_dir, cell_filename)

                # Load the cell image
                cell_image = cv2.imread(cell_path, cv2.IMREAD_COLOR)
                if cell_image is None:
                    print(f"Warning: Cell image not found at {cell_path}")
                    cell_text = ''
                    row_data.append(cell_text)
                    continue

                # Perform OCR using PaddleOCR
                result = ocr.ocr(cell_image, cls=True)
                cell_text = ''
                if result:
                    text_list = []
                    for res in result:
                        if res is not None:
                            for line in res:
                                if line is not None and len(line) > 1:
                                    text = line[1][0]
                                    text_list.append(text)
                    if text_list:
                        cell_text = ' '.join(text_list)
                row_data.append(cell_text)
            else:
                # Cell is assumed to be blank
                cell_text = ''
                row_data.append(cell_text)

        # Write the row data to the CSV file
        csv_writer.writerow(row_data)

# Post-processing to calculate '% Change Post' for specific rows
# Rows to calculate: 2, 4, 5, 6, 8
rows_to_calculate = [2, 4, 5, 6, 8, 9]

# Read the CSV file back into a list
with open(csv_output_path, mode='r', newline='', encoding='utf-8') as csv_file:
    csv_reader = csv.reader(csv_file)
    csv_data = list(csv_reader)

# Update '% Change Post' column for specified rows
for row_idx in rows_to_calculate:
    # Retrieve the row from csv_data (add 1 to account for header row)
    row_data = csv_data[row_idx + 1]
    try:
        # Extract 'Pre' (column 1) and 'Post' (column 5) values
        pre_value = row_data[1]
        post_value = row_data[5]
        # Convert to float
        pre_value = float(pre_value)
        post_value = float(post_value)
        # Calculate % Change
        percent_change = ((post_value - pre_value) / pre_value) * 100
        # Round down towards zero
        if percent_change > 0:
            percent_change = int(percent_change)
        else:
            percent_change = int(percent_change)    
        # Add '+' sign if positive
        if percent_change > 0:
            percent_change_str = f"+{percent_change}"
        else:
            percent_change_str = f"{percent_change}"
        # Update the '% Change Post' column (index 7)
        row_data[7] = percent_change_str
    except (ValueError, IndexError):
        # If conversion fails or indices are out of range, leave the cell blank
        row_data[7] = ''

# Write the updated csv_data back to the CSV file
with open(csv_output_path, mode='w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerows(csv_data)

print(f"OCR results saved to {csv_output_path}")