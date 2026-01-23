"""
Custom dialog widgets for the Droplet Assay Analyzer GUI.

"""

import tkinter as tk
from tkinter import Toplevel, Label, Button, messagebox, simpledialog
from .window_utils import center_window

class CustomInputDialog(tk.Toplevel):
    """
    Custom modal input dialog for collecting user text input.
    
    Attributes:
        entry (tk.Entry): Text input widget
        result (str): User's input text, or None if cancelled
        
    Features:
        - Modal behavior (grab_set prevents parent interaction)
        - Auto-centered on screen
        - Default value support
        - Focus automatically set to input field
        - Submit and Cancel buttons with clear visual feedback
    """
    
    def __init__(self, parent, prompt, title="Input", initialvalue=""):
        """
        Initialize the custom input dialog.
        
        Args:
            parent: Parent Tkinter widget 
            prompt: Instruction text displayed above input field
            title: Dialog window title (default: "Input")
            initialvalue: Pre-filled text in input field (default: empty string)
        """
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()  # Make the dialog modal - prevents user from clicking parent window

        # Calculate centered window position on screen
        window_width = 450
        window_height = 150
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        # Configure grid layout with equal column weights for button centering
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Prompt label with readable font size
        label_font = ("Helvetica", 12)
        self.label = tk.Label(self, text=prompt, font=label_font)
        self.label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))

        # Text entry widget for user input
        entry_font = ("Helvetica", 12)
        self.entry = tk.Entry(self, font=entry_font)
        self.entry.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="we")
        self.entry.insert(0, str(initialvalue))  # Pre-fill with initial value
        self.entry.focus_set()  # Set keyboard focus to entry field

        # Frame container for buttons to keep them organized
        button_frame = tk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2)

        # Submit button - confirms user input
        button_font = ("Helvetica", 12)
        self.submit_button = tk.Button(button_frame, text="Submit", command=self.on_submit, font=button_font, width=10)
        self.submit_button.pack(side="left", padx=10)
        
        # Cancel button - dismisses dialog without result
        self.cancel_button = tk.Button(button_frame, text="Cancel", command=self.on_cancel, font=button_font, width=10)
        self.cancel_button.pack(side="right", padx=10)

        # Result variable - stores user input or None if cancelled
        self.result = None

    def on_submit(self):
        """
        Handle submit button click event.
        
        Captures the current entry text into result variable and closes dialog.
        This allows parent code to access the user's input via self.result.
        """
        self.result = self.entry.get()
        self.destroy()

    def on_cancel(self):
        """
        Handle cancel button click event.
        
        Closes dialog without modifying result (remains None).
        Parent code can distinguish between cancellation and submission by
        checking if result is None.
        """
        self.destroy()

class CustomMessageBox(tk.Toplevel):
    """
    Custom modal message box for displaying information to users.
    
    Provides a professional, centered message display dialog that extends
    tk.Toplevel. 
    
    Attributes:
        label (tk.Label): Message text widget with automatic wrapping
        ok_button (tk.Button): Single OK button to dismiss dialog
 
    """
    
    def __init__(self, parent, message, title="Message", msg_type="info"):
        """
        Initialize the custom message box dialog.
        
        Args:
            parent: Parent Tkinter widget 
            message: Message text to display
            title: Dialog window title
            msg_type: Message type indicator for future extensibility
        """
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()  # Make the dialog modal - blocks parent window interaction

        # Calculate centered window position on screen
        window_width = 450
        window_height = 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        # Configure grid with equal column weights for button centering
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Message label with text wrapping for readability
        label_font = ("Helvetica", 12)
        self.label = tk.Label(self, text=message, font=label_font, wraplength=400, justify="center")
        self.label.grid(row=0, column=0, columnspan=2, padx=20, pady=(30, 20))

        # Button frame for consistent button layout
        button_frame = tk.Frame(self)
        button_frame.grid(row=1, column=0, columnspan=2, pady=1)

        # OK button to dismiss dialog
        button_font = ("Helvetica", 12)
        self.ok_button = tk.Button(button_frame, text="OK", command=self.destroy, font=button_font, width=10)
        self.ok_button.pack()

