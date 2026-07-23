"""Run the ICS Risk Assessment Framework.

Usage:
    python main.py
    python -m backend
"""
import sys
import os

# Add the project root to Python path so the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from backend.cli import main as cli_main
    cli_main()

