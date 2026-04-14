"""
Diagnostico de audio para o JARVIS
Testa cada dispositivo de entrada e mostra qual captura audio real.
"""

import sys
import time
import numpy as np

print("=" * 55)
print("  DIAGNOSTICO DE AUDIO - JARVIS  (teste por dispositivo)")
print("=" * 55)

try:
    import sounddevice as sd
    import numpy as np
except ImportError as e:
    print(f"ERRO: {e}")
    sys.exit(1)

devices = sd.query_devices()
candidatos = [
    (i, dev) for i, dev in enumerate(devices)
    if dev['max_input_channels'] > 0 and dev['default_samplerate'] in (44100, 48000)
    and any(k in dev['name'] for k in ['Realtek', 'Microfone', 'Microphone', 'Camo', 'Input', 'Primario', 'Driver'])
    and 'Alto-falante' not in dev['name']
    and 'Mixagem' not in dev['name']
    and 'Mapeador' not in dev['name']
]

print(f"\nEncontrei {len(candidatos)} dispositivos para testar.\n")
print("BATA PALMAS CONTINUAMENTE enquanto o teste roda...\n")
input("Pressione ENTER para iniciar: ")
print()

resultados = []

for idx, (i, dev) in enumerate(candidatos):
    nome = dev['name']
    sr = int(dev['default_samplerate'])
    ch = min(dev['max_input_channels'], 2)
    print(f"  [{i:2d}] {nome[:45]:<45} testando...", end='', flush=True)
    try:
        audio = sd.rec(int(sr * 0.6), samplerate=sr, channels=ch,
                       dtype='float32', device=i)
        sd.wait()
        audio = audio.flatten()
        rms = float(np.sqrt(np.mean(audio ** 2)))
        pico = float(np.max(np.abs(audio)))
        status = "OK  " if rms > 0.005 else ("FRACO" if rms > 0.0002 else "MUDO ")
        print(f" RMS={rms:.5f}  PICO={pico:.4f}  [{status}]")
        resultados.append((rms, i, nome, sr, status))
    except Exception as e:
        print(f" ERRO: {e}")

# Ordena pelo melhor RMS
resultados.sort(reverse=True)

print("\n" + "=" * 55)
print("  RESULTADO")
print("=" * 55)

if resultados and resultados[0][0] > 0.0002:
    melhor_rms, melhor_idx, melhor_nome, melhor_sr, _ = resultados[0]
    print(f"\n  Melhor dispositivo: [{melhor_idx}] {melhor_nome}")
    print(f"  RMS capturado:      {melhor_rms:.5f}")
    print(f"\n  Configure em jarvis.py:")
    print(f"    AUDIO_DEVICE = {melhor_idx}")
    print(f"\n  Depois recalibre:")
    print(f"    python jarvis.py --calibrar")
else:
    print("\n  NENHUM dispositivo capturou audio suficiente.")
    print("  Verifique: Configuracoes > Privacidade > Microfone")
    print("  Certifique-se de que 'Permitir que apps acessem o microfone' esta ON")
    print("  e que 'Permitir que aplicativos de desktop acessem o microfone' esta ON")

print("\n  Top 3 dispositivos:")
for rms, i, nome, sr, status in resultados[:3]:
    print(f"    [{i:2d}] {nome[:40]:<40} RMS={rms:.5f} [{status}]")

print("=" * 55)
