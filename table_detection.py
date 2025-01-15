import cv2
import numpy as np
import os
import imutils

#Phase 1 - Table Detection
##########################

# Define the paths to the template and target images
template_path = 'table_template.png'
target_path = 'table_target.png'

# Define the output directory
output_dir = 'output'
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
neighborhood_scales = np.arange(0.5, 1.5, 0.1)  # Additional scales for robustness

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

# Print the best match for testing
print(f"Best match value: {best_match_value} at scale: {best_match_scale}")

# Check if a match was found
if best_match_value >= 0.2:  # Adjust threshold as needed
    # Calculate the bounding box coordinates
    top_left = best_match_location
    tW, tH = best_template_size
    bottom_right = (top_left[0] + tW, top_left[1] + tH)

    # Draw a rectangle around the detected table
    detected_image = target_image.copy()
    cv2.rectangle(detected_image, top_left, bottom_right, (0, 255, 0), 2)
    cv2.imwrite(os.path.join(output_dir, 'table_detected.png'), detected_image)

    # Crop the detected table from the target image
    cropped_table = target_image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
    cv2.imwrite(os.path.join(output_dir, 'cropped_table.png'), cropped_table)
else:
    print("No good match found.")