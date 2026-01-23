"""
Turn analysis and behavioral choice index calculation module.

Computes turn counts, turn rates, and choice indices from eccentricity and
centroid signal data. Supports both individual and grouped analyses with
visualization and data persistence.
"""

import numpy as np
import matplotlib.pyplot as plt
from gui.grouping import GroupingApp
from data_saving import save_analysis_data, get_default_save_paths
import os

def analyze_turns(valid_turns, invalid_data, num_frames, roi_coords, params, root, directory, bw_Eccentricity_filtered, show_plots=True, batch_mode=False):
    """
    Analyze turn data to calculate turn counts, turn rates, and choice indices.

    Args:
        valid_turns (dict): Dictionary with keys 'ROI_0', 'ROI_1', ... indicating valid turns.
        invalid_data (dict): Dictionary with keys 'ROI_0', 'ROI_1', ... indicating invalid data.
        num_frames (int): Total number of frames.
        roi_coords (list): List of ROI coordinate tuples.
        params (dict): Parameter dictionary.
        root (tk.Tk): Tk root widget (for GUI dialogs).
        directory (str): Base directory for saving.
        bw_Eccentricity_filtered (np.ndarray): Filtered eccentricity data.
    
    Returns:
        Tuple: (num_turns_all, turn_rate_grouped, choice_index_grouped, choice_index_individual)
    """
    num_roi = len(roi_coords)
    halfperiod = 300

    # Generate frame masks.
    frames = np.arange(num_frames)
    frames1 = ((frames // halfperiod) % 2) == 0  # Stimulus 1
    frames2 = ~frames1                          # Stimulus 2

    num_datasets = 1
    num_turns_all = np.zeros((num_datasets, num_roi, 2))
    # Convert dictionaries to arrays.
    turndata_valid_arr = np.array([valid_turns[f'ROI_{k}'] for k in range(num_roi)])
    data_invalid_arr   = np.array([invalid_data[f'ROI_{k}'] for k in range(num_roi)])

    # Calculate turn counts for each ROI.
    for dataset in range(num_datasets):
        for roi in range(num_roi):
            num_turns_all[dataset, roi, 0] = np.sum(turndata_valid_arr[roi] & frames1)
            num_turns_all[dataset, roi, 1] = np.sum(turndata_valid_arr[roi] & frames2)

    
    # Grouping logic.
    if batch_mode == False:
        # Ask user for grouping selection.
        grouping_app = GroupingApp(root)
        grouping = grouping_app.get_grouping(num_roi, batch_mode=False)
        if grouping is None:
            print("Grouping selection canceled or invalid.")
            return None, None, None, None
        num_groups, groups = grouping
    else:
        grouping_app = GroupingApp(root)
        num_groups, groups = grouping_app.get_grouping(num_roi, batch_mode=True)

    turn_rate_grouped = np.zeros((num_datasets, num_groups, 2))
    choice_index_grouped = np.zeros((num_datasets, num_groups))

    for dataset in range(num_datasets):
        for group_idx, group in enumerate(groups):
            group = group[group < num_roi]  # ensure valid indices
            if len(group) == 0:
                turn_rate_grouped[dataset, group_idx, :] = np.nan
                choice_index_grouped[dataset, group_idx] = np.nan
                continue

            num_turns_grouped = np.sum(num_turns_all[dataset, group, :], axis=0)
            valid_frames1 = (~data_invalid_arr[group, :]) & frames1
            valid_frames2 = (~data_invalid_arr[group, :]) & frames2
            valid_count1 = np.sum(valid_frames1)
            valid_count2 = np.sum(valid_frames2)

            turn_rate_grouped[dataset, group_idx, 0] = num_turns_grouped[0] / valid_count1 if valid_count1 > 0 else np.nan
            turn_rate_grouped[dataset, group_idx, 1] = num_turns_grouped[1] / valid_count2 if valid_count2 > 0 else np.nan

            sum_rates = turn_rate_grouped[dataset, group_idx, 0] + turn_rate_grouped[dataset, group_idx, 1]
            if sum_rates > 0:
                choice_index_grouped[dataset, group_idx] = (turn_rate_grouped[dataset, group_idx, 0] - turn_rate_grouped[dataset, group_idx, 1]) / sum_rates
            else:
                choice_index_grouped[dataset, group_idx] = np.nan

    # Calculate individual choice indices.
    with np.errstate(divide='ignore', invalid='ignore'):
        turns_01 = num_turns_all[0, :, 0]
        turns_02 = num_turns_all[0, :, 1]
        choice_index_individual = (turns_01 - turns_02) / (turns_01 + turns_02)
        choice_index_individual = np.where((turns_01 + turns_02) > 0, choice_index_individual, np.nan)
    
    if show_plots:
        # Plotting the results.
        fig, axs = plt.subplots(3, 1, figsize=(6,5), tight_layout=True)
        total_turns = np.sum(num_turns_all[0, :, :], axis=1)
        axs[0].bar(range(1, num_roi+1), total_turns, edgecolor='black', color='darkgray')
        axs[0].set_xlabel("Worm")
        axs[0].set_ylabel("Total Number of Turns")
        axs[0].set_title("Total Number of Turns per Worm")

        axs[1].bar(range(1, num_groups+1), choice_index_grouped[0], edgecolor='black', color='plum')
        axs[1].set_xlabel("Group")
        axs[1].set_ylabel("Choice Index")
        axs[1].set_title("Grouped Choice Index")
        axs[1].set_xticks(range(1, num_groups+1))

        axs[2].bar(range(1, num_roi+1), choice_index_individual, color='darkorange', edgecolor='black')
        axs[2].set_xlabel("Worm")
        axs[2].set_ylabel("Choice Index (Individual)")
        axs[2].set_title("Individual Choice Index per Worm")
        axs[2].set_xticks(range(1, num_roi+1))
        plt.show()

    # Save analysis data
    file_paths = get_default_save_paths(directory)
    # Pass analyzer instance so saver can access optional arrays without changing APIs
    from app.analyzer import DropletAssayAnalyzer
    analyzer_obj = getattr(root, 'analyzer', None)
    save_analysis_data(directory, bw_Eccentricity_filtered, num_turns_all, turn_rate_grouped,
                       choice_index_grouped, choice_index_individual, turndata_valid_arr, data_invalid_arr,
                       file_paths, analyzer=analyzer_obj)

    return num_turns_all, turn_rate_grouped, choice_index_grouped, choice_index_individual
