"""
ROI selection and visualization module.

Provides interactive ROI drawing interface and utilities for displaying,
filtering, and saving ROI selections. Supports both manual drawing and
automatic detection workflows.
"""

# gui/roi.py

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from gui.dialogs import CustomInputDialog, CustomMessageBox
import os

class CustomRectangleSelector(RectangleSelector):
    """Custom rectangle selector with disabled default key bindings."""
    
    def __init__(self, *args, **kwargs):
        super(CustomRectangleSelector, self).__init__(*args, **kwargs)

    def key_press_callback(self, event):
        """Override key press callback to prevent default key bindings."""
        pass

class ROISelector:
    """
    Interactive ROI selection interface via matplotlib rectangle drawing.
    
    Allows users to draw rectangular ROIs on an image or skip ROIs via spacebar.
    Tracks ROI coordinates and skip flags for each worm.
    """
    
    def __init__(self, ax, num_roi):
        """
        Initialize ROI selector.
        
        Args:
            ax: Matplotlib axis for drawing
            num_roi: Number of ROIs to select
        """
        self.ax = ax
        self.num_roi = num_roi
        self.roi_coords = [None] * num_roi
        self.ignore_worm = [1] * num_roi  # 1 = skip by default
        self.k = 0  # Current ROI index

        # Configure rectangle selector for interactive drawing
        self.toggle_selector = CustomRectangleSelector(
            ax, self.onselect, useblit=True,
            button=[1], minspanx=5, minspany=5, spancoords='pixels',
            interactive=True,
            props=dict(facecolor='red', edgecolor='black', alpha=0.5, fill=True)
        )

        # Connect keyboard events
        self.cid = self.ax.figure.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.update_title()

    def onselect(self, eclick, erelease):
        """Handle rectangle selection event."""
        if self.k >= self.num_roi:
            print("All worms have been processed.")
            return

        x1, y1 = int(eclick.xdata), int(eclick.ydata)
        x2, y2 = int(erelease.xdata), int(erelease.ydata)

        # Zero-size rectangles mark ROI as ignored
        if x1 == x2 or y1 == y2:
            self.ignore_worm[self.k] = 1
            self.roi_coords[self.k] = None
            print(f"Ignoring worm #{self.k + 1}")
        else:
            self.ignore_worm[self.k] = 0
            self.roi_coords[self.k] = ((x1, y1), (x2, y2))
            print(f"Selected ROI #{self.k + 1}: ({x1}, {y1}) to ({x2}, {y2})")

        self.k += 1
        self.update_title()

    def on_key_press(self, event):
        """Handle spacebar to skip current ROI."""
        if self.k >= self.num_roi:
            print("All worms have been processed.")
            return
        if event.key in (' ', 'space'):
            self.ignore_worm[self.k] = 1
            self.roi_coords[self.k] = None
            print(f"Ignoring worm #{self.k + 1} due to key press: '{event.key}'")
            self.k += 1
            self.update_title()

    def update_title(self):
        """Update display title with current ROI number and instructions."""
        if self.k < self.num_roi:
            self.ax.set_title(
                f"Please draw ROI for worm #{self.k + 1}, drag cursor to draw a rectangle.\nPress Space to skip this worm."
            )
            self.ax.figure.canvas.draw_idle()
        else:
            self.toggle_selector.set_visible(False)
            self.toggle_selector.disconnect_events()
            self.ax.figure.canvas.mpl_disconnect(self.cid)
            plt.close(self.ax.figure)

    def get_roi_data(self):
        """Return ROI coordinates and ignore flags."""
        return self.roi_coords, self.ignore_worm


def display_minimum_image(imgmin):
    """Display minimum projection image using matplotlib."""
    import matplotlib.pyplot as plt
    plt.figure(figsize=(4, 4))
    plt.imshow(imgmin, cmap='viridis')
    plt.title('Minimum Image')
    plt.axis('off')
    plt.show()

