"""
File selection and frame range configuration module.

Handles user file selection, frame range specification, and batch processing
configuration. Provides dialog-based interfaces for both single and batch workflows.

"""

import os
import tkinter as tk
from tkinter import filedialog
from gui.dialogs import CustomMessageBox
import imageio.v2 as imageio
from gui.dialogs import FrameSelectionDialog


def file_type_dialog(analyzer):
    """
    Handle file selection and frame range configuration based on analysis mode.
    
    In batch mode: Automatically searches for matching files (no user dialog).
    In single mode: Prompts user to select an image file and specify frame range.
    
    Args:
        analyzer: DropletAssayAnalyzer instance with current analysis configuration
        
    Returns:
        True if file selection successful, False otherwise
    """
    if analyzer.batch_mode:
        # Batch mode - automatic processing without user interaction
        if not analyzer.find_matching_files():
            analyzer.stop_processing = True
            return False
        return True
    
    # Single mode - display file selection dialog
    filename = select_image_file(analyzer.root)
    if not filename:
        analyzer.stop_processing = True
        return False
    
    analyzer.filename = filename
    analyzer.directory = os.path.dirname(filename)
    
    # Get initial frame count for frame range dialog
    initial_files = [f for f in os.listdir(analyzer.directory) 
                   if f.lower().startswith('w1a') and f.lower().endswith('.jpg')]
    
    # Prompt user to select frame range for analysis
    dialog = FrameSelectionDialog(
        analyzer.root,
        analyzer,
        title="Select Frame Range",
        initial_start=1,
        initial_end=len(initial_files)
    )
    
    analyzer.istart, analyzer.iend = dialog.result
    return analyzer.find_matching_files()

def select_image_file(parent, title="Select Image File"):
    """
    Display file dialog for selecting a single image file.
    
    Filters dialog to show common image formats (JPG, PNG, TIFF).
    
    Args:
        parent: Parent Tkinter widget (typically root window)
        title: Dialog window title (default: "Select Image File")
        
    Returns:
        Full path to selected file, or empty string if cancelled
    """
    filetypes = [
        ("Image files", "*.jpg;*.jpeg;*.png;*.tiff;*.tif"),
        ("All files", "*.*")
    ]
    return filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=filetypes
    )

def setup_batch_processing(analyzer, directories):
    """
    Configure analyzer instance for batch processing mode.
    
    Sets batch mode flag and stores list of directories to be processed.
    
    Args:
        analyzer: DropletAssayAnalyzer instance to configure
        directories: List of directory paths for batch processing
    """
    analyzer.batch_mode = True
    analyzer.batch_directories = directories