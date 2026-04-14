#!/usr/bin/env python3
"""
JARVIS v2.0 - INFUSER AUTOMATION TRIGGER
Detecta palmas via fingerprint espectral e dispara automações.

Uso:
  python jarvis.py             -> monitoramento normal
  python jarvis.py --calibrar  -> recalibrar palmas
"""

import sys
import os
import json
import time
import webbrowser
import threading
import numpy as np
import sounddevice as sd

# ─────────────────────────────────────────
# DISPOSITIVO DE AUDIO
# Execute diagnostico.py para ver os indices disponiveis.
# None = usa o padrao do Windows. Troque pelo indice do Realtek se necessario.
# Exemplo: sd.default.device = [1, None]
AUDIO_DEVICE = 23  # Microfone 2 (Fuxi-H6) - melhor dispositivo detectado
if AUDIO_DEVICE is not None:
    sd.default.device = [AUDIO_DEVICE, None]

# ─────────────────────────────────────────
# CONFIGURACOES
# ─────────────────────────────────────────
# Usa a sample rate nativa do dispositivo selecionado para evitar erros
_dev_info   = sd.query_devices(AUDIO_DEVICE if AUDIO_DEVICE is not None else sd.default.device[0])
SAMPLE_RATE = int(_dev_info['default_samplerate'])
CHUNK_DURATION   = 0.05          # 50ms por chunk
CHUNK_SIZE       = int(SAMPLE_RATE * CHUNK_DURATION)
CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_palmas.json")
FFT_SIZE         = 2048

# Deteccao (ajustados automaticamente na calibracao)
ENERGY_THRESHOLD     = 0.015     # limiar minimo de energia RMS
SIMILARITY_THRESHOLD = 0.75      # correlacao coseno minima com o fingerprint
CLAP_COOLDOWN        = 0.3       # segundos de cooldown entre palmas
CLAP_WINDOW          = 3.0       # janela de tempo para contar N palmas

# ─────────────────────────────────────────
# AUTOMACOES
# ─────────────────────────────────────────
DAILY_MEET_URL = "https://meet.google.com/rdc-prsm-gtg"


def trigger_3_palmas():
    """3 palmas -> Abre a daily do Google Meet."""
    print("\n[JARVIS] 3 palmas! Abrindo Daily Meeting...")
    webbrowser.open(DAILY_MEET_URL)
    print("   OK - Meet aberto.\n")


# Mapeamento: N palmas -> funcao a disparar
TRIGGERS = {
    3: trigger_3_palmas,
    # Adicione mais aqui:
    # 2: trigger_2_palmas,
}

# ─────────────────────────────────────────
# DSP - FINGERPRINT ESPECTRAL
# ─────────────────────────────────────────

def compute_fingerprint(audio_chunk):
    """FFT normalizada de um chunk de audio."""
    fft = np.abs(np.fft.rfft(audio_chunk, n=FFT_SIZE))
    peak = fft.max()
    return fft / peak if peak > 0 else fft


