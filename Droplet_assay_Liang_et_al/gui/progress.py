"""Progress bar dialog for image processing visualization."""

import tkinter as tk
from tkinter import Toplevel, Label, ttk
from .window_utils import center_window

def create_progress_bar(analyzer, total):
    """
    Create progress bar window for processing feedback.
    
    Closing the window stops processing and exits the application.
    
    Args:
        analyzer: DropletAssayAnalyzer instance
        total: Total number of items to process (for progress scale)
        
    Returns:
        Tuple of (progress_widget, progress_window) for updating and managing display
    """
    progress_window = Toplevel(analyzer.root)
    progress_window.title("Processing Progress")
    window_width = 600
    window_height = 100
    progress_window.geometry(f"{window_width}x{window_height}")
    center_window(progress_window)
    
    # Force immediate window rendering
    progress_window.update()

    def on_closing_local():
        """Handle window close - stops processing."""
        print("Progress window closed by the user.")
        analyzer.stop_processing = True
        progress_window.destroy()
        analyzer.on_closing()
       
    progress_window.protocol("WM_DELETE_WINDOW", on_closing_local)

    label = Label(progress_window, text="Please wait, processing images...", font=("Helvetica", 12))
    label.pack(pady=10)

    # Configure progress bar styling
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Custom.Horizontal.TProgressbar", 
                    troughcolor='white', 
                    bordercolor='black', 
                    background='#4CAF50',
                    lightcolor='#4CAF50',
                    darkcolor='#4CAF50',
                    thickness=20)

    progress = ttk.Progressbar(progress_window, style="Custom.Horizontal.TProgressbar",
                               orient="horizontal", length=window_width - 40, mode="determinate")
    progress.pack(pady=10)
    progress["maximum"] = total

    return progress, progress_window
