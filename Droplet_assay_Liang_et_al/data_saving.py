"""
Data persistence and result file generation module.

Manages output file generation, formatting, and saving of analysis results
including measurements, turn counts, choice indices, and workspace variables.
"""

import os
import numpy as np
import pandas as pd
import pprint
from pathlib import Path
from typing import Dict

def save_workspace_as_py(file_path, workspace_data):
    """Save analysis workspace variables to Python file for reproducibility."""
    with open(file_path, 'w') as f:
        f.write("# Auto-generated workspace data\n")
        f.write("workspace_data = ")
        f.write(pprint.pformat(workspace_data, indent=4))


def get_default_save_paths(directory: str) -> Dict[str, str]:
    """
    Generate standardized output file paths for analysis results.

    Constructs file paths using parent and current directory names to create
    unique, descriptive filenames. Uses pathlib for cross-platform compatibility.

    Args:
        directory: Base analysis directory

    Returns:
        Dictionary mapping output type names to full file paths
    """
    p = Path(directory)
    current = p.name or p.resolve().name               # Current (last) folder name
    parent = (p.parent.name or p.resolve().parent.name # Parent folder name
              or "root")

    prefix = f"{parent}_{current}"

    def make(name_suffix, prefix, p):
        return str(p / f"{prefix}_{name_suffix}")
    
    paths = {
        'ecc_data':               make("eccentricity_data.csv", prefix, p),
        'turn_times':             make("turn_data.xlsx", prefix, p),
        'turn_rates':             make("turn_rates_choice_indices.txt", prefix, p),
        'turn_all':               make("turndata_all.xlsx", prefix, p),
        'choice_index_individual':make("choice_index_individual.xlsx", prefix, p),
        'workspace_data':         make("workspace_data.py", prefix, p),
        # Additional optional outputs (used if available)
        'major_axes':             make("major_axes.csv", prefix, p),
        'minor_axes':             make("minor_axes.csv", prefix, p),
    }

    return paths


def save_analysis_data(directory, bw_Eccentricity_filtered, num_turns_all, turn_rate_grouped,
                       choice_index_grouped, choice_index_individual, turndata_valid, data_invalid,
                       file_paths, **kwargs):
    """
    Save all analysis results to disk in standard formats.
    
    Generates CSV, XLSX, and text files containing measurements, turn statistics,
    choice indices, and workspace variables for downstream analysis and archival.

    Args:
        directory: Base output directory
        bw_Eccentricity_filtered: Filtered eccentricity measurements (num_roi × num_frames)
        num_turns_all: Turn counts per ROI and stimulus condition
        turn_rate_grouped: Turn rates for grouped ROIs
        choice_index_grouped: Grouped preference indices
        choice_index_individual: Per-ROI preference indices
        turndata_valid: Boolean array of valid turn events
        data_invalid: Boolean array of invalid/missing data points
        file_paths: Dictionary of output file paths
        **kwargs: Optional parameters (bw_MajorAxis, bw_MinorAxis, analyzer instance)
    """
    numroi, numframes = bw_Eccentricity_filtered.shape

    # Save filtered eccentricity measurements per ROI
    ecc_data = pd.DataFrame({'Frame': np.arange(numframes)})
    for k in range(numroi):
        ecc_data[f'Worm_{k+1}'] = bw_Eccentricity_filtered[k]
    ecc_data.to_csv(file_paths['ecc_data'], index=False)
    print(f"Smoothed eccentricity data saved to {file_paths['ecc_data']}")

    # Save frame numbers where turns occurred (1-indexed for compatibility)
    max_num_turns = int(np.max(np.sum(num_turns_all, axis=2)))
    tmp = np.full((max_num_turns, numroi), np.nan)
    for k in range(numroi):
        turns = np.where(turndata_valid[k, :])[0] + 1  # Add 1 for 1-based indexing
        tmp[:len(turns), k] = turns
    turns_data = pd.DataFrame(tmp, columns=[f'Worm_{k+1}' for k in range(numroi)])
    turns_data.to_excel(file_paths['turn_times'], index=False)
    print(f"Turn times saved to {file_paths['turn_times']}")

    # Save turn rates and grouped choice indices
    turn_rates_data = np.vstack([
        10 * turn_rate_grouped[0, :, 0],  # Stimulus 1 rate (turns/10 frames)
        10 * turn_rate_grouped[0, :, 1],  # Stimulus 2 rate (turns/10 frames)
        choice_index_grouped[0, :]         # Choice index (preference metric)
    ])
    np.savetxt(file_paths['turn_rates'], turn_rates_data, delimiter=' ', fmt='%.4f', newline='\n')
    print(f"Turn rates and choice indices saved to {file_paths['turn_rates']}")

    # Calculate turn counts in fixed intervals across sequence
    interval_size = 10  # Frames per interval
    num_intervals = numframes // interval_size
    turn_all = np.zeros((num_intervals, numroi))
    for i in range(num_intervals):
        start_idx = i * interval_size
        end_idx = min(start_idx + interval_size, numframes)
        turn_all[i, :] = np.sum(turndata_valid[:, start_idx:end_idx], axis=1)
    turn_all_df = pd.DataFrame(turn_all, columns=[f'Worm_{k+1}' for k in range(numroi)])
    turn_all_df.to_excel(file_paths['turn_all'], index=False)
    print(f"Turn counts over intervals saved to {file_paths['turn_all']}")

    # Save individual choice index per ROI
    choice_index_individual_df = pd.DataFrame(choice_index_individual, columns=['Choice Index Individual'])
    choice_index_individual_df.to_excel(file_paths['choice_index_individual'], index=False)
    print(f"Choice index individual saved to {file_paths['choice_index_individual']}")

    # Save major/minor axis measurements if available
    bw_MajorAxis = kwargs.get('bw_MajorAxis')
    bw_MinorAxis = kwargs.get('bw_MinorAxis')

    # Attempt to retrieve from analyzer if not provided directly
    analyzer = kwargs.get('analyzer')
    if bw_MajorAxis is None and analyzer is not None:
        bw_MajorAxis = getattr(analyzer, 'bw_MajorAxis', None)
    if bw_MinorAxis is None and analyzer is not None:
        bw_MinorAxis = getattr(analyzer, 'bw_MinorAxis', None)

    def _save_axis_csv(arr, path):
        """Helper to save axis measurements to CSV."""
        if arr is None:
            return
        # arr shape: (numroi, numframes)
        df = pd.DataFrame({'Frame': np.arange(arr.shape[1])})
        for k in range(arr.shape[0]):
            df[f'Worm_{k+1}'] = arr[k]
        df.to_csv(path, index=False)

    if bw_MajorAxis is not None and 'major_axes' in file_paths:
        _save_axis_csv(bw_MajorAxis, file_paths['major_axes'])
        print(f"Major axes saved to {file_paths['major_axes']}")
    if bw_MinorAxis is not None and 'minor_axes' in file_paths:
        _save_axis_csv(bw_MinorAxis, file_paths['minor_axes'])
        print(f"Minor axes saved to {file_paths['minor_axes']}")

    # Save analysis workspace variables as Python code for reproducibility
    workspace_data = {
        'num_turns_all': num_turns_all,
        'turn_rate_grouped': turn_rate_grouped,
        'choice_index_grouped': choice_index_grouped,
        'choice_index_individual': choice_index_individual,
        'turndata_valid': turndata_valid,
        'data_invalid': data_invalid,
        'turn_all': turn_all,
    }
    file_path = file_paths['workspace_data']
    save_workspace_as_py(file_path, workspace_data)
    print(f"Workspace variables saved to {file_path}")