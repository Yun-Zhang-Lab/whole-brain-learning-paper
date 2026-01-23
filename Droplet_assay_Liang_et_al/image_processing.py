"""
Image processing and morphological feature extraction module.

Processes image sequences to extract morphological measurements (area, centroid,
eccentricity) for each ROI across all frames. Uses background subtraction,
disk filtering, and connected component analysis.
"""

import os
import numpy as np
import concurrent.futures
from skimage import io
from skimage.morphology import disk, dilation
from scipy.ndimage import correlate
from skimage.measure import label, regionprops
from gui.progress import create_progress_bar
import cv2

def compute_minimum_image(directory, matching_files):
    """
    Compute minimum intensity projection across image sequence.
    
    Samples frames at regular intervals to reduce noise and suppress bright noise.
    
    Returns:
        imgmin: Minimum intensity image
        numframes: Total number of frames in sequence
    """
    first_image = io.imread(os.path.join(directory, matching_files[0]))
    imgmin = 255 * np.ones(first_image.shape, dtype=np.float32)
    numframes = len(matching_files)
    skip = max(1, numframes // 10)  # Sample every ~10% of frames
    for i in range(0, numframes, skip):
        image_name = matching_files[i]
        img = io.imread(os.path.join(directory, image_name)).astype(np.float32)
        imgmin = np.minimum(img, imgmin)
    return imgmin, numframes


def process_frame(frame_args):
    """
    Extract morphological features from a single image frame within each ROI.
    
    Performs background subtraction, disk-based filtering, adaptive thresholding,
    and connected component analysis to extract area, centroid, and eccentricity.
    
    Returns:
        index: Frame index
        frame_result: List of (area, centroid, eccentricity, ellipse_params) tuples per ROI
    """
    (index, image_name, directory, imgmin_dilate, roi_coords, ignore_worm,
     mask_multiplier, img_threshold, radius) = frame_args
     
    img_full = io.imread(os.path.join(directory, image_name)).astype(np.float32)
    # Background subtraction: subtract dilated minimum image
    img_diff = img_full - mask_multiplier * imgmin_dilate
    img_diff[img_diff < 0] = 0
    
    frame_result = []
    for roi, ignore in zip(roi_coords, ignore_worm):
        if ignore or roi is None:
            frame_result.append((np.nan, (np.nan, np.nan), np.nan, None))
            continue

        # Extract ROI from image
        (x1, y1), (x2, y2) = roi
        y1, y2 = max(0, y1), min(img_diff.shape[0], y2)
        x1, x2 = max(0, x1), min(img_diff.shape[1], x2)
        img_crop = img_diff[y1:y2, x1:x2]

        # Apply windowed disk filter for local feature detection
        masksize = min(80, y2 - y1, x2 - x1)
        hann_window = np.outer(np.hanning(masksize), np.hanning(masksize))
        tmp = np.zeros_like(img_crop)
        tmp[:masksize, :masksize] = hann_window
        mask2 = np.roll(np.roll(tmp, round(-masksize / 2), axis=0), round(-masksize / 2), axis=1)

        # Disk-based correlation filter
        disk_filter = disk(radius).astype(float)
        disk_filter /= disk_filter.sum()

        imgcrop1 = correlate(img_crop, disk_filter, mode='nearest')
        imgmax = np.max(imgcrop1)
        yi, xi = np.unravel_index(np.argmax(imgcrop1), imgcrop1.shape)

        # Apply adaptive windowing around peak
        imgcrop1f = imgcrop1 * np.roll(np.roll(mask2, int(yi), axis=0), int(xi), axis=1)
        imgcrop1f_bw = (imgcrop1f > imgmax * img_threshold).astype(np.uint8)
     
        # Extract connected component containing peak
        labeled_img = label(imgcrop1f_bw, connectivity=2)
        if labeled_img[yi, xi] != 0:
            imgcrop1f_bws = (labeled_img == labeled_img[yi, xi])
        else:
            imgcrop1f_bws = np.zeros_like(imgcrop1f_bw)
        
        # Extract morphological properties
        props = regionprops(imgcrop1f_bws.astype(int))
        if props:
            prop = props[0]
            area = prop.area
            centroid = prop.centroid
            eccentricity = prop.eccentricity
            # Store ellipse parameters for shape tracking
            if prop.major_axis_length > 0 and prop.minor_axis_length > 0:
                ellipse_params = (
                    (centroid[1], centroid[0]),
                    (prop.major_axis_length, prop.minor_axis_length),
                    -np.degrees(prop.orientation)
                )
            else:
                ellipse_params = None
            frame_result.append((area, centroid, eccentricity, ellipse_params))
        else:
            frame_result.append((np.nan, (np.nan, np.nan), np.nan, None))
            
    return index, frame_result



def process_images(analyzer, directory, matching_files, roi_coords, ignore_worm,
                   mask_multiplier=1.1, img_threshold=0.1, radius=5):
    """
    Extract morphological features from all image frames in all ROIs.
    
    Processes image sequence in parallel, extracting area, centroid, and eccentricity
    for each ROI per frame. Automatically detects and flags inactive worms.
    
    Args:
        analyzer: DropletAssayAnalyzer instance (for stop_processing flag)
        directory: Path to image directory
        matching_files: List of image filenames
        roi_coords: ROI bounding box coordinates
        ignore_worm: Flags indicating which ROIs to skip
        mask_multiplier: Background subtraction scaling factor
        img_threshold: Relative threshold for connected component extraction
        radius: Disk filter radius for feature detection
    
    Returns:
        bw_Area: Area measurements (num_roi × num_frames)
        bw_Centroid: Centroid coordinates (num_roi × num_frames × 2)
        bw_Eccentricity: Eccentricity measurements (num_roi × num_frames)
    """
    progress_bar, progress_window = create_progress_bar(analyzer, len(matching_files))
    progress_window.update_idletasks()
    progress_window.after(100, lambda: None)
    progress_window.update()

    # Compute minimum image for background subtraction
    imgmin, numframes = compute_minimum_image(directory, matching_files)
    
    # Prepare background mask via dilation
    imgmin_thresh = 10
    imgmin_bw = imgmin > imgmin_thresh
    se = disk(3)
    imgmin_dilate = dilation(imgmin, se)
    
    numroi = len(roi_coords)
    # Initialize output arrays
    bw_Area = np.zeros((numroi, numframes))
    bw_Centroid = np.zeros((numroi, numframes, 2))
    bw_Eccentricity = np.zeros((numroi, numframes))
    # Track major/minor axes for shape analysis (stored as analyzer attributes)
    bw_MajorAxis = np.full((numroi, numframes), np.nan)
    bw_MinorAxis = np.full((numroi, numframes), np.nan)
    
    # Prepare frame processing tasks
    tasks = []
    for j, image_name in enumerate(matching_files):
        tasks.append((j, image_name, directory, imgmin_dilate, roi_coords, ignore_worm,
                      mask_multiplier, img_threshold, radius))
    
    # Process frames in parallel using process pool
    results = [None] * numframes
    try:
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = {executor.submit(process_frame, task): task[0] for task in tasks}
            for future in concurrent.futures.as_completed(futures):
                j = futures[future]
                # Check for user-requested stop
                if analyzer.stop_processing:
                    print("Processing stopped by user via progress window.")
                    executor.shutdown(wait=False)
                    progress_window.destroy()
                    return None, None, None

                try:
                    index, frame_result = future.result()
                except Exception as exc:
                    print(f"Frame {j} generated an exception: {exc}")
                    frame_result = [(np.nan, (np.nan, np.nan), np.nan, None)] * numroi
                results[j] = frame_result
                progress_bar["value"] += 1
                progress_window.update()

    except Exception as e:
        print(f"An error occurred during parallel processing: {e}")
        progress_window.destroy()
        return None, None, None

    # Assemble results into output arrays
    for j in range(numframes):
        frame_result = results[j]
        if frame_result is None:
            # Fill with NaN if frame did not complete
            for k in range(numroi):
                bw_Area[k, j] = np.nan
                bw_Centroid[k, j, :] = np.nan
                bw_Eccentricity[k, j] = np.nan
        else:
            for k, (area, centroid, ecc, ellipse_params) in enumerate(frame_result):
                bw_Area[k, j] = area
                bw_Centroid[k, j, :] = centroid
                bw_Eccentricity[k, j] = ecc
                # Extract major/minor axis lengths from ellipse parameters
                if ellipse_params is not None:
                    (_, _), (major, minor), _ = ellipse_params
                    bw_MajorAxis[k, j] = major
                    bw_MinorAxis[k, j] = minor
                else:
                    bw_MajorAxis[k, j] = np.nan
                    bw_MinorAxis[k, j] = np.nan

    # Auto-detect inactive worms based on eccentricity stability
    # A worm is inactive if eccentricity remains nearly constant for 100+ frames
    if isinstance(ignore_worm, list) and all(flag is False for flag in ignore_worm):
        computed_ignore_worm = []
        ecc_threshold = 0.015  # Threshold for "little" eccentricity change
        for k in range(numroi):
            ecc_vals = bw_Eccentricity[k, :]
            # Mark as ignored if all measurements are NaN
            if np.all(np.isnan(ecc_vals)):
                computed_ignore_worm.append(True)
                continue
            
            # Detect stretches of stability (low eccentricity changes)
            differences = np.abs(np.diff(ecc_vals))
            not_changing = differences < ecc_threshold

            # Check for 100+ consecutive frames with little change
            consecutive = 0
            ignore_flag = False
            for change in not_changing:
                if change:
                    consecutive += 1
                    if consecutive >= 100:
                        ignore_flag = True
                        break
                else:
                    consecutive = 0
            computed_ignore_worm.append(ignore_flag)
        ignore_worm = computed_ignore_worm

        # Set inactive worms to NaN across all measurements
        for k in range(numroi):
            if ignore_worm[k]:
                bw_Area[k, :] = np.nan
                bw_Centroid[k, :, :] = np.nan
                bw_Eccentricity[k, :] = np.nan
                bw_MajorAxis[k, :] = np.nan
                bw_MinorAxis[k, :] = np.nan
                print(f"Worm {k+1} has been marked as ignored due to inactivity.")

    print("Image processing complete.")
    if progress_window:
        progress_window.destroy()

    # Expose axis measurements via analyzer attributes without changing API
    try:
        setattr(analyzer, 'bw_MajorAxis', bw_MajorAxis)
        setattr(analyzer, 'bw_MinorAxis', bw_MinorAxis)
    except Exception:
        pass
    
    return bw_Area, bw_Centroid, bw_Eccentricity



