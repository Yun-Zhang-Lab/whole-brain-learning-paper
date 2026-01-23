"""
Automatic ROI detection using circular Hough transform.

Detects circular droplets in microscopy images using pixel-wise minimum projection
and Hough circle detection. Generates annotated visualizations and CSV output.
"""

import cv2
import numpy as np
import pandas as pd
import os
import cv2
import numpy as np
import pandas as pd
import os
from typing import Union, List, Tuple

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """Read image file supporting Unicode paths."""
    stream = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(stream, flags)

def imwrite_unicode(path, img, params=None):
    """Write image file supporting Unicode paths."""
    ext = '.' + path.split('.')[-1]
    result, encoded = cv2.imencode(ext, img, params or [])
    if result:
        encoded.tofile(path)
        return True
    else:
        return False

def detect_circles_in_image(image_file_path: Union[str, List[str], Tuple[str, ...]]):
    """
    Detect circular droplet ROIs using Hough circle detection on minimum image.

    Creates a pixel-wise minimum projection across input images to suppress noise,
    applies Hough circle detection, and generates labeled output with column-major
    (left-to-right, top-to-bottom) ordering.

    Parameters
    ----------
    image_file_path : str | list[str] | tuple[str, ...]
        Single file path or list/tuple of image paths for min projection.
    
    Returns
    -------
    circles_sorted : list[dict]
        Detected circles with keys: {'x','y','radius','col','row','label'}.
        Label indicates position in grid (1..N, column-major order).
    annotated_image : np.ndarray (H,W,3) uint8
        BGR image with detected circles and labels drawn.
    csv_output_path : str
        Path to saved detected_ROIs.csv
    output_image_path : str
        Path to saved annotated JPG
    """
    # Normalize input to list of file paths
    if isinstance(image_file_path, (list, tuple)):
        paths = [p for p in image_file_path if isinstance(p, str) and os.path.isfile(p)]
        if not paths:
            raise FileNotFoundError("No valid image files provided.")
        folder_path = os.path.dirname(paths[0])
    else:
        # Single file path
        if not os.path.isfile(image_file_path):
            raise FileNotFoundError(f"Error: File {image_file_path} does not exist.")
        paths = [image_file_path]
        folder_path = os.path.dirname(image_file_path)

    # Define output file paths
    csv_output_path = os.path.join(folder_path, "detected_ROIs.csv")
    output_image_path = os.path.join(folder_path, "detected_circles_visualized.jpg")
    min_image_debug_path = os.path.join(folder_path, "min_image_debug.png")

    # Build grayscale minimum image across all input images
    img0 = imread_unicode(paths[0], cv2.IMREAD_COLOR)
    if img0 is None:
        raise FileNotFoundError(f"Cannot read: {paths[0]}")
    h, w = img0.shape[:2]
    min_gray = np.full((h, w), 255, dtype=np.uint8)

    for p in paths:
        im = imread_unicode(p, cv2.IMREAD_COLOR)
        if im is None:
            continue
        if im.shape[:2] != (h, w):
            im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        # Light denoise before min to suppress salt noise
        g = cv2.GaussianBlur(g, (3, 3), 0)
        cv2.min(min_gray, g, dst=min_gray)  # Pixel-wise minimum

    # Save minimum image for debugging
    imwrite_unicode(min_image_debug_path, min_gray)

    # Detect circles using Hough Circle detection
    gray_blurred = cv2.GaussianBlur(min_gray, (5, 5), 0)
    detected_circles = cv2.HoughCircles(
        gray_blurred,
        cv2.HOUGH_GRADIENT,
        dp=2,
        minDist=60,
        param1=150,
        param2=100,
        minRadius=10,
        maxRadius=80
    )

    annotated_image = cv2.cvtColor(min_gray, cv2.COLOR_GRAY2BGR)
    circle_data = []
    if detected_circles is not None:
        detected_circles = np.uint16(np.around(detected_circles))
        for pt in detected_circles[0, :]:
            a, b, r = int(pt[0]), int(pt[1]), int(pt[2])
            circle_data.append({"x": a, "y": b, "radius": r})
            cv2.circle(annotated_image, (a, b), 2, (0, 255, 0), 3)

        # Assign column-major labels (L→R columns, T→B rows)
        circles_df = pd.DataFrame(circle_data)
        num_cols, num_rows = 4, 3  # Grid dimensions (adjust as needed)

        x_min, x_max = circles_df["x"].min(), circles_df["x"].max()
        y_min, y_max = circles_df["y"].min(), circles_df["y"].max()
        col_bins = np.linspace(x_min, x_max, num_cols + 1)
        row_bins = np.linspace(y_min, y_max, num_rows + 1)

        # Bin circles into grid cells
        circles_df["col"] = pd.cut(circles_df["x"], bins=col_bins, labels=False, include_lowest=True)
        circles_df["row"] = pd.cut(circles_df["y"], bins=row_bins, labels=False, include_lowest=True)

        # Sort by column first (L→R), then row (T→B) for column-major ordering
        circles_df = circles_df.sort_values(["col", "row", "y", "x"], ascending=[True, True, True, True])

        circles_sorted = circles_df.to_dict("records")
        # Add sequential labels and annotate on image
        for idx, c in enumerate(circles_sorted, start=1):
            c["label"] = idx
            a, b = int(c["x"]), int(c["y"])
            cv2.putText(
                annotated_image, str(idx), (a - 10, b + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2, cv2.LINE_AA
            )
    else:
        circles_sorted = []

    # Save annotated image and ROI data
    imwrite_unicode(output_image_path, annotated_image)
    if circles_sorted:
        pd.DataFrame(circles_sorted).to_csv(csv_output_path, index=False)
    else:
        print("No ROIs detected in the (min) image.")

    cv2.destroyAllWindows()
    return circles_sorted, annotated_image, csv_output_path, output_image_path