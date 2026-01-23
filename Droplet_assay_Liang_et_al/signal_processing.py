"""
Signal processing and turn detection module.

Applies filtering, peak detection, and validity checks to morphological measurements
to identify behavioral turns. Computes normalized centroid radius and detects peaks
in eccentricity signals.
"""

# signal_processing.py

import numpy as np

class SignalProcessor:
    def __init__(self, bw_Eccentricity, bw_Centroid, bw_Area, roi_coords):
        """
        Initialize the signal processor with the raw signals and ROI coordinates.
        """
        self.bw_Eccentricity = bw_Eccentricity  # 2D array [numroi, numframes]
        self.bw_Centroid = bw_Centroid          # 3D array [numroi, numframes, 2]
        self.bw_Area = bw_Area                  # 2D array [numroi, numframes]
        self.roi_coords = roi_coords            # List of ROI coordinates for each ROI

    def detect_peaks(self, v, delta):
        """
        Detect peaks and troughs in a signal.
        v: Array of values.
        delta: Minimum difference required to consider a peak/trough significant.
        Returns:
            maxtab: List of tuples (index, value) of detected maxima.
            mintab: List of tuples (index, value) of detected minima.
        """
        maxtab, mintab = [], []
        mn, mx = np.inf, -np.inf
        mnpos, mxpos = None, None
        look_for_max = True

        for i, this in enumerate(v):
            if this > mx:
                mx = this
                mxpos = i
            if this < mn:
                mn = this
                mnpos = i

            if look_for_max:
                if this < mx - delta:
                    maxtab.append((mxpos, mx))
                    mn = this
                    mnpos = i
                    look_for_max = False
            else:
                if this > mn + delta:
                    mintab.append((mnpos, mn))
                    mx = this
                    mxpos = i
                    look_for_max = True

        return maxtab, mintab

    def moving_average(self, data, window_size):
        """
        Compute the moving average of the data using a sliding window.
        Adjusts the window boundaries at the edges.
        """
        if window_size < 1:
            raise ValueError("window_size must be a positive integer.")
        n = len(data)
        smoothed = np.zeros(n)
        w = window_size

        for i in range(n):
            half_window = (w - 1) // 2
            left = i - half_window
            right = i + half_window + 1
            if w % 2 == 0:
                right += 1
            start = max(0, left)
            end = min(n, right)
            smoothed[i] = np.mean(data[start:end])
        return smoothed

    def process_signals(self, params):
        """
        Process signals for multiple ROIs to detect valid turns based on eccentricity, area, and centroid radius.
        
        Peak detection identifies turning events via minima in smoothed eccentricity. Invalid data points
        are flagged when centroid radius exceeds threshold OR area falls below median threshold, then
        excluded from the valid turn set.
        
        Args:
            params (dict): Dictionary of parameters including:
                - Eccentricity_filsize: window size for eccentricity smoothing
                - Area_filsize: window size for area smoothing
                - Centroid_filsize: window size for centroid radius smoothing
                - peak_det_abs_threshold: absolute eccentricity value threshold for turn detection
                - peak_det_threshold: relative peak prominence threshold
                - Centroid_r_threshold: maximum normalized centroid radius (0.0-1.0 relative to droplet)
                - area_threshold: minimum area fraction (relative to median)
            
        Returns:
            valid_turns (dict): Boolean arrays per ROI keyed as 'ROI_0', 'ROI_1', etc.
            invalid_data (dict): Invalid data point flags per ROI (spatial/amplitude violations)
            bw_Eccentricity_filtered (ndarray): Smoothed eccentricity signals
            bw_Area_filtered (ndarray): Smoothed area signals
            bw_Centroid_r_filtered (ndarray): Normalized centroid radius signals
            droplet_radius (ndarray): Computed radius per ROI for normalization
        """
        
        # Extract parameters with sensible defaults
        Eccentricity_filsize = params.get('Eccentricity_filsize', 3)
        Area_filsize = params.get('Area_filsize', 10)
        Centroid_filsize = params.get('Centroid_filsize', 10)
        peak_det_abs_threshold = params.get('peak_det_abs_threshold', 0.85)
        peak_det_threshold = params.get('peak_det_threshold', 0.15)
        Centroid_r_threshold = params.get('Centroid_r_threshold', 0.7)
        area_threshold = params.get('area_threshold', 0.7)

        numroi, numframes = self.bw_Eccentricity.shape

        # Initialize storage for filtered signals and detection results
        bw_Centroid_r_filtered = np.zeros((numroi, numframes))
        bw_Eccentricity_filtered = np.zeros((numroi, numframes))
        bw_Area_filtered = np.zeros((numroi, numframes))
        droplet_radius = np.zeros(numroi)

        # Initialize binary flags for turn detection and validity
        turndata = np.zeros((numroi, numframes), dtype=bool)
        data_invalid = np.zeros((numroi, numframes), dtype=bool)
        turndata_valid = np.zeros((numroi, numframes), dtype=bool)

        # Process each ROI independently
        for kk in range(numroi):
            ecc = self.bw_Eccentricity[kk]
            centroid = self.bw_Centroid[kk]
            area = self.bw_Area[kk]

            # Skip ROIs with no data
            if np.all(np.isnan(ecc)) and np.all(np.isnan(centroid)) and np.all(np.isnan(area)):
                continue

            # Smooth morphological signals via moving average
            ecc_smooth = self.moving_average(ecc, Eccentricity_filsize)
            area_smooth = self.moving_average(area, Area_filsize)

            # Compute normalized centroid radius: distance from ROI center divided by droplet radius
            (x1, y1), (x2, y2) = self.roi_coords[kk]
            rect_width = x2 - x1
            rect_height = y2 - y1
            droplet_radius[kk] = (rect_width + rect_height) / 4
            centroid_r = np.sqrt((centroid[:, 0] - rect_width/2)**2 + (centroid[:, 1] - rect_height/2)**2) / droplet_radius[kk]
            centroid_smooth = self.moving_average(centroid_r, Centroid_filsize)

            # Store filtered signals
            bw_Centroid_r_filtered[kk, :] = centroid_smooth
            bw_Eccentricity_filtered[kk, :] = ecc_smooth
            bw_Area_filtered[kk, :] = area_smooth

            # Detect peaks (troughs) in eccentricity signal: turns correspond to local minima
            maxtab, mintab = self.detect_peaks(ecc_smooth, peak_det_threshold)
            peaks = np.array([idx for idx, val in mintab if val < peak_det_abs_threshold], dtype=int)
            turndata[kk, peaks] = True

            # Flag invalid data: centroid displacement OR insufficient area (2-stage validation)
            invalid_centroid_indices = np.where(centroid_smooth > Centroid_r_threshold)[0]
            invalid_area_indices = np.where(area_smooth < area_threshold * np.nanmedian(area))[0]
            data_invalid[kk, invalid_centroid_indices] = True
            data_invalid[kk, invalid_area_indices] = True
            
            # Valid turns: detected peaks that pass both spatial and amplitude validity checks
            turndata_valid[kk, :] = turndata[kk, :] & ~data_invalid[kk, :]

        # Return results as dictionaries keyed by ROI name
        valid_turns = {f'ROI_{kk}': turndata_valid[kk] for kk in range(numroi)}
        invalid_data = {f'ROI_{kk}': data_invalid[kk] for kk in range(numroi)}

        # Store filtered signals for potential later retrieval
        self.bw_Eccentricity_filtered = bw_Eccentricity_filtered
        self.bw_Area_filtered = bw_Area_filtered
        self.bw_Centroid_r_filtered = bw_Centroid_r_filtered

        return valid_turns, invalid_data, bw_Eccentricity_filtered, bw_Area_filtered, bw_Centroid_r_filtered, droplet_radius