class FrameSelectionDialog(simpledialog.Dialog):
    """
    Custom dialog for selecting start and end frame indices for analysis.
    
    Extends tk.simpledialog.Dialog to provide frame range input with validation.
    This dialog ensures users select valid frame ranges before image sequence
    processing begins. Essential for large image sequences where processing
    the entire sequence may be computationally expensive or unnecessary.
    
    The dialog validates that:
    - Start frame is >= 1 (frame indexing begins at 1)
    - End frame is >= start frame (logical sequence)
    - Both values are valid integers
    
    Attributes:
        start_frame (tk.Entry): Entry widget for start frame index
        end_frame (tk.Entry): Entry widget for end frame index
        result (tuple): (start, end) frame indices, or None if cancelled/invalid
        analyzer (DropletAssayAnalyzer): Optional reference to analyzer instance

    """
    
    def __init__(self, parent, analyzer, title=None, initial_start=1, initial_end=7200):
        """
        Initialize the frame selection dialog.
        
        Args:
            parent: Parent Tkinter widget (typically root window)
            analyzer: DropletAssayAnalyzer instance (optional; used for stop_processing flag)
            title: Dialog window title (default: None, uses Dialog's default)
            initial_start: Default starting frame index (default: 1, first frame)
            initial_end: Default ending frame index (default: 7200, typical sequence length)
                        This should be set to len(matching_files) for accurate defaults
        """
        # The analyzer parameter is optional; if provided, it will be used in on_cancel.
        self.analyzer = analyzer
        self.initial_start = initial_start
        self.initial_end = initial_end
        super().__init__(parent, title=title)

    def body(self, master):
        """
        Construct the dialog body with input fields.
        
        Called by Dialog class to populate the dialog content. Creates labels,
        entry fields, and configures the layout.
        
        Args:
            master: The frame widget to populate with dialog content
            
        Returns:
            tk.Entry: Widget to receive initial keyboard focus (start_frame entry)
        """
        self.geometry("400x200")
        # Use the imported center_window function instead of relying on analyzer.
        center_window(self)
        
        # Title label explaining the dialog purpose
        tk.Label(master, text="Please select start and end frames for the analysis",
                 font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 20))
        
        # Label for start frame input
        tk.Label(master, text="Start Frame:", font=("Helvetica", 11)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        
        # Label for end frame input
        tk.Label(master, text="End Frame:", font=("Helvetica", 11)).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        
        # Entry widget for start frame - pre-filled with initial_start value
        self.start_frame = tk.Entry(master, font=("Helvetica", 11))
        self.end_frame = tk.Entry(master, font=("Helvetica", 11))
        self.start_frame.insert(0, str(self.initial_start))
        self.end_frame.insert(0, str(self.initial_end))
        self.start_frame.grid(row=1, column=1, padx=10, pady=10)
        self.end_frame.grid(row=2, column=1, padx=10, pady=10)
        
        # Return start_frame to receive initial keyboard focus
        return self.start_frame

    def apply(self):
        """
        Validate and process user input from the dialog.
        
        Called by Dialog class when user clicks OK button. Validates that:
        1. Both inputs are valid integers
        2. Start frame >= 1 (valid indexing)
        3. End frame >= start frame (logical range)
        
        If validation fails, displays error message and calls on_cancel.
        If successful, stores (start, end) tuple in self.result.
    
        """
        try:
            start = int(self.start_frame.get())
            end = int(self.end_frame.get())
            # Validate frame range logic
            if start < 1 or end < start:
                raise ValueError
            self.result = (start, end)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integer values.")
            self.result = None
            self.on_cancel()

    def on_cancel(self):
        """
        Handle cancel action from dialog.
    
        """
        print("Frame selection dialog canceled by the user.")
        self.result = None
        if self.analyzer is not None:
            self.analyzer.stop_processing = True