def cosine_similarity(a, b):
    """Correlacao coseno entre dois vetores."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def rms_energy(chunk):
    return float(np.sqrt(np.mean(chunk ** 2)))


def best_chunk_in_recording(audio):
    """Retorna o chunk de maior energia dentro de uma gravacao."""
    best, best_e = None, 0.0
    step = CHUNK_SIZE // 2
    for start in range(0, len(audio) - CHUNK_SIZE, step):
        chunk = audio[start:start + CHUNK_SIZE]
        e = rms_energy(chunk)
        if e > best_e:
            best_e, best = e, chunk
    return best


# ─────────────────────────────────────────
# CALIBRACAO
# ─────────────────────────────────────────

def calibrar():
    print("\n[JARVIS] MODO CALIBRACAO")
    print("-" * 40)
    print("Vou gravar 5 amostras das suas palmas.")
    print("A cada prompt, bata UMA palma com forca.\n")

    samples = []
    energies = []

    for i in range(5):
        input(f"  -> ENTER e bata a palma #{i + 1}: ")
        time.sleep(0.08)

        audio = sd.rec(
            int(SAMPLE_RATE * 0.4),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        audio = audio.flatten()

        chunk = best_chunk_in_recording(audio)
        if chunk is None:
            print("     AVISO: Sinal muito fraco, ignorado.\n")
            continue

        e = rms_energy(chunk)
        fp = compute_fingerprint(chunk)
        samples.append(fp)
        energies.append(e)
        print(f"     OK - Capturada (energia RMS: {e:.4f})\n")

    if len(samples) < 3:
        print("ERRO: Poucas amostras validas. Execute novamente.")
        return

    avg_fp = np.mean(samples, axis=0)
    avg_fp = avg_fp / avg_fp.max()

    auto_energy = float(min(energies)) * 0.4

    data = {
        "fingerprint": avg_fp.tolist(),
        "energy_threshold": max(auto_energy, 0.008),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "calibrated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "samples_count": len(samples),
    }

    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"OK - Calibracao salva em '{CALIBRATION_FILE}'")
    print(f"   Limiar de energia: {data['energy_threshold']:.4f}")
    print("   Execute: python jarvis.py\n")


# ─────────────────────────────────────────
# DETECTOR EM TEMPO REAL
# ─────────────────────────────────────────

class JarvisDetector:
    def __init__(self, cal):
        self.fingerprint      = np.array(cal["fingerprint"])
        self.energy_threshold = cal.get("energy_threshold", ENERGY_THRESHOLD)
        self.sim_threshold    = cal.get("similarity_threshold", SIMILARITY_THRESHOLD)
        self.clap_timestamps  = []
        self.last_clap_time   = 0.0
        self.running          = False
        self._lock            = threading.Lock()

    def _process_chunk(self, chunk):
        now    = time.time()
        energy = rms_energy(chunk)

        if energy < self.energy_threshold:
            return

        if now - self.last_clap_time < CLAP_COOLDOWN:
            return

        fp  = compute_fingerprint(chunk)
        sim = cosine_similarity(fp, self.fingerprint)

        if sim < self.sim_threshold:
            return

        with self._lock:
            self.last_clap_time = now
            self.clap_timestamps.append(now)
            self.clap_timestamps = [
                t for t in self.clap_timestamps if now - t <= CLAP_WINDOW
            ]
            count = len(self.clap_timestamps)

        print(f"PALMA #{count}  [sim={sim:.2f} | energia={energy:.4f}]")

        if count in TRIGGERS:
            with self._lock:
                self.clap_timestamps.clear()
            threading.Thread(target=TRIGGERS[count], daemon=True).start()

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"AVISO: {status}", flush=True)
        self._process_chunk(indata[:, 0].copy())

    def run(self):
        print("\n[JARVIS] Online - aguardando palmas...")
        print("   3 palmas -> Abre Daily Meeting")
        print("   Ctrl+C para encerrar.\n")
        self.running = True
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=CHUNK_SIZE,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
        ):
            try:
                while self.running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[JARVIS] Desligando...\n")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    print("=" * 38)
    print("   JARVIS v2.0  -  INFUSER AUTO")
    print("=" * 38)

    if mode == "--calibrar":
        calibrar()
        return

    if not os.path.exists(CALIBRATION_FILE):
        print("\nCALIBRACAO NAO ENCONTRADA.")
        print("Execute primeiro: python jarvis.py --calibrar\n")
        sys.exit(1)

    with open(CALIBRATION_FILE) as f:
        cal = json.load(f)

    print(f"   Calibracao de:  {cal.get('calibrated_at', '?')}")
    print(f"   Amostras usadas: {cal.get('samples_count', '?')}")

    detector = JarvisDetector(cal)
    detector.run()


if __name__ == "__main__":
    main()