def process_signals_and_analyze(bw_Eccentricity, bw_Centroid, bw_Area, roi_coords, params, stop_processing, analyze_turns_callback, get_parameters_callback):
    """
    Standalone helper function for parameter adjustment, signal processing, and turn analysis.
    
    Provides a functional interface to SignalProcessor for workflows requiring interactive
    parameter tuning and callback-based analysis.
    
    Args:
        bw_Eccentricity, bw_Centroid, bw_Area: Signal arrays from image processing
        roi_coords: List of ROI bounding boxes
        params: Parameter dictionary for signal processing
        stop_processing: Flag to halt processing if True
        analyze_turns_callback: Function to analyze turns given (valid_turns, invalid_data)
        get_parameters_callback: Function to obtain/adjust parameters from user
    
    Returns:
        Tuple of (valid_turns, invalid_data) dictionaries or (None, None) if stopped
    """
    # Allow user to adjust parameters using provided callback
    get_parameters_callback(params)
    if stop_processing:
        print("Processing stopped.")
        return None, None

    # Create a SignalProcessor instance and process signals
    processor = SignalProcessor(bw_Eccentricity, bw_Centroid, bw_Area, roi_coords)
    valid_turns, invalid_data = processor.process_signals(params)

    # Invoke analysis callback (e.g., analyze_turns) for downstream processing
    analyze_turns_callback(valid_turns, invalid_data)
    return valid_turns, invalid_data
