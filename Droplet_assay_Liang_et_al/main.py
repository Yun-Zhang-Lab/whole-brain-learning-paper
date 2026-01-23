"""
Application entry point for Droplet Assay Analyzer.

Initializes and runs the main GUI application.
"""

from app.analyzer import DropletAssayAnalyzer

def main():
    analyzer = DropletAssayAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()
