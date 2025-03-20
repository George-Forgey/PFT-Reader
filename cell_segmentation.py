import cv2
import numpy as np
import os

def segment_cells(config, 
                  cropped_table_path="output/cropped_table.png", 
                  cells_output_dir="output/cells"):
    """
    Segments the cropped_table.png image into individual cell images,
    based on row_proportions and column_proportions from the config dict.
    
    This segmentation is for the numeric portion of the table only,
    where cell indices start at (0,0).
    
    The config should contain:
      - "row_proportions": list of floats in ascending order (0.0 .. 1.0)
      - "column_proportions": list of floats in ascending order (0.0 .. 1.0)
      - "num_rows": int (number of numeric rows)
      - "num_columns": int (number of numeric columns)
    
    Each cell is saved as:
        cells_output_dir/cell_row{i}_col{j}.png
    """
    # Load the cropped table
    cropped_table = cv2.imread(cropped_table_path)
    if cropped_table is None:
        raise IOError(f"Cropped table image not found at {cropped_table_path}")

    # Get image dimensions
    table_height, table_width, _ = cropped_table.shape

    # Read row/column proportions from config
    row_proportions = config.get("row_proportions", [])
    column_proportions = config.get("column_proportions", [])
    num_rows = config.get("num_rows", 1)
    num_cols = config.get("num_columns", 1)

    # Create output directory for cells
    os.makedirs(cells_output_dir, exist_ok=True)

    # Convert each proportion to an absolute pixel boundary
    row_boundaries = [int(p * table_height) for p in row_proportions]
    col_boundaries = [int(p * table_width) for p in column_proportions]

    total_cells = 0
    row_segments = len(row_boundaries) - 1
    col_segments = len(col_boundaries) - 1

    for i in range(row_segments):
        start_y = row_boundaries[i]
        end_y = row_boundaries[i+1]
        for j in range(col_segments):
            start_x = col_boundaries[j]
            end_x = col_boundaries[j+1]

            cell = cropped_table[start_y:end_y, start_x:end_x]
            cell_filename = f"cell_row{i}_col{j}.png"
            cell_path = os.path.join(cells_output_dir, cell_filename)
            cv2.imwrite(cell_path, cell)
            total_cells += 1

    print(f"Segmented {total_cells} cells into directory: {cells_output_dir}")
