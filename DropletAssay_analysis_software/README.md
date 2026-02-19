# Droplet Assay Analyzer
Developed by Panagiotis E. Eleftheriadis  

Automated image analysis and behavioral turn detection for droplet-based assays. This Python package provides a complete workflow for analyzing worm swimming behavior in droplets with automated ROI detection, morphological feature extraction, and turn detection.

## Features

- **Automated ROI Detection**: Circular ROI detection using Hough circle transforms
- **Parallel Image Processing**: Frame-by-frame morphological feature extraction (area, centroid, eccentricity)
- **Signal Processing**: Peak detection and turn validation based on morphological thresholds
- **Behavioral Analysis**: Turn detection with stimulus-response mapping and choice index calculation
- **GUI Interface**: Interactive matplotlib-based ROI selection and visualization
- **Multi-format Export**: CSV, Excel, and Python serialization of results
- **Batch Processing**: Process multiple image datasets sequentially

## Installation
First clone the repository, then:

Install the package in editable mode

\\\Bash
pip install -e .
\\\


### Launch the Application

\\\Bash
droplet-assay
\\\

### Using Example Data

Example image data is included in the \example_data\ folder (unzip to acess the 7200 JPEG images) to help you get started:

1. Launch the application: \droplet-assay\
2. When prompted to select images, navigate to and select the \example_data\ folder, after unzipping it
3. Select the first image from the sequence. The application will automatically load all other images.
4. Follow the GUI prompts to:
   - Define regions of interest (ROIs) - either draw circles manually or use auto-detection
   - Configure analysis parameters (filter sizes, thresholds)
   - Run the analysis on all images
5. View results and export to CSV/Excel


## Requirements

- Python 3.8 or higher
- Dependencies: numpy, pandas, scikit-image, opencv-python, matplotlib, Pillow, scipy, imageio

## Module Overview

- **app/analyzer.py**: Main application controller and GUI orchestration
- **app/file_selection.py**: File dialog and frame range selection
- **app/roi_selection.py**: Manual and automatic ROI detection
- **gui/**: GUI components (dialogs, progress bars, ROI visualization)
- **image_processing.py**: Parallel morphological feature extraction
- **signal_processing.py**: Peak detection and turn validation
- **analysis.py**: Behavioral analysis and choice index calculation
- **auto_roi_detection.py**: Hough circle-based automatic ROI detection
- **data_saving.py**: Multi-format result export

## Input/Output

**Input formats:**
- TIFF stacks (.tif, .tiff)
- Image sequences (.png, .jpg, .tif)

**Output formats:**
- CSV: Eccentricity measurements
- Excel: Turn times, turn counts, choice indices
- TXT: Turn rates
- Python: Complete workspace serialization

## Configuration Parameters

- **Eccentricity filter size**: Smoothing window for eccentricity signal
- **Area filter size**: Smoothing window for area signal
- **Centroid filter size**: Smoothing window for centroid radius
- **Peak detection threshold**: Relative prominence for peak detection
- **Peak absolute threshold**: Absolute eccentricity threshold for turns
- **Centroid radius threshold**: Maximum normalized centroid displacement (0.0-1.0 relative to droplet)
- **Area threshold**: Minimum area fraction relative to median

## Credits
Inspired by Chris Fang-Yen prototype Matlab alogirthms

## License

MIT License - see LICENSE file for details.
