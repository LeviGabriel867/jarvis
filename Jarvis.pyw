"""
JARVIS - Assistente por Comando de Voz
Clique duplo neste arquivo para iniciar o Jarvis sem janela de console.
"""

import sys
from pathlib import Path

# Adicionar src ao path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import time
from jarvis.app import main


def run_with_restart():
    """Executa o main() e reinicia silenciosamente em caso de crash."""
    while True:
        try:
            main()
            break
        except SystemExit:
            break
        except Exception:
            time.sleep(3)


if __name__ == "__main__":
    run_with_restart()
