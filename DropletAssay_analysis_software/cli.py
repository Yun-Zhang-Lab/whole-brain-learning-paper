"""
Command-line interface and application entry point.

Provides the 'droplet-assay' command for launching the GUI application.
"""

import sys
from app.analyzer import DropletAssayAnalyzer


def main():
    """
    Main entry point for the command-line interface.
    
    Initializes and runs the Droplet Assay Analyzer GUI application.
    """
    try:
        analyzer = DropletAssayAnalyzer()
        analyzer.run()
    except Exception as e:
        print(f"Error launching Droplet Assay Analyzer: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
