"""
Droplet Assay Analyzer Application Package.

Contains the main GUI analyzer, ROI selection, file selection, and related utilities.
"""

__version__ = "1.0.0"

# Lazy import to avoid import issues when sys.path hasn't been set up yet
def __getattr__(name):
    if name == "DropletAssayAnalyzer":
        from app.analyzer import DropletAssayAnalyzer
        return DropletAssayAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["DropletAssayAnalyzer"]
