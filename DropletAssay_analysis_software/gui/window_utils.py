"Window utility functions for tkinter applications."
"Centering windows and handling close events."

import tkinter as tk

def center_window(window):
    """
    Center a tkinter window on the screen.
    """
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

def on_closing(root, stop_processing_callback):
    """
    Handle the window close event.
    The stop_processing_callback should be a function that sets a flag indicating processing should stop.
    """
    print("Application closing requested by the user.")
    stop_processing_callback()
    root.quit()
