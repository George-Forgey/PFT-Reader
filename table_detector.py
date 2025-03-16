# -- table_detector.py (function-based) --
import cv2
import numpy as np
import os
import imutils

def detect_table(template_path, target_path, output_dir="output", threshold=0.2):
    """
    Detects the table in target_path using the template_path image.
    Saves 'table_detected.png' and 'cropped_table.png' to output_dir if successful.
    Returns True if a match was found and cropped, otherwise False.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load the template image
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise IOError(f"Template image not found at {template_path}")

    # Load the target image
    target_image = cv2.imread(target_path, cv2.IMREAD_GRAYSCALE)
    if target_image is None:
        raise IOError(f"Target image not found at {target_path}")

    # Initialize variables to keep track of the best match
    best_match_value = -1
    best_match_location = None
    best_match_scale = 1.0
    best_template_size = (0, 0)

    # Define scales to test
    neighborhood_scales = np.arange(0.5, 1.5, 0.1)

    # Iterate over the scales
    for scale in neighborhood_scales:
        # Resize the template image
        template_resized = imutils.resize(template, width=int(template.shape[1] * scale))
        tH, tW = template_resized.shape[:2]

        # Skip if the resized template is larger than the target image
        if tH > target_image.shape[0] or tW > target_image.shape[1]:
            continue

        # Perform template matching
        result = cv2.matchTemplate(target_image, template_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # Update the best match if the current one is better
        if max_val > best_match_value:
            best_match_value = max_val
            best_match_location = max_loc
            best_match_scale = scale
            best_template_size = (tW, tH)

    print(f"Best match value: {best_match_value} at scale: {best_match_scale}")

    # Check if a match was found
    if best_match_value >= threshold:
        # Calculate the bounding box coordinates
        top_left = best_match_location
        tW, tH = best_template_size
        bottom_right = (top_left[0] + tW, top_left[1] + tH)

        # Draw a rectangle around the detected table
        detected_image = target_image.copy()
        cv2.rectangle(detected_image, top_left, bottom_right, (255, 255, 255), 2)
        cv2.imwrite(os.path.join(output_dir, 'table_detected.png'), detected_image)

        # Crop the detected table from the target image
        cropped_table = target_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        cv2.imwrite(os.path.join(output_dir, 'cropped_table.png'), cropped_table)
        print("Table detected and cropped_table.png saved.")
        return True
    else:
        print("No good match found.")
        return False