def display_debug_image(annotated_img, roi_coords, circles, directory):
    """
    Display detected ROIs with numeric labels on annotated image.
    
    Draws green rectangles around each ROI, saves as "detected_ROIs.jpg",
    and displays via OpenCV.
    
    Returns:
        Annotated debug image with ROI rectangles and labels
    """
    debug_img = annotated_img.copy()
    # Draw ROI rectangles with numeric labels
    for idx, ((x1, y1), (x2, y2)) in enumerate(roi_coords, start=1):
        cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(debug_img, str(idx), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2, cv2.LINE_AA)
    
    # Overlay instruction message
    message = "Automatically detected ROIs. Please select ROIs to ignore and press Submit."
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    color = (255, 255, 255)
    background_color = (0, 0, 0)
    text_size = cv2.getTextSize(message, font, font_scale, font_thickness)[0]
    text_x = (debug_img.shape[1] - text_size[0]) // 2
    text_y = debug_img.shape[0] - 30
    cv2.rectangle(debug_img, (text_x - 10, text_y - text_size[1] - 10),
                  (text_x + text_size[0] + 10, text_y + 10), background_color, -1)
    cv2.putText(debug_img, message, (text_x, text_y), font, font_scale, color, font_thickness, cv2.LINE_AA)
    cv2.imshow("ROIs", debug_img)
    cv2.imwrite(os.path.join(directory, "detected_ROIs.jpg"), debug_img)
    cv2.waitKey(1)
    return debug_img

def ask_ignore_indices():
    """
    Prompt user to select ROI indices to ignore.
    
    Returns:
        List of 0-based indices to ignore
    """
    root = tk.Tk()
    root.withdraw()
    input_dialog = CustomInputDialog(root,
                                     "Enter the numbers of ROIs to ignore, separated by commas\n(e.g., 1,3,5):",
                                     title="Select ROIs to Ignore")
    input_dialog.wait_window()
    user_input = input_dialog.result
    indices = []
    if user_input:
        try:
            indices = [int(num.strip()) - 1 for num in user_input.split(',') if num.strip().isdigit()]
        except Exception as e:
            error_dialog = CustomMessageBox(root, f"Invalid input: {e}. No ROIs will be ignored.",
                                            title="Invalid Input", msg_type="error")
            root.wait_window(error_dialog)
    else:
        info_dialog = CustomMessageBox(root, "No ROIs were ignored.", title="No Input", msg_type="info")
        root.wait_window(info_dialog)
    root.destroy()
    return indices

def display_selected_rois(annotated_img, roi_coords, circles, ignore_flags, directory):
    """
    Mark ignored ROIs with red X's and save result image.
    
    Saves as "Selected_ROIs.jpg" in the specified directory.
    Displays confirmation to user before proceeding.
    """
    selected_img = annotated_img.copy()
    # Draw red X's on ignored ROIs
    for idx, coord in enumerate(roi_coords):
        if ignore_flags[idx]:
            center_x = int(circles[idx]["x"])
            center_y = int(circles[idx]["y"])
            size = 15
            cv2.line(selected_img, (center_x - size, center_y - size),
                     (center_x + size, center_y + size), (0, 0, 255), 3)
            cv2.line(selected_img, (center_x - size, center_y + size),
                     (center_x + size, center_y - size), (0, 0, 255), 3)
    
    # Save result image
    selected_output_path = os.path.join(directory, "Selected_ROIs.jpg")
    cv2.imwrite(selected_output_path, selected_img)
    print(f"Selected ROIs image saved: {selected_output_path}")

    # Display confirmation with instruction message
    message = "Ignored ROIs (marked with X) will be excluded, press Enter to continue."
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    color = (255, 255, 255)
    background_color = (0, 0, 0)
    text_size = cv2.getTextSize(message, font, font_scale, font_thickness)[0]
    text_x = (selected_img.shape[1] - text_size[0]) // 2
    text_y = selected_img.shape[0] - 30
    cv2.rectangle(selected_img, (text_x - 10, text_y - text_size[1] - 10),
                  (text_x + text_size[0] + 10, text_y + 10), background_color, -1)
    cv2.putText(selected_img, message, (text_x, text_y), font, font_scale, color, font_thickness, cv2.LINE_AA)
    cv2.imshow("Selected ROIs", selected_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
