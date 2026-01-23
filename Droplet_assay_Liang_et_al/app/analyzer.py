"""
Droplet Assay Analyzer - Analyzer module.

This module implements the core analysis workflow for the droplet assay system, 
managing single and batch image processing pipelines with interactive ROI selection
and signal analysis.

"""

import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import traceback
from skimage import io

from gui.splash import SplashScreen
from gui.window_utils import center_window
from gui.dialogs import CustomInputDialog, CustomMessageBox
from image_processing import process_images
from signal_processing import SignalProcessor
from analysis import analyze_turns
from auto_roi_detection import detect_circles_in_image
from .file_selection import file_type_dialog
from .roi_selection import roi_method_dialog


class DropletAssayAnalyzer:
    """
    Main analyzer class for the droplet assay application.
    
    Manages the complete workflow including file selection, ROI definition,
    image processing, signal analysis, and result visualization. Supports
    both single and batch processing modes.
    """
    
    def __init__(self):
        """
        Initialize the analyzer with a Tkinter root window and default attributes.
        
        Sets up the main application window, protocol handlers, and initializes
        all analysis parameters to None or default values.
        """
        self.root = tk.Tk()
        # Attach analyzer to root so other modules can retrieve it without changing signatures
        self.root.analyzer = self
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.stop_processing = False
        self.batch_mode = False
        self.batch_directories = []
        self._init_attributes()

    def _init_attributes(self):
        """
        Initialize all analysis-related instance attributes to None or default values.
        
        Attributes include:
        - File metadata: directory, filename, base_filename, extension, prefix
        - Image properties: frame indices, image dimensions
        - Analysis data: ROI coordinates, binary morphological measurements
        - Processing parameters: thresholds and filter sizes for signal processing
        """
        self.directory = self.filename = self.base_filename = None
        self.ext = self.prefix = None
        self.istart = self.iend = self.numframes = None
        self.image = None
        self.ysize = self.xsize = None
        self.matching_files = []
        self.roi_coords = None
        self.ignore_worm = None
        self.bw_Area = self.bw_Centroid = self.bw_Eccentricity = None
        # Default analysis parameters
        self.params = {
            'Eccentricity_filsize': 3,         # Filter size for eccentricity measurements
            'Area_filsize': 9,                 # Filter size for area measurements
            'Centroid_filsize': 9,             # Filter size for centroid measurements
            'peak_det_abs_threshold': 0.85,    # Absolute threshold for peak detection
            'peak_det_threshold': 0.15,        # Relative threshold for peak detection
            'Centroid_r_threshold': 0.7,       # Correlation threshold for centroid tracking
            'area_threshold': 0.7,             # Correlation threshold for area tracking
        }

    def on_closing(self):
        """Handle application window close event."""
        print("User requested exit.")
        self.stop_processing = True
        self.root.quit()
        self.root.destroy()

    def run(self):
        """
        Start the application main loop.
        
        Displays splash screen, prompts user to select analysis mode (single or batch),
        and executes the appropriate workflow.
        """
        splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Droplet_Assay_Logo.png')
        self.splash = SplashScreen(self.root, splash_path, duration=2000, bg_color="black", image_size=(300, 350))
        self.root.after(2000, self.select_analysis_mode)
        self.root.mainloop()

        if self.stop_processing:
            sys.exit("Processing aborted.")
        else:
            print("Processing complete.")
            self.cleanup_and_exit()

    def select_analysis_mode(self):
        """
        Display dialog for user to choose between single and batch analysis modes.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Analysis Mode")
        dialog.geometry("300x150")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)

        tk.Label(dialog, text="Select analysis mode:", font=("Helvetica", 12)).pack(pady=10)

        frame = tk.Frame(dialog)
        frame.pack(pady=10)

        tk.Button(frame, text="Single Analysis", command=lambda: self.set_analysis_mode(dialog, False)).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Batch Analysis", command=lambda: self.set_analysis_mode(dialog, True)).pack(side=tk.LEFT, padx=5)

        dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_analysis_mode(self, dialog, batch_mode):
        """
        Set the analysis mode and proceed accordingly.
        
        Args:
            dialog: The dialog window to close
            batch_mode: Boolean indicating batch (True) or single (False) analysis
        """
        self.batch_mode = batch_mode
        dialog.destroy()
        self.select_batch_directories() if batch_mode else self.run_single_analysis()

    def run_single_analysis(self):
        """
        Execute single file analysis workflow.
        
        Sequentially prompts for file type selection, finds matching image files,
        selects ROI method, and processes images and signals.
        """
        try:
            if not self.select_file_type():
                if self.stop_processing:
                    self.on_closing() 
                return
            if not self.find_matching_files():
                if self.stop_processing:
                    self.on_closing()
                return
            if not self.select_roi_method() or not self.roi_coords:
                if self.stop_processing:
                    self.on_closing()
                return
            self.process_images_and_signals()
        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
        finally:
            if not self.stop_processing:
                print("Single analysis completed")

    def select_batch_directories(self):
        """
        Display dialog for user to select multiple directories for batch processing.
        
        Allows users to add/remove directories from a list and initiate batch analysis
        when ready.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Directories for Batch Processing")
        dialog.geometry("500x400")
        center_window(dialog)

        tk.Label(dialog, text="Select directories to analyze:", font=("Helvetica", 12)).pack(pady=10)
        listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE, width=60, height=15)
        listbox.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        def add_directory():
            path = filedialog.askdirectory()
            if path:
                listbox.insert(tk.END, path)

        def remove_selected():
            for i in reversed(listbox.curselection()):
                listbox.delete(i)

        tk.Button(dialog, text="Add Directory", command=add_directory).pack()
        tk.Button(dialog, text="Remove Selected", command=remove_selected).pack()
        tk.Button(dialog, text="Start Batch Processing", command=lambda: self.start_batch(dialog, listbox)).pack(pady=10)
        dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_batch(self, dialog, listbox):
        """
        Validate directory selection and initiate batch processing.
        
        Args:
            dialog: The directory selection dialog
            listbox: Listbox widget containing selected directories
        """
        if listbox.size() == 0:
            tk.messagebox.showwarning("Warning", "Please select at least one directory.")
            return
        self.batch_directories = list(listbox.get(0, tk.END))
        dialog.destroy()
        self.run_batch_analysis()

    def collect_analysis_dirs(self, paths, recursive: bool = False, require_files=()):
        """
        Normalize and expand a mixed selection of directories into a flat list of analysis directories.
        
        Handles both parent and leaf directories, optionally filtering by required files.
        Removes duplicates and returns a sorted list.

        Args:
            paths: Iterable of directory paths
            recursive: If False, expands immediate subdirs; if True, includes all nested subdirs via os.walk
            require_files: Optional iterable of filenames that must exist in a directory for inclusion

        Returns:
            Sorted list of valid analysis directories
        """
        def _immediate_subdirs(path: str):
            """Get immediate subdirectories of the given path."""
            try:
                return [
                    os.path.join(path, d)
                    for d in os.listdir(path)
                    if os.path.isdir(os.path.join(path, d))
                ]
            except Exception:
                return []
            
        out, seen = [], set()
        req = tuple(require_files) if require_files else ()

        def eligible(d: str) -> bool:
            """Check if directory contains all required files."""
            return all(os.path.exists(os.path.join(d, f)) for f in req)

        for base in (paths or []):
            if not os.path.isdir(base):
                continue
            base = os.path.normpath(base)

            if recursive:
                # Include all nested directories
                for d, subdirs, _files in os.walk(base):
                    d = os.path.normpath(d)
                    if d not in seen and (not req or eligible(d)):
                        seen.add(d); out.append(d)
            else:
                # Use immediate subdirectories if they exist, otherwise use base directory
                subs = _immediate_subdirs(base)
                if subs:
                    for d in subs:
                        d = os.path.normpath(d)
                        if d not in seen and (not req or eligible(d)):
                            seen.add(d); out.append(d)
                else:
                    if base not in seen and (not req or eligible(base)):
                        seen.add(base); out.append(base)

        out.sort()
        return out

    def run_batch_analysis(self):
        """
        Execute batch analysis on all selected directories.
        
        Expands user-selected directories using directory collection logic, displays
        progress dialog, processes each directory, and provides summary of results
        including any failures encountered.
        """
        # Expand selection to include parent or leaf directories
        all_dirs = self.collect_analysis_dirs(self.batch_directories, recursive=True, require_files=('w1a000000.jpg',))
        # Set recursive=False to only use immediate subdirectories

        if not all_dirs:
            tk.messagebox.showerror("Error", "No valid directories found for batch processing")
            self.cleanup_and_exit()
            return

        # Create progress dialog
        progress = tk.Toplevel(self.root)
        progress.title("Batch Processing Progress")
        progress.geometry("820x180")
        center_window(progress)

        status_lbl = tk.Label(progress, text="", font=("Helvetica", 12))
        status_lbl.pack(pady=10)

        var = tk.DoubleVar(value=0)
        bar = ttk.Progressbar(progress, variable=var, maximum=len(all_dirs))
        bar.pack(pady=10, padx=20, fill=tk.X)

        tk.Button(progress, text="Cancel",
                command=lambda: self.cancel_batch_processing(progress)).pack(pady=5)

        self.stop_processing = False
        failures = []

        # Process each directory
        for i, directory in enumerate(all_dirs, start=1):
            if self.stop_processing:
                break

            status_lbl.config(text=f"Processing {i}/{len(all_dirs)}: {directory}")
            progress.update()

            try:
                self.directory = directory
                self.process_single_batch_item()  # Process current directory
            except Exception as e:
                print(f"[WARN] Analysis failed for: {directory}\nReason: {e}")
                traceback.print_exc()
                failures.append((directory, str(e)))
                # Continue to next directory on error
            finally:
                var.set(i)
                progress.update()

        progress.destroy()

        # Display summary results
        if failures:
            lines = "\n\n".join(f"- {d}\n  {err}" for d, err in failures[:10])
            if len(failures) > 10:
                lines += f"\n\n... and {len(failures) - 10} more."
            tk.messagebox.showwarning(
                "Batch finished with errors",
                f"Processed {len(all_dirs)} directories.\n"
                f"Failures: {len(failures)}\n\n{lines}"
            )
        else:
            tk.messagebox.showinfo("Batch finished",
                                f"Processed {len(all_dirs)} directories successfully.")

        self.cleanup_and_exit()


    def cancel_batch_processing(self, window):
        """
        Cancel batch processing and close progress window.
        
        Args:
            window: The progress dialog window to close
        """
        self.stop_processing = True
        window.destroy()

    def process_single_batch_item(self):
        """
        Process a single directory in batch mode with automatic circle detection.
        
        Uses automatic ROI detection to identify circles in images, converts circle
        parameters to ROI coordinates, and processes all detected droplets without
        user intervention.
        """
        self.roi_method = "auto"
        self.ignore_worm = False
        if not self.find_matching_files():
            return

        # Sample images at regular intervals for circle detection
        image_list = [
            os.path.join(self.directory, f)
            for f in self.matching_files[::100]
            if os.path.basename(f).startswith('w1a')
        ]
        circles, annotated, _, _ = detect_circles_in_image(image_list)
        h, w = annotated.shape[:2]

        self.roi_coords = []
        self.ignore_worm = []
        pad = 5  # Padding around detected circles

        # Convert circle detection results to ROI coordinates
        for c in circles:
            x, y, r = int(c["x"]), int(c["y"]), int(c["radius"])
            self.roi_coords.append(((max(0, x - r - pad), max(0, y - r - pad)), (min(w, x + r + pad), min(h, y + r + pad))))
            self.ignore_worm.append(False)
        
        self.process_images_and_signals()

    def find_matching_files(self):
        """
        Search for image files matching the analysis prefix in the current directory.
        
        Finds all image files starting with 'w1a' prefix, sorts them, extracts image
        dimensions from the first image, and stores metadata for analysis.
        
        Returns:
            True if matching files found and successfully processed, False otherwise
        """
        try:
            self.prefix = "w1a"
            files = os.listdir(self.directory)
            # Filter for matching image files with standard image extensions
            self.matching_files = sorted([f for f in files if f.lower().startswith(self.prefix) and f.lower().endswith(('jpg','jpeg','png','tiff','tif'))])
            if not self.matching_files:
                print(f"No matching files in {self.directory}")
                return False
            self.istart = 1
            self.iend = len(self.matching_files)
            self.numframes = self.iend - self.istart + 1
            img = io.imread(os.path.join(self.directory, self.matching_files[0]))
            self.image = img
            self.ysize, self.xsize = img.shape[:2]
            return True
        except Exception as e:
            print(f"Error finding files: {e}")
            return False

    def process_images_and_signals(self):
        """
        Process all images in the current sequence using morphological operations.
        
        Extracts binary morphological features (area, centroid, eccentricity) for
        each ROI across all frames. Proceeds to signal processing if successful.
        """
        self.bw_Area, self.bw_Centroid, self.bw_Eccentricity = process_images(
            self, self.directory, self.matching_files, self.roi_coords, self.ignore_worm)

        if any(v is None for v in (self.bw_Area, self.bw_Centroid, self.bw_Eccentricity)):
            print("Image processing interrupted.")
            return

        self.process_signals_and_analyze()

    def process_signals_and_analyze(self):
        """
        Apply signal processing to morphological measurements and perform turn analysis.
        
        In single mode, prompts user for analysis parameters. Applies filtering,
        peak detection, and turn identification. Results are visualized and saved
        to the analysis directory.
        """
        if not self.batch_mode:
            self.get_parameters(self.params)
            if self.stop_processing:
                return

        # Process signals with user-defined or default parameters
        processor = SignalProcessor(
            self.bw_Eccentricity, self.bw_Centroid, self.bw_Area, self.roi_coords
        )

        valid_turns, invalid_data, ecc_filt, area_filt, centroid_r_filt, radius = processor.process_signals(self.params)

        # Store filtered measurements for visualization
        self.bw_Eccentricity_filtered = ecc_filt
        self.bw_Area_filtered = area_filt
        self.bw_Centroid_r_filtered = centroid_r_filt

        # Analyze turns and generate output
        analyze_turns(
            valid_turns, invalid_data, self.numframes, self.roi_coords, self.params,
            self.root, self.directory, ecc_filt, show_plots=not self.batch_mode, batch_mode=self.batch_mode
        )

        if not self.batch_mode:
            self.cleanup_and_exit()

    def get_parameters(self, params):
        """
        Display dialog for user to input analysis parameters (single mode only).
        
        Allows adjustment of peak detection thresholds and correlation thresholds
        for signal tracking. Parameters are validated as numeric values.
        
        Args:
            params: Dictionary to update with user-provided parameter values
        """
        if self.batch_mode:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Parameters")
        dialog.geometry("400x400")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.columnconfigure(1, weight=1)

        # Define editable parameters
        keys = ['peak_det_abs_threshold', 'peak_det_threshold', 'Centroid_r_threshold', 'area_threshold']
        labels = ["Peak Detection Absolute Threshold", "Peak Detection Threshold", "Centroid Radius Threshold", "Area Threshold"]
        entries = {}

        tk.Label(dialog, text="Select analysis parameters:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 10))

        for idx, label_text in enumerate(labels):
            row = idx * 2 + 1
            tk.Label(dialog, text=label_text, font=("Helvetica", 12)).grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")
            entry = tk.Entry(dialog, width=40)
            entry.insert(0, str(params[keys[idx]]))
            entry.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
            entries[keys[idx]] = entry

        def on_ok():
            """Validate and apply parameter changes."""
            try:
                for k in keys:
                    params[k] = float(entries[k].get().strip())
                dialog.destroy()
            except ValueError:
                tk.messagebox.showerror("Invalid Input", "Please enter valid numeric values.")

        def on_cancel():
            """Cancel and abort processing."""
            self.stop_processing = True
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        tk.Button(dialog, text="OK", width=15, command=on_ok).grid(row=len(keys)*2+1, column=0, padx=10, pady=10, sticky='w')
        tk.Button(dialog, text="Cancel", width=15, command=on_cancel).grid(row=len(keys)*2+1, column=1, padx=10, pady=10, sticky='e')

        dialog.wait_window(dialog)

    def cleanup_and_exit(self):
        """Properly close the application and exit."""
        self.root.destroy()
        sys.exit()

    def select_file_type(self):
        """Display dialog for file type selection. Delegates to file_type_dialog module."""
        return file_type_dialog(self)

    def select_roi_method(self):
        """Display dialog for ROI selection method. Delegates to roi_method_dialog module."""
        return roi_method_dialog(self)

    def custom_askinteger(self, title, prompt, initialvalue=12):
        """
        Display custom integer input dialog.
        
        Args:
            title: Dialog title
            prompt: Input prompt message
            initialvalue: Default value (default: 12)
            
        Returns:
            Integer value entered by user, or None if invalid
        """
        dialog = CustomInputDialog(self.root, prompt, title=title, initialvalue=initialvalue)
        self.root.wait_window(dialog)
        result = dialog.result
        return int(result) if result and result.isdigit() else None

    def custom_print(self, message):
        """
        Display custom message box with information.
        
        Args:
            message: Message text to display
        """
        dialog = CustomMessageBox(self.root, message, title="Information")
        self.root.wait_window(dialog)
