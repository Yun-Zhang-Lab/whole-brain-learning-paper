"""
Setup configuration for Droplet Assay Analyzer.

Installs the package with a 'droplet-assay' command-line entry point.
"""

from setuptools import setup, find_packages
import os

# Read the long description from README if it exists
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="droplet-assay-analyzer",
    version="1.0.0",
    description="Automated image analysis and behavioral turn detection for droplet-based assays",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "scikit-image>=0.18.0",
        "opencv-python>=4.5.0",
        "matplotlib>=3.4.0",
        "Pillow>=8.0.0",
        "scipy>=1.7.0",
        "imageio>=2.9.0",
    ],
    entry_points={
        "console_scripts": [
            "droplet-assay=app.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
