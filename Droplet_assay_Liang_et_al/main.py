"""
Application entry point for Droplet Assay Analyzer.

Initializes and runs the main GUI application with comprehensive error handling.
"""

import sys
import traceback
from app.analyzer import DropletAssayAnalyzer

def main():
    """
    Main entry point.
    
    Ensures the application exits safely.
    """
    try:
        analyzer = DropletAssayAnalyzer()
        analyzer.run()
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        # Ensure complete exit with error code
        sys.exit(1)

if __name__ == "__main__":
    main()
