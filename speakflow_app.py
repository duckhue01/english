#!/usr/bin/env python3
"""
SpeakFlow Launcher Script
Allows running directly with `python3 speakflow_app.py` or `./speakflow_app.py`
"""

import sys
import os

# Ensure the package directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speakflow.cli import main

if __name__ == "__main__":
    main()
