"""Splash screen display for application startup."""

import tkinter as tk
from tkinter import Toplevel, Label
from PIL import Image, ImageTk
from .window_utils import center_window

class SplashScreen:
    """Display a branded splash screen during application startup."""
    
    def __init__(self, root, image_path, duration, bg_color, image_size):
        """
        Create and display splash screen.
        
        Args:
            root: Parent Tkinter root window
            image_path: Path to splash screen image file
            duration: Display duration in milliseconds
            bg_color: Background color (e.g., "black")
            image_size: Tuple of (width, height) for image display
        """
        self.root = root
        self.image_path = image_path
        self.duration = duration
        self.bg_color = bg_color
        self.image_size = image_size

        # Create borderless top-level window
        self.splash = Toplevel(root)
        self.splash.overrideredirect(True)  # Remove window decorations
        self.splash.configure(bg=self.bg_color)
        
        # Center on screen with specified dimensions
        self.splash.geometry(f"{self.image_size[0]}x{self.image_size[1]}+{root.winfo_screenwidth() // 2 - self.image_size[0] // 2}+{root.winfo_screenheight() // 2 - self.image_size[1] // 2}")

        # Load and resize image to specified dimensions
        self.image = Image.open(self.image_path)
        self.image = self.image.resize(self.image_size, Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.image)

        # Display image in label
        self.label = Label(self.splash, image=self.photo, bg=self.bg_color)
        self.label.pack()

        # Auto-close splash screen after specified duration
        self.splash.after(self.duration, self.splash.destroy)
