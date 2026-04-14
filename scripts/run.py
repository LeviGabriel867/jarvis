#!/usr/bin/env python3
"""
JARVIS v3.0 - Entry point com auto-restart.
Se o processo morrer (crash, segfault, etc.), reinicia automaticamente.

Usage:
  python run.py             -> normal operation
  python run.py --list      -> list all available commands
"""

import sys
import time
from pathlib import Path

# Adicionar src ao path para poder importar o pacote jarvis
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from jarvis.app import main


def run_with_restart():
    """Executa o main() e reinicia automaticamente em caso de crash."""
    while True:
        try:
            main()
            break  # saiu normalmente (ex: Ctrl+C, comando "desligar")
        except SystemExit:
            break  # sys.exit() intencional
        except Exception as e:
            print(f"\n  [LAUNCHER] Jarvis crashou: {e}")
            print("  [LAUNCHER] Reiniciando em 3 segundos...\n")
            time.sleep(3)


if __name__ == "__main__":
    if "--listar" in sys.argv or "--list" in sys.argv:
        main()
    else:
        run_with_restart()
