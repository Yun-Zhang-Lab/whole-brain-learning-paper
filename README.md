# Whole-Brain Learning Paper

This repository contains the code for the paper:

**"Context-Gated and Electrical Synapse-Mediated Brain-Wide Activity Reorganization Regulates Learning Behavior in *C. elegans*"**

## Overview

Code and analysis scripts accompanying our research on brain-wide activity reorganization and learning behavior in *C. elegans*. The repository includes:

1. **`DropletAssay_analysis_software/`** — MATLAB and Python versions of the behavior analysis code used to extract behavior data in the droplet assay (MIT License).
2. **`NeuralData_Analysis_pipeline/`** — Jupyter notebooks numbered in order of the paper's figures. Figure numbers are marked as subtitles within the notebooks.

---

## 1. System Requirements

### Software Dependencies

- **Python** ≥ 3.11, < 3.13 (tested on 3.12; constrained by CeDNe)
- **CeDNe** — install from [GitHub](https://github.com/sahilm89/CeDNe/blob/main/INSTALL.md) (required to load `.cedne` pickle files)
- All Python package dependencies are listed in [`requirements.txt`](requirements.txt)
- Additional per-notebook dependencies: PyTorch (`torch`), TensorLy, cvxpy (see [`NeuralData_Analysis_pipeline/README.md`](NeuralData_Analysis_pipeline/README.md) for details)

### Operating Systems

- **macOS** 13+ (tested on macOS 14 Sonoma, Apple Silicon (M1))
- **Linux** (tested on Ubuntu 22.04)
- **Windows** 10/11 (not tested, but expected to work)

### Hardware

- No non-standard hardware required.
- Minimum 8 GB RAM recommended

---

## 2. Installation Guide

### Instructions

```bash
# Clone the repository
git clone https://github.com/Yun-Zhang-Lab/whole-brain-learning-paper.git
cd whole-brain-learning-paper

# Create and activate a Python virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install all dependencies (includes CeDNe)
pip install -r requirements.txt

# Install the DropletAssay analysis software (optional, for behavior analysis)
cd DropletAssay_analysis_software
pip install -e .
cd ..
```

### Typical Install Time

~5–10 minutes on a standard desktop with a broadband connection (dominated by PyTorch download).

---

## 3. Demo

### Demo Data

A small demo dataset is included in this repository as compressed archives:

- **`sampled_imaging_part1.zip`** — sampled raw imaging CSVs, part 1 (input to notebook 00)
- **`sampled_imaging_part2.zip`** — sampled raw imaging CSVs, part 2 (input to notebook 00)
- **`sampled_behavior_data.zip`** — sampled eccentricity CSVs (input to notebook 06)

### Instructions to Run Demo

```bash
# 1. Decompress demo data in the repository root
unzip sampled_imaging_part1.zip
unzip sampled_imaging_part2.zip
unzip sampled_behavior_data.zip

# 2. Launch Jupyter
cd NeuralData_Analysis_pipeline
jupyter notebook
```

Then open and run the notebooks in order (00 → 08). Each notebook will read its inputs from the previous step's outputs.

### Expected Output

Each notebook produces:
- **Figures** matching those in the paper (heatmaps, SVD component plots, geometry visualizations, etc.) displayed inline.
- **Intermediate data files** (`.cedne` pickles, `.pickle` tensors) saved to `pickles/` and `processed/`.

See the [Notebooks table](NeuralData_Analysis_pipeline/README.md#notebooks) for which notebook produces which paper figure.

### Expected Run Time (Demo)

The full notebook pipeline runs in approximately **15–30 minutes** on a standard laptop (Apple M1/M2 or comparable x86 CPU, 16 GB RAM) using the demo dataset. Individual notebooks range from ~1–5 minutes each.

---

### Expected Results

The notebooks have been pre-run to produce expected graphs, wihch can be compared against.

---

## Repository Structure

```
whole-brain-learning-paper/
├── README.md                          ← this file
├── LICENSE.md
├── requirements.txt
├── sampled_imaging_part1.zip           ← demo neural imaging data (part 1)
├── sampled_imaging_part2.zip           ← demo neural imaging data (part 2)
├── sampled_behavior_data.zip           ← demo behavior data
├── DropletAssay_analysis_software/    ← behavior analysis package (Python + MATLAB)
│   ├── README.md
│   └── ...
├── NeuralData_Analysis_pipeline/      ← analysis notebooks (00–08)
│   ├── README.md
│   ├── pickles/                       ← .cedne files
│   ├── processed/                     ← intermediate outputs
│   └── ...
├── data/
    └── behavior_data/                 ← eccentricity CSVs
```

## License

Copyright © 2026 Yun Zhang Lab. All rights reserved. No reuse or distribution without written permission. License will be changed to MIT License upon the publication of the manuscript.

## Reproduction
To reproduce all results from the manuscript, the same code needs to run on the full dataset, which will be made open source after the manuscript has been published.

## Contact

For questions, please contact Yun Zhang Lab.