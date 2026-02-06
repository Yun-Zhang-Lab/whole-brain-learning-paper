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
from .roi_selection import roi_method_dialog, auto_roi


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
        self.batch_analysis_mode = "separate"  # Default: analyze each folder separately
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
        """
        Handle application window close event safely.
        
        Safe to call multiple times. Sets stop flag, cleans up root window,
        and ensures the application exits completely.
        """
        print("User requested exit.")
        self.stop_processing = True
        try:
            # Only quit if the window still exists and root is active
            if self.root.winfo_exists():
                self.root.quit()
        except Exception as e:
            print(f"Error during quit: {e}")
        try:
            # Only destroy if the window still exists
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            print(f"Error during destroy: {e}")
        # Ensure complete exit
        sys.exit(0)

    def run(self):
        """
        Start the application main loop.
        
        Displays splash screen, prompts user to select analysis mode (single or batch),
        and executes the appropriate workflow. Ensures safe exit on any error.
        """
        try:
            splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Droplet_Assay_Logo.png')
            self.splash = SplashScreen(self.root, splash_path, duration=2000, bg_color="black", image_size=(300, 350))
            self.root.after(2000, self.select_analysis_mode)
            self.root.mainloop()

            if self.stop_processing:
                sys.exit(0)
            else:
                print("Processing complete.")
                self.cleanup_and_exit()
        except Exception as e:
            print(f"Error in main application loop: {e}")
            import traceback
            traceback.print_exc()
            self.safe_exit_with_error(str(e))

    def select_analysis_mode(self):
        """
        Display dialog for user to choose between single and batch analysis modes.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Analysis Mode Selection")
        dialog.geometry("500x280")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.resizable(False, False)

        tk.Label(dialog, text="Select analysis mode:", font=("Helvetica", 14, "bold")).pack(pady=30)

        frame = tk.Frame(dialog)
        frame.pack(pady=20, padx=40, fill=tk.X)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        tk.Button(frame, text="Single Analysis", font=("Helvetica", 12), height=2, 
                 command=lambda: self.set_analysis_mode(dialog, False)).grid(row=0, column=0, padx=10, sticky="ew")
        tk.Button(frame, text="Batch Analysis", font=("Helvetica", 12), height=2,
                 command=lambda: self.set_analysis_mode(dialog, True)).grid(row=0, column=1, padx=10, sticky="ew")

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
        
        Prompts user to choose between analyzing a single folder or multiple
        timestamp folders. Then sequentially prompts for file type selection,
        finds matching image files, selects ROI method, and processes images 
        and signals. Ensures safe exit on error.
        """
        try:
            # Ask user whether to analyze single folder or timestamp folders
            analysis_type = self.select_single_analysis_type()
            if analysis_type is None:  # User cancelled
                return
            
            self.single_analysis_type = analysis_type
            
            if not self.select_file_type():
                return
            if not self.find_matching_files():
                return
            if not self.select_roi_method() or not self.roi_coords:
                return
            self.process_images_and_signals()
        except Exception as e:
            print(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")
            self.stop_processing = True
        finally:
            if self.stop_processing:
                self.on_closing()
            elif not self.stop_processing:
                print("Single analysis completed")

    def select_single_analysis_type(self):
        """
        Display dialog for user to choose single analysis type.
        
        Options:
        1. Single Folder - Analyze a specific folder selected by the user
        2. Timestamp Folders - Analyze all timestamp-named folders in a directory
        
        Returns:
            'single' for single folder analysis
            'timestamp' for timestamp folders analysis
            None if user cancels
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Single Analysis Type")
        dialog.geometry("400x220")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.resizable(False, False)
        
        result = [None]  # Mutable container to store result
        
        tk.Label(dialog, text="How would you like to analyze?", font=("Helvetica", 12, "bold")).pack(pady=20)
        
        frame = tk.Frame(dialog)
        frame.pack(pady=10, padx=20, fill=tk.X)
        
        tk.Button(
            frame,
            text="Single Folder",
            command=lambda: self._set_analysis_type(dialog, result, 'single'),
            width=25,
            height=2
        ).pack(pady=8, fill=tk.X)
        
        tk.Button(
            frame,
            text="Combine Timestamp Folders",
            command=lambda: self._set_analysis_type(dialog, result, 'timestamp'),
            width=25,
            height=2
        ).pack(pady=8, fill=tk.X)
        
        dialog.protocol("WM_DELETE_WINDOW", lambda: self._set_analysis_type(dialog, result, None))
        
        self.root.wait_window(dialog)
        return result[0]
    
    def _set_analysis_type(self, dialog, result, value):
        """
        Set analysis type result and close dialog.
        
        Args:
            dialog: The dialog window to close
            result: Mutable list to store the selected value
            value: The analysis type ('single', 'timestamp', or None for cancel)
        """
        result[0] = value
        dialog.destroy()

    def select_batch_directories(self):
        """
        Display dialog for user to select multiple directories for batch processing.
        
        Allows users to add/remove directories from a list and initiate batch analysis
        when ready.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Directories for Batch Processing")
        dialog.geometry("650x550")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.resizable(False, False)

        # Title
        tk.Label(dialog, text="Select directories to analyze:", font=("Helvetica", 13, "bold")).pack(pady=15)
        
        # Listbox frame
        listbox_frame = tk.Frame(dialog)
        listbox_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, font=("Helvetica", 10), height=15)
        listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        def add_directory():
            path = filedialog.askdirectory()
            if path:
                listbox.insert(tk.END, path)

        def remove_selected():
            for i in reversed(listbox.curselection()):
                listbox.delete(i)

        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=15, padx=20, fill=tk.X)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        tk.Button(button_frame, text="Add Directory", font=("Helvetica", 11), height=2,
                 command=add_directory).grid(row=0, column=0, padx=5, sticky="ew")
        tk.Button(button_frame, text="Remove Selected", font=("Helvetica", 11), height=2,
                 command=remove_selected).grid(row=0, column=1, padx=5, sticky="ew")
        tk.Button(button_frame, text="Start Processing", font=("Helvetica", 11, "bold"), height=2,
                 command=lambda: self.start_batch(dialog, listbox)).grid(row=0, column=2, padx=5, sticky="ew")
        
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
        self.select_batch_analysis_mode()

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

    def select_batch_analysis_mode(self):
        """
        Display dialog for user to choose batch analysis mode.
        
        Options:
        1. Analyze each subfolder separately (independent analyses)
        2. Analyze all subfolders as one experiment (combined images, single ROI selection)
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("Batch Analysis Mode")
        dialog.geometry("550x220")
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.resizable(False, False)

        tk.Label(dialog, text="How would you like to analyze potential subfolders?", font=("Helvetica", 12, "bold")).pack(pady=20)

        frame = tk.Frame(dialog)
        frame.pack(pady=10, padx=20, fill=tk.X)

        def set_batch_mode(mode):
            dialog.destroy()
            self.batch_analysis_mode = mode
            self.run_batch_analysis()

        tk.Button(
            frame,
            text="Analyze each subfolder separately",
            width=25,
            height=2,
            command=lambda: set_batch_mode("separate")
        ).pack(pady=8, fill=tk.X)
        
        tk.Button(
            frame,
            text="Combine all subfolders",
            width=25,
            height=2,
            command=lambda: set_batch_mode("combined")
        ).pack(pady=8, fill=tk.X)

        dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def run_batch_analysis(self):
        """
        Execute batch analysis on all selected directories.
        
        Expands user-selected directories using directory collection logic, displays
        progress dialog, processes each directory, and provides summary of results
        including any failures encountered. Ensures safe exit on critical errors.
        
        Supports two modes:
        - separate: Analyze each directory independently (default)
        - combined: Treat all images from all directories as one experiment
        """
        try:
            # Check which analysis mode was selected
            if self.batch_analysis_mode == "combined":
                self.run_combined_batch_analysis()
            else:
                self.run_separate_batch_analysis()
        except Exception as e:
            print(f"Critical error during batch processing: {e}")
            import traceback
            traceback.print_exc()
            tk.messagebox.showerror("Critical Error", f"Batch processing failed: {str(e)}")
            self.safe_exit_with_error(str(e))

    def run_separate_batch_analysis(self):
        """
        Execute batch analysis where each subdirectory in selected directories is analyzed separately.
        
        For each selected directory, finds all immediate subdirectories with images,
        and processes each subdirectory as an independent analysis. Displays progress
        dialog and provides summary of results.
        """
        try:
            all_dirs = []
            
            # For each selected directory, collect all its subdirectories with images
            for base_dir in self.batch_directories:
                # Collect immediate subdirectories
                subdirs = self.collect_analysis_dirs([base_dir], recursive=False)
                
                if not subdirs:
                    # If no subdirectories, use the base directory itself
                    all_dirs.append(base_dir)
                else:
                    all_dirs.extend(subdirs)
            
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

            print("[INFO] Batch processing complete. Exiting application.")
            self.cleanup_and_exit()
        except Exception as e:
            print(f"Critical error during separate batch processing: {e}")
            import traceback
            traceback.print_exc()
            tk.messagebox.showerror("Critical Error", f"Batch processing failed: {str(e)}")
            self.safe_exit_with_error(str(e))

    def run_combined_batch_analysis(self):
        """
        Execute combined batch analysis where all subdirectories in each selected directory are pooled as one experiment.
        
        For each selected directory, collects all images from all its subdirectories,
        maintains proper order, performs single ROI selection, and analyzes as one experiment.
        Repeats for each selected directory.
        """
        try:
            # Create progress dialog
            progress = tk.Toplevel(self.root)
            progress.title("Batch Processing Progress")
            progress.geometry("820x180")
            center_window(progress)

            status_lbl = tk.Label(progress, text="", font=("Helvetica", 12))
            status_lbl.pack(pady=10)

            var = tk.DoubleVar(value=0)
            bar = ttk.Progressbar(progress, variable=var, maximum=len(self.batch_directories))
            bar.pack(pady=10, padx=20, fill=tk.X)

            tk.Button(progress, text="Cancel",
                    command=lambda: self.cancel_batch_processing(progress)).pack(pady=5)

            self.stop_processing = False
            failures = []

            # Process each selected directory as a combined experiment
            for i, base_dir in enumerate(self.batch_directories, start=1):
                if self.stop_processing:
                    break

                status_lbl.config(text=f"Processing {i}/{len(self.batch_directories)}: {base_dir}")
                progress.update()

                try:
                    # Reset analysis attributes for this directory
                    self._init_attributes()
                    
                    # Collect all subdirectories in this base directory
                    subdirs = self.collect_analysis_dirs([base_dir], recursive=False)
                    
                    if not subdirs:
                        # If no subdirectories, use the base directory itself
                        subdirs = [base_dir]
                    
                    # Collect all matching files from all subdirectories, maintaining order
                    all_matching_files = []
                    for directory in subdirs:
                        try:
                            # Recursively find all w1a images in this directory and subdirectories
                            image_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.tif')
                            
                            # Use os.walk to recursively find images
                            all_nested_dirs = []
                            for root, dirs, files in os.walk(directory):
                                dirs.sort()  # Sort for consistent order
                                all_nested_dirs.append(root)
                            
                            # Process directories in sorted order
                            for nested_dir in sorted(all_nested_dirs):
                                files = os.listdir(nested_dir)
                                dir_files = sorted([
                                    f for f in files
                                    if f.lower().startswith('w1a')
                                    and (
                                        any(f.lower().endswith(ext) for ext in image_extensions)
                                        or '.' not in f
                                    )
                                ])
                                # Store full paths from this directory
                                for f in dir_files:
                                    all_matching_files.append(os.path.join(nested_dir, f))
                        except Exception as e:
                            print(f"[WARN] Could not read directory {directory}: {e}")

                    if not all_matching_files:
                        print(f"[WARN] No matching images found in {base_dir}")
                        continue

                    # For combined batch mode, save results to the top directory (base_dir)
                    # not to any subdirectory
                    self.directory = base_dir
                    self.matching_files = all_matching_files
                    self.istart = 1
                    self.iend = len(self.matching_files)
                    self.numframes = self.iend - self.istart + 1

                    # Load first image for display (from first subdirectory)
                    self.image = io.imread(all_matching_files[0])
                    self.ysize, self.xsize = self.image.shape[:2]

                    print(f"[INFO] Processing {len(all_matching_files)} images from {len(subdirs)} subdirectories in {base_dir}")

                    # Use automatic ROI detection (no dialog in batch mode)
                    print(f"[INFO] Running automatic ROI detection for {base_dir}")
                    auto_roi(self)
                    
                    if not self.roi_coords:
                        print(f"[WARN] No ROIs detected for {base_dir}")
                        continue

                    # Process all images from this directory as one experiment
                    print(f"[INFO] Starting analysis for {base_dir}")
                    self.process_images_and_signals()
                    print(f"[INFO] Completed analysis for {base_dir}")

                except Exception as e:
                    print(f"[WARN] Analysis failed for: {base_dir}\nReason: {e}")
                    traceback.print_exc()
                    failures.append((base_dir, str(e)))
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
                    f"Processed {len(self.batch_directories)} directories.\n"
                    f"Failures: {len(failures)}\n\n{lines}"
                )
            else:
                tk.messagebox.showinfo("Batch finished",
                                    f"Processed {len(self.batch_directories)} directories successfully.")

            print("[INFO] Batch processing complete. Exiting application.")
            self.cleanup_and_exit()
        except Exception as e:
            print(f"Critical error during combined batch processing: {e}")
            import traceback
            traceback.print_exc()
            tk.messagebox.showerror("Critical Error", f"Batch processing failed: {str(e)}")
            self.safe_exit_with_error(str(e))

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
        # self.matching_files already contains full paths
        image_list = self.matching_files[::100] if len(self.matching_files) > 0 else []
        
        if not image_list:
            print(f"[WARN] No images to sample for circle detection in {self.directory}")
            return
        
        # In separate batch mode, save ROI files to the subdirectory being analyzed (default)
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
        Recursively search for image files matching the analysis prefix in all subdirectories.
        
        Finds all image files starting with 'w1a' prefix in the directory and all
        subdirectories, maintains proper order (by directory then by filename),
        extracts image dimensions from the first image, and stores metadata for analysis.
        Stores full paths to each image file in consistent order.
        
        Order is maintained as: all files from directory 1 (alphabetical),
        then all files from directory 2 (alphabetical), etc.
        
        Returns:
            True if matching files found and successfully processed, False otherwise
        """
        try:
            self.prefix = "w1a"
            
            # Recursively find all matching image files, maintaining directory order
            self.matching_files = []
            image_extensions = ('jpg', 'jpeg', 'png', 'tiff', 'tif')
            
            # Collect all directories first and sort them
            all_dirs = []
            for root, dirs, files in os.walk(self.directory):
                dirs.sort()
                all_dirs.append(root)

            # Sort directories by name (timestamp)
            for directory in sorted(all_dirs):
                try:
                    files = os.listdir(directory)
                    # Find and sort matching files in this directory
                    dir_files = sorted([
                        f for f in files
                        if f.lower().startswith(self.prefix)
                        and (
                            any(f.lower().endswith(ext) for ext in image_extensions)
                            or '.' not in f
                        )
                    ])
                    # Add full paths to matching files
                    for f in dir_files:
                        full_path = os.path.join(directory, f)
                        self.matching_files.append(full_path)
                except Exception as e:
                    print(f"Warning: Could not read directory {directory}: {e}")
            
            if not self.matching_files:
                print(f"No matching files found in {self.directory} or subdirectories")
                return False
            
            self.istart = 1
            self.iend = len(self.matching_files)
            self.numframes = self.iend - self.istart + 1
            img = io.imread(self.matching_files[0])
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
        dialog.title("Analysis Parameters")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        center_window(dialog)
        dialog.columnconfigure(0, weight=1)
        dialog.columnconfigure(1, weight=1)

        # Title label
        tk.Label(dialog, text="Configure Analysis Parameters:", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=20)

        # Define editable parameters
        keys = ['peak_det_abs_threshold', 'peak_det_threshold', 'Centroid_r_threshold', 'area_threshold']
        labels = ["Peak Detection Absolute Threshold", "Peak Detection Threshold", "Centroid Radius Threshold", "Area Threshold"]
        entries = {}

        for idx, label_text in enumerate(labels):
            row = idx + 1
            tk.Label(dialog, text=label_text, font=("Helvetica", 11)).grid(row=row, column=0, padx=15, pady=8, sticky="w")
            entry = tk.Entry(dialog, font=("Helvetica", 11), width=20)
            entry.insert(0, str(params[keys[idx]]))
            entry.grid(row=row, column=1, padx=15, pady=8, sticky="ew")
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
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.grid(row=len(keys)+1, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="OK", font=("Helvetica", 12), width=12, height=2, command=on_ok).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", font=("Helvetica", 12), width=12, height=2, command=on_cancel).pack(side="left", padx=10)

        dialog.wait_window(dialog)

    def cleanup_and_exit(self):
        """Properly close the application and exit."""
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            print(f"Error destroying root window: {e}")
        sys.exit(0)

    def safe_exit_with_error(self, error_message="Unknown error"):
        """
        Safely exit the application after an error.
        
        Args:
            error_message: Error message to display before exit
        """
        try:
            print(f"Exiting due to error: {error_message}")
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            print(f"Error during error exit: {e}")
        sys.exit(1)

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
