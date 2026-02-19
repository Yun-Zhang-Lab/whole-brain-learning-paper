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
    
    In single mode: Based on analysis type:
    - 'single': Prompts user to select a specific folder to analyze
    - 'timestamp': Prompts user to select a top directory containing timestamp folders,
                    then recursively finds all images in subdirectories
    
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
    
    # Single mode - determine analysis type and handle accordingly
    analysis_type = getattr(analyzer, 'single_analysis_type', 'timestamp')
    
    if analysis_type == 'single':
        # Single folder mode - select specific folder
        directory = filedialog.askdirectory(
            parent=analyzer.root,
            title="Select Folder to Analyze"
        )
    else:  # 'timestamp'
        # Timestamp folders mode - select top directory with timestamp folders
        directory = select_top_directory(analyzer.root)
    
    if not directory:
        analyzer.stop_processing = True
        return False
    
    analyzer.directory = directory
    
    # Find all matching files recursively
    if not analyzer.find_matching_files():
        analyzer.stop_processing = True
        return False
    
    # Get initial frame count for display
    num_files = len(analyzer.matching_files)
    
    # Prompt user to select frame range for analysis
    dialog = FrameSelectionDialog(
        analyzer.root,
        analyzer,
        title="Select Frame Range",
        initial_start=1,
        initial_end=num_files
    )
    
    # Check if user cancelled the dialog
    if dialog.result is None:
        analyzer.stop_processing = True
        return False
    
    analyzer.istart, analyzer.iend = dialog.result
    return True

def select_image_file(parent, title="Select Image File"):
    """
    Display dialog for selecting a top-level directory.
    
    Args:
        parent: Parent Tkinter widget (typically root window)
        title: Dialog window title (default: "Select Top Directory")
        
    Returns:
        Full path to selected directory, or empty string if cancelled
    """
    return filedialog.askdirectory(
        parent=parent,
        title=title
    )


def select_top_directory(parent, title="Select Top Directory"):
    """
    Display dialog for selecting a top-level directory to search for images.
    
    Allows user to choose a directory, which will be recursively searched for
    all images starting with 'w1a' in all subdirectories.
    
    Args:
        parent: Parent Tkinter widget (typically root window)
        title: Dialog window title
        
    Returns:
        Full path to selected directory, or empty string if cancelled
    """
    return filedialog.askdirectory(
        parent=parent,
        title=title
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