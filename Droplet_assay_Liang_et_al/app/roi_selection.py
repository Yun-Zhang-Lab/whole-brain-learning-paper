"""
Region of Interest (ROI) selection module.

Provides both manual and automatic ROI detection methods. Manual mode allows
users to interactively draw ROIs on the image. Automatic mode uses circle
detection to identify droplets and create ROIs with optional user filtering.

"""

import os
from pathlib import Path
import tkinter as tk
from gui.window_utils import center_window
from gui.dialogs import CustomInputDialog, CustomMessageBox
from gui.roi import ROISelector, display_debug_image, display_selected_rois
from auto_roi_detection import detect_circles_in_image
import matplotlib.pyplot as plt
import cv2
import numpy as np

def roi_method_dialog(analyzer):
    """
    Display dialog for user to choose between manual or automatic ROI detection.
    
    Creates a modal dialog with two options:
    - Manual: User interactively draws ROIs on the image
    - Automatic: Algorithm automatically detects circular ROIs
    
    Args:
        analyzer: DropletAssayAnalyzer instance containing image and analysis state
    """
    win = tk.Toplevel(analyzer.root)
    win.title("Select ROI Method")
    win.geometry("400x250")
    center_window(win)

    def on_close():
        """Handle window close event."""
        analyzer.stop_processing = True
        win.destroy()
        analyzer.on_closing()

    win.protocol("WM_DELETE_WINDOW", on_close)
    tk.Label(win, text="Select ROI extraction method:", font=("Helvetica", 12, "bold")).pack(pady=20)

    tk.Button(win, text="Manual", font=8, width=20, height=2,
              command=lambda: [win.destroy(), manual_roi(analyzer)]).pack(pady=5)
    tk.Button(win, text="Automatic", font=8, width=20, height=2,
              command=lambda: [win.destroy(), auto_roi(analyzer)]).pack(pady=5)

def manual_roi(analyzer):
    """
    Enable interactive manual ROI selection via matplotlib drawing interface.
    
    Prompts user for the number of ROIs to define, displays the image, and allows
    interactive drawing of rectangular regions. Press Enter to finalize selection.
    
    Args:
        analyzer: DropletAssayAnalyzer instance containing image data
    """
    # Prompt user for number of ROIs to manually define
    num_roi = analyzer.custom_askinteger("Number of ROIs", "Enter number of ROIs:", initialvalue=12)
    if num_roi is None:
        analyzer.custom_print("ROI selection canceled.")
        analyzer.on_closing()
        return

    if analyzer.image is None:
            print("Error", "No image loaded for ROI selection")
            return False
    
    # Ensure image is in numpy array format
    if isinstance(analyzer.image, np.ndarray):
            img_to_show = analyzer.image
    else:
            try:
                img_to_show = np.array(analyzer.image)
            except Exception as e:
                print("Error", f"Failed to convert image: {str(e)}")
                return False
            
    # Display image with interactive ROI selector overlay
    fig, ax = plt.subplots()
    ax.imshow(analyzer.image, cmap='autumn')
    roi_selector = ROISelector(ax, num_roi)
    plt.connect('key_press_event', lambda event: plt.close() if event.key == 'enter' else None)
    plt.show()

    # Store selected ROI coordinates and worm flags
    analyzer.roi_coords = roi_selector.roi_coords
    analyzer.ignore_worm = roi_selector.ignore_worm
    analyzer.process_images_and_signals()

def auto_roi(analyzer):
    """
    Automatically detect circular ROIs using image processing.
    
    Detects circles in a subset of images, converts circle parameters to ROI
    coordinates with padding, displays results, and allows user to exclude
    specific ROIs before analysis.
    
    Args:
        analyzer: DropletAssayAnalyzer instance with matching files and directory
    """
    # Sample images at regular intervals for circle detection efficiency
    image_list = [
            os.path.join(analyzer.directory, f)
            for f in analyzer.matching_files[::100]
            if os.path.basename(f).startswith('w1a')
        ]
    circles, annotated_img, _, _ = detect_circles_in_image(image_list)

    # Convert detected circles to ROI rectangular coordinates
    padding = 5
    img_h, img_w = annotated_img.shape[:2]
    roi_coords = []
    for circle in circles:
        x, y, radius = int(circle["x"]), int(circle["y"]), int(circle["radius"])
        # Define bounding box around circle with padding
        x1 = max(0, x - radius - padding)
        y1 = max(0, y - radius - padding)
        x2 = min(img_w, x + radius + padding)
        y2 = min(img_h, y + radius + padding)
        roi_coords.append(((x1, y1), (x2, y2)))

    # Initialize flags indicating which ROIs contain worms to ignore
    ignore_worm = [0] * len(roi_coords)
    debug_img = display_debug_image(annotated_img, roi_coords, circles, analyzer.directory)
    

    # Temporary root for the input dialog
    temp_root = tk.Tk()
    temp_root.withdraw()
    # Prompt user to specify which ROIs should be excluded from analysis
    input_dialog = CustomInputDialog(temp_root, "Enter ROIs to ignore (e.g. 1,3,5):", title="Ignore ROIs")
    temp_root.wait_window(input_dialog)
    user_input = input_dialog.result

    if user_input is None:
        print("Auto ROI dialog closed or canceled by user.")
        analyzer.stop_processing = True
        analyzer.on_closing()
        return

    # Process user input to mark ROIs as ignored
    if user_input:
        try:
            # Parse comma-separated ROI indices (1-indexed from user perspective)
            indices = [int(i.strip()) - 1 for i in user_input.split(',') if i.strip().isdigit()]
            for idx in indices:
                if 0 <= idx < len(ignore_worm):
                    ignore_worm[idx] = 1
                    roi_coords[idx] = None
                else:
                    CustomMessageBox(temp_root, f"ROI {idx+1} is out of range.", title="Invalid ROI")
        except Exception as e:
            CustomMessageBox(temp_root, f"Invalid input: {e}", title="Invalid Input")
    else:
        CustomMessageBox(temp_root, "No ROIs were ignored.", title="No Input")

    temp_root.destroy()
    cv2.destroyAllWindows()
    # Display final ROI selection for verification
    display_selected_rois(annotated_img, roi_coords, circles, ignore_worm, analyzer.directory)

    # Store final ROI configuration
    analyzer.roi_coords = roi_coords
    analyzer.ignore_worm = ignore_worm
    analyzer.process_images_and_signals()