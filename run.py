#!/usr/bin/env python3
"""
Quick run script for VoiceType.

Usage:
    python run.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from src.main import main
    main()
