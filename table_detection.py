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
template = cv2.imread(template_path, cv2.IMREAD_COLOR)
if template is None:
    raise IOError(f"Template image not found at {template_path}")

# Load the target image
target_image = cv2.imread(target_path, cv2.IMREAD_COLOR)
if target_image is None:
    raise IOError(f"Target image not found at {target_path}")

# Convert images to grayscale
template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
target_gray = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)

### Preprocessing (optional)

# Apply Gaussian blur to reduce noise
# template_gray = cv2.GaussianBlur(template_gray, (3, 3), 0)
# target_gray = cv2.GaussianBlur(target_gray, (3, 3), 0)

#use normalization to adjust for resolution discrepencies
#code

#use brightness normalization to adjust for different brightness
#code


# Initialize variables to keep track of the best match
best_match_value = -1
best_match_location = None
best_match_scale = 1.0
best_template_size = (0, 0)

# Define the scales to iterate over
scale_factors = np.linspace(0.5, 1.5, 21)  # Adjust as needed

# Iterate over the scales
for scale in scale_factors:
    # Resize the template image
    template_resized = imutils.resize(template_gray, width=int(template_gray.shape[1] * scale))
    tH, tW = template_resized.shape[:2]

    # Break if the resized template is larger than the target image
    if tH > target_gray.shape[0] or tW > target_gray.shape[1]:
        continue

    # Perform template matching
    result = cv2.matchTemplate(target_gray, template_resized, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # Update the best match if the current one is better
    if max_val > best_match_value:
        best_match_value = max_val
        best_match_location = max_loc
        best_match_scale = scale
        best_template_size = (tW, tH)

# Print for testing
print(f"Best match value: {best_match_value} at scale: {best_match_scale}")

# Check if a match was found
if best_match_value >= 0.4:  # Adjust threshold as needed
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
    
##########################
##possible improvements for table detection:
    #run tests on tables with different number values *at different resolutions, scales, and brightness*
    #if the accuracy is not good enough i.e. < 80: 
    #run grid search over preprocessing methods mentioned earlier (loop over different combinations of effects and intensities) to find best combination
    #additionally, adjust the model type used in cv2.matchTemplate (currently = cv2.TM_CCOEFF_NORMED)
    #if the scale adjustment doesnt fix the problem enough, could implement a binary-search-type algorithm that keeps adjusting scale until confidence converges at a set threshold
    
#optional:
    #add algorithm to fix rotated/skewed images (likely not necessary)
    #add a tool to let the user upload an image of their own annotated table manually

##########################