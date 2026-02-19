"""
Command-line interface and application entry point.

Provides the 'droplet-assay' command for launching the GUI application.
"""

import sys
import os
from pathlib import Path

# Add the package root to sys.path to enable root-level imports
package_root = str(Path(__file__).parent.parent)
if package_root not in sys.path:
    sys.path.insert(0, package_root)

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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
