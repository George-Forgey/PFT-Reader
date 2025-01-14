import cv2
import numpy as np
import os

# Assuming 'cropped_table' is the detected table from Phase 1
# Load the cropped table if not already loaded
cropped_table_path = os.path.join('output', 'cropped_table.png')
cropped_table = cv2.imread(cropped_table_path)
if cropped_table is None:
    raise IOError(f"Cropped table image not found at {cropped_table_path}")

# Get the dimensions of the cropped table
table_height, table_width, _ = cropped_table.shape

# Define the number of rows and columns
num_rows = 28  # Example: Adjust based on your table
column_proportions = [
    (0.005, 0.25),  
    (0.26, 0.344), 
    (0.344, 0.431),  
    (0.435, 0.558),  
    (0.561, 0.646),
    (0.65, 0.729),
    (0.78, 0.863),
    (0.9, 0.995)
]  

# Calculate the row height
row_height = table_height // num_rows

# Create the output directory for cells
cells_output_dir = os.path.join('output', 'cells')
os.makedirs(cells_output_dir, exist_ok=True)

# Loop through rows and columns to segment each cell
for row_idx in range(num_rows):
    for col_idx, (start_prop, end_prop) in enumerate(column_proportions):
        # Calculate the x-coordinates for the current column
        start_x = int(start_prop * table_width)
        end_x = int(end_prop * table_width)
        
        # Calculate the y-coordinates for the current row
        start_y = row_idx * row_height
        end_y = (row_idx + 1) * row_height

        # Crop the cell from the table
        cell = cropped_table[start_y:end_y, start_x:end_x]

        # Save the cell image
        cell_filename = f'cell_row{row_idx}_col{col_idx}.png'
        cell_path = os.path.join(cells_output_dir, cell_filename)
        cv2.imwrite(cell_path, cell)

print(f"Cells saved in directory: {cells_output_dir}")