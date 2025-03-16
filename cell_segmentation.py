import cv2
import numpy as np
import os

def segment_cells(config, 
                  cropped_table_path="output/cropped_table.png", 
                  cells_output_dir="output/cells"):
    """
    Segments the cropped_table.png image into individual cell images,
    based on row_proportions and column_proportions from the config dict.

    config should contain:
      - "row_proportions":  list of floats in ascending order (0.0 .. 1.0)
      - "column_proportions": list of floats in ascending order (0.0 .. 1.0)
      - "num_rows": int
      - "num_columns": int

    The function saves each cell as:
        cells_output_dir/cell_row{i}_col{j}.png
    """
    # Load the cropped table
    cropped_table = cv2.imread(cropped_table_path)
    if cropped_table is None:
        raise IOError(f"Cropped table image not found at {cropped_table_path}")

    # Extract image dimensions
    table_height, table_width, _ = cropped_table.shape

    # Read row/col proportions from the config
    row_proportions = config.get("row_proportions", [])
    column_proportions = config.get("column_proportions", [])
    num_rows = config.get("num_rows", 1)
    num_cols = config.get("num_columns", 1)

    # Create output directory for cells
    os.makedirs(cells_output_dir, exist_ok=True)

    # Convert each proportion to an absolute pixel boundary
    # e.g., 0.0 -> 0, 0.5 -> table_width * 0.5, etc.
    # We expect row_proportions and column_proportions to already have
    # the 0.0 and 1.0 boundaries included. If not, you can insert them here.
    row_boundaries = [int(p * table_height) for p in row_proportions]
    col_boundaries = [int(p * table_width) for p in column_proportions]

    # Loop through adjacent boundaries to get each cell
    # e.g., row i from row_boundaries[i] to row_boundaries[i+1]
    #       col j from col_boundaries[j] to col_boundaries[j+1]
    total_cells = 0

    # Safety check: ensure we have at least 2 boundaries in each dimension
    # (e.g., [0, ..., 1])
    row_segments = len(row_boundaries) - 1
    col_segments = len(col_boundaries) - 1

    for i in range(row_segments):
        start_y = row_boundaries[i]
        end_y = row_boundaries[i+1]
        for j in range(col_segments):
            start_x = col_boundaries[j]
            end_x = col_boundaries[j+1]

            # Crop the cell
            cell = cropped_table[start_y:end_y, start_x:end_x]

            # Save the cell image
            cell_filename = f"cell_row{i}_col{j}.png"
            cell_path = os.path.join(cells_output_dir, cell_filename)
            cv2.imwrite(cell_path, cell)
            total_cells += 1

    print(f"Segmented {total_cells} cells into directory: {cells_output_dir}")