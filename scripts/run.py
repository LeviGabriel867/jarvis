#!/usr/bin/env python3
"""
JARVIS v3.0 - Entry point
Local voice assistant for Windows.

Usage:
  python run.py             -> normal operation
  python run.py --list      -> list all available commands
"""

import sys
from pathlib import Path

# Adicionar src ao path para poder importar o pacote jarvis
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from jarvis.app import main

if __name__ == "__main__":
    main()
