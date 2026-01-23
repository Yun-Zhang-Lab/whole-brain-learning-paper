"""
ROI grouping dialog and configuration module.

Provides interface for users to group ROIs into analysis categories.
Supports predefined groupings and custom user-defined configurations.
"""

# # gui/grouping.py

import tkinter as tk
import numpy as np
from tkinter import messagebox
from .window_utils import center_window

class GroupingApp:
    """Manages ROI grouping selection and configuration dialogs."""
    
    def __init__(self, root):
        """Initialize grouping app with root window reference."""
        self.root = root

    def get_grouping(self, num_roi, batch_mode=False):
        """
        Get ROI grouping configuration from user.
        
        Args:
            num_roi: Number of ROIs to group
            batch_mode: If True, auto-select standard grouping without dialog
            
        Returns:
            Tuple of (num_groups, groups_array_list) or None if cancelled
        """
        # Auto-select grouping in batch mode
        if batch_mode and num_roi == 12:
            num_groups = 2
            groups = [np.arange(0, 6), np.arange(6, 12)]
            return num_groups, groups
            
        # Dialog callback handlers
        def on_button_click(option):
            nonlocal grouping_option
            grouping_option = option
            dialog.destroy()

        def on_custom_submit():
            nonlocal custom_grouping
            custom_grouping = custom_entry.get()
            dialog.destroy()

        def on_closing_local():
            print("Grouping selection dialog closed by the user.")
            nonlocal grouping_option
            grouping_option = None
            dialog.destroy()
            self.root.quit()

        grouping_option = None
        custom_grouping = None

        # Create grouping selection dialog
        width = 400
        height = 200
        dialog = tk.Toplevel(self.root)
        dialog.title("Grouping Selection")
        dialog.geometry(f"{width}x{height}")
        center_window(dialog)
        dialog.protocol("WM_DELETE_WINDOW", on_closing_local)

        # 12 ROI configuration
        if num_roi == 12:
            tk.Label(dialog, text="Select grouping option:", font=("Helvetica", 12, "bold")).grid(
                row=0, column=0, columnspan=2, pady=(10, 10)
            )
            button1 = tk.Button(dialog, text="1) 1-3, 4-6, 7-9, 10-12", font=8, width=30, command=lambda: on_button_click("1"))
            button2 = tk.Button(dialog, text="2) 1-6, 7-12", width=30, font=8, command=lambda: on_button_click("2"))
            button3 = tk.Button(dialog, text="3) Custom grouping", width=30, font=8, command=lambda: on_button_click("3"))
            button1.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
            button2.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
            button3.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
            dialog.columnconfigure(0, weight=1)
            dialog.wait_window()
            
            if grouping_option == "1":
                num_groups = 4
                groups = [np.arange(0, 3), np.arange(3, 6), np.arange(6, 9), np.arange(9, 12)]
            elif grouping_option == "2":
                num_groups = 2
                groups = [np.arange(0, 6), np.arange(6, 12)]
            elif grouping_option == "3":
                # Custom grouping input dialog
                dialog = tk.Toplevel(self.root)
                dialog.title("Custom Grouping")
                dialog.geometry("400x150")
                tk.Label(dialog, text="Enter custom groups separated by commas\n(e.g., '0-5,6-11'):", font=("Helvetica", 12)).pack(pady=(10, 5))
                custom_entry = tk.Entry(dialog, width=40)
                custom_entry.pack(pady=5)
                tk.Button(dialog, text="Submit", width=15, command=on_custom_submit).pack(pady=(5, 10))
                dialog.wait_window()
                
                if not custom_grouping:
                    messagebox.showerror("Input Error", "No custom grouping entered.")
                    return None
                
                # Parse custom grouping string
                groups_str = custom_grouping.split(',')
                groups = []
                for grp in groups_str:
                    if '-' in grp:
                        try:
                            start, end = map(int, grp.strip().split('-'))
                            groups.append(np.arange(start, end + 1))
                        except ValueError:
                            messagebox.showerror("Input Error", f"Invalid range '{grp}'.")
                            return None
                    else:
                        try:
                            groups.append(np.array([int(grp.strip())]))
                        except ValueError:
                            messagebox.showerror("Input Error", f"Invalid group '{grp}'.")
                            return None
                num_groups = len(groups)
            else:
                messagebox.showerror("Invalid Selection", "Invalid or No grouping option selected.")
                return None
                
        # 15 ROI configuration
        elif num_roi == 15:
            tk.Label(dialog, text="Select grouping option:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, pady=(10, 10))
            button1 = tk.Button(dialog, text="1) 1-6, 10-12, 7-9, 13-15", width=30, command=lambda: on_button_click("1"))
            button1.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
            dialog.columnconfigure(0, weight=1)
            dialog.wait_window()
            
            if grouping_option == "1":
                num_groups = 4
                groups = [np.arange(0, 6), np.arange(9, 12), np.arange(6, 9), np.arange(12, 15)]
            else:
                messagebox.showerror("Invalid Selection", "Invalid or No grouping option selected.")
                return None
        else:
            messagebox.showerror("Unsupported ROI Count", f"Grouping not defined for {num_roi} ROIs.")
            return None

        return num_groups, groups
