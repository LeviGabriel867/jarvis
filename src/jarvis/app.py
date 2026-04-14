#!/usr/bin/env python3
"""
JARVIS v3.0 - Assistente por Comando de Voz
Escuta a wake word "Jarvis", responde por voz e executa comandos.
Comandos e respostas configurados em comandos.json.

Uso:
  python jarvis.py             -> monitoramento normal
  python jarvis.py --listar    -> lista todos os comandos disponiveis
"""

import sys
import os
import json
import time
import webbrowser
import datetime
import asyncio
import tempfile
import random
import re
import subprocess
import ctypes
import threading
from difflib import SequenceMatcher

from pathlib import Path

# ─────────────────────────────────────────
# DISPOSITIVO DE AUDIO
# Execute diagnostico.py para ver os indices disponiveis.
# None = usa o padrao do Windows.
AUDIO_DEVICE = None
SAMPLE_RATE = 16000         # 16kHz — ideal para speech recognition

# ─────────────────────────────────────────
# CONFIGURACOES
# ─────────────────────────────────────────
WAKE_WORD = "jarvis"
LISTEN_TIMEOUT = 5          # segundos esperando frase completa
COMMAND_PAUSE = 0.8         # segundos de silencio para finalizar frase
PHRASE_TIME_LIMIT = 8       # duracao maxima da frase capturada
LANGUAGE = "pt-BR"
VOICE = "pt-BR-AntonioNeural"  # voz masculina brasileira (edge-tts)
RECALIBRATE_EVERY = 5       # recalibrar microfone a cada N comandos

_PROJECT_ROOT = Path(__file__).parent.parent.parent
BASE_DIR = _PROJECT_ROOT / "config"
COMMANDS_FILE = BASE_DIR / "commands.json"

# ─────────────────────────────────────────
# RESPOSTAS DO SISTEMA (wake word, erros, etc.)
# ─────────────────────────────────────────
UNKNOWN_COMMAND_RESPONSES = [
    "Desculpe senhor, não reconheço esse comando.",
    "Esse comando não está na minha lista senhor.",
    "Não tenho essa instrução configurada senhor.",
    "Senhor, não sei executar isso ainda.",
]

# ─────────────────────────────────────────
# IMPORTACOES COM VALIDACAO
# ─────────────────────────────────────────
try:
    import speech_recognition as sr
except ImportError:
    print("ERRO: Biblioteca 'speech_recognition' nao encontrada.")
    print("  Instale com: pip install SpeechRecognition")
    sys.exit(1)

try:
    import pyaudio  # noqa: F401 - necessario para sr.Microphone
except ImportError:
    print("ERRO: Biblioteca 'pyaudio' nao encontrada.")
    print("  Instale com: pip install pyaudio")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("ERRO: Biblioteca 'edge_tts' nao encontrada.")
    print("  Instale com: pip install edge-tts")
    sys.exit(1)

try:
    import pygame
except ImportError:
    print("ERRO: Biblioteca 'pygame' nao encontrada.")
    print("  Instale com: pip install pygame")
    sys.exit(1)


# ─────────────────────────────────────────
# MOTOR DE VOZ (TTS) HUMANIZADO
# ─────────────────────────────────────────

pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)

# Perfis de prosódia — cada fala sorteia um perfil levemente diferente
# para nao soar sempre igual (rate e pitch aceitos pelo edge-tts)
PROSODY_PROFILES = [
    {"rate": "-8%",  "pitch": "+3Hz"},   # calmo, levemente agudo
    {"rate": "-4%",  "pitch": "+0Hz"},   # ritmo natural, tom neutro
    {"rate": "-6%",  "pitch": "-2Hz"},   # pausado, tom serio
    {"rate": "-10%", "pitch": "+5Hz"},   # lento, gentil
    {"rate": "-2%",  "pitch": "-4Hz"},   # quase normal, mais grave
]

# Event loop persistente para TTS (evita overhead de asyncio.run() a cada fala)
_tts_loop = asyncio.new_event_loop()


_TTS_FILE = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")


def _release_tts_file():
    """Garante que o pygame libere o arquivo de áudio no Windows."""
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass
    # No Windows o unload() pode não liberar o handle imediatamente;
    # tenta deletar com breve retry para aguardar a liberação.
    for _ in range(5):
        try:
            if os.path.exists(_TTS_FILE):
                os.unlink(_TTS_FILE)
            return
        except PermissionError:
            time.sleep(0.05)


def speak(text):
    """Sintetiza e reproduz texto com voz masculina humanizada via edge-tts."""
    print(f'  [JARVIS] "{text}"')
    _release_tts_file()
    try:
        profile = random.choice(PROSODY_PROFILES)
        _tts_loop.run_until_complete(_generate_speech(text, _TTS_FILE, profile))
        pygame.mixer.music.load(_TTS_FILE)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(30)
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"  [JARVIS] Erro no TTS: {e}")


async def _generate_speech(text, output_file, profile):
    """Gera audio via edge-tts com prosódia variada."""
    communicate = edge_tts.Communicate(
        text,
        VOICE,
        rate=profile["rate"],
        pitch=profile["pitch"],
    )
    await communicate.save(output_file)


# ─────────────────────────────────────────
# ACOES BUILT-IN
# ─────────────────────────────────────────

_cached_calendar = None

def _calendar_module():
    """Importa e cacheia o módulo calendar para evitar re-imports."""
    global _cached_calendar
    if _cached_calendar is None:
        from . import calendar as cal
        _cached_calendar = cal
    return _cached_calendar


def _speak_response(cmd, default, **kwargs):
    """Fala uma resposta aleatória do comando, formatando variáveis."""
    resposta = random.choice(cmd.get("respostas", [default]))
    speak(resposta.format(**kwargs) if kwargs else resposta)


def action_abrir_url(cmd):
    """Abre uma URL no navegador e depois confirma."""
    webbrowser.open(cmd["url"])
    _speak_response(cmd, "Pronto senhor.")


def action_hora(cmd):
    """Informa a hora atual por voz."""
    agora = datetime.datetime.now().strftime("%H e %M")
    _speak_response(cmd, "São {hora} senhor.", hora=agora)


def action_data(cmd):
    """Informa a data atual por voz."""
    hoje = datetime.datetime.now()
    dias = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sábado", "domingo"]
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    data_str = f"{dias[hoje.weekday()]}, {hoje.day} de {meses[hoje.month - 1]} de {hoje.year}"
    _speak_response(cmd, "Hoje é {data} senhor.", data=data_str)


def action_desligar(cmd):
    """Fala despedida e encerra o JARVIS."""
    _speak_response(cmd, "Até logo senhor.")
    os._exit(0)


def action_saudacao(cmd):
    """Responde a uma saudação."""
    _speak_response(cmd, "Olá senhor.")


def action_fechar_programa(cmd):
    """Fecha um programa pelo nome do processo e depois confirma."""
    processos = cmd.get("processos", [])
    for proc in processos:
        subprocess.run(
            ["taskkill", "/im", proc, "/f"],
            capture_output=True,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    _speak_response(cmd, "Feito senhor.")


def _set_system_volume(level_0_to_10):
    """Define o volume do sistema de 0 a 10 via pycaw."""
    from pycaw.pycaw import AudioUtilities
    dev = AudioUtilities.GetSpeakers()
    vol = dev.EndpointVolume
    scalar = max(0.0, min(1.0, level_0_to_10 / 10.0))
    vol.SetMasterVolumeLevelScalar(scalar, None)


def action_volume(cmd):
    """Define o volume do sistema para o nível especificado (0 a 10)."""
    nivel = cmd.get("_nivel", 5)
    try:
        _set_system_volume(nivel)
        _speak_response(cmd, "Volume ajustado para {nivel} senhor.", nivel=nivel)
    except Exception as e:
        print(f"  [JARVIS] Erro ao ajustar volume: {e}")
        speak("Não consegui ajustar o volume senhor.")


def action_proxima_reuniao(cmd):
    """Busca a próxima reunião no Google Agenda e abre o Meet."""
    try:
        meeting = _calendar_module().get_next_meeting()
    except FileNotFoundError as e:
        print(f"  [JARVIS] {e}")
        speak("Senhor, o arquivo de credenciais do Google não foi encontrado. Verifique o setup.")
        return
    except Exception as e:
        print(f"  [JARVIS] Erro ao acessar Google Agenda: {e}")
        speak("Não consegui acessar o Google Agenda senhor.")
        return

    if meeting is None:
        speak("Senhor, não encontrei nenhuma reunião com link nas próximas horas.")
        return

    webbrowser.open(meeting["link"])
    _speak_response(
        cmd,
        "Abrindo a reunião {reuniao} das {horario} senhor.",
        reuniao=meeting["title"],
        horario=meeting["start"],
    )


def action_listar_reunioes_hoje(cmd):
    """Lista as reuniões de hoje com links de videoconferência."""
    try:
        meetings = _calendar_module().get_today_meetings()
    except FileNotFoundError as e:
        print(f"  [JARVIS] {e}")
        speak("Senhor, o arquivo de credenciais do Google não foi encontrado.")
        return
    except Exception as e:
        print(f"  [JARVIS] Erro ao acessar Google Agenda: {e}")
        speak("Não consegui acessar o Google Agenda senhor.")
        return

    if not meetings:
        speak("Senhor, não há reuniões com videoconferência agendadas para hoje.")
        return

    # Fala a lista
    msg = f"Você tem {len(meetings)} reunião" if len(meetings) == 1 else f"Você tem {len(meetings)} reuniões"
    msg += " com videoconferência hoje senhor. "
    for i, m in enumerate(meetings, 1):
        msg += f"{i}. {m['title']} das {m['start']} às {m['end']}. "
    speak(msg)


def action_reunioes_data(cmd):
    """Lista reuniões com links de videoconferência para uma data especificada."""
    try:
        date_reference = cmd.get("_date_ref", "")
        meetings = _calendar_module().get_meetings_for_date(date_reference)
    except FileNotFoundError as e:
        print(f"  [JARVIS] {e}")
        speak("Senhor, o arquivo de credenciais do Google não foi encontrado.")
        return
    except Exception as e:
        print(f"  [JARVIS] Erro ao acessar Google Agenda: {e}")
        speak("Não consegui acessar o Google Agenda senhor.")
        return

    if not meetings:
        speak("Senhor, não há reuniões com videoconferência agendadas para essa data.")
        return

    # Fala a lista
    msg = f"Você tem {len(meetings)} reunião" if len(meetings) == 1 else f"Você tem {len(meetings)} reuniões"
    msg += " com videoconferência nessa data senhor. "
    for i, m in enumerate(meetings, 1):
        msg += f"{i}. {m['title']} das {m['start']} às {m['end']}. "
    speak(msg)


def action_eventos_data(cmd):
    """Lista todos os eventos (reuniões e compromissos) para uma data especificada."""
    try:
        date_reference = cmd.get("_date_ref", "")
        events = _calendar_module().get_all_events_for_date(date_reference)
    except FileNotFoundError as e:
        print(f"  [JARVIS] {e}")
        speak("Senhor, o arquivo de credenciais do Google não foi encontrado.")
        return
    except Exception as e:
        print(f"  [JARVIS] Erro ao acessar Google Agenda: {e}")
        speak("Não consegui acessar o Google Agenda senhor.")
        return

    if not events:
        speak("Senhor, você não tem nenhum compromisso agendado para essa data.")
        return

    # Fala a lista completa (reuniões + eventos)
    msg = f"Você tem {len(events)} compromisso" if len(events) == 1 else f"Você tem {len(events)} compromissos"
    msg += " nessa data senhor. "
    for i, e in enumerate(events, 1):
        # Diferencia reuniões de eventos
        tipo_label = "reunião" if e['type'] == "meeting" else "evento"
        hora = f"das {e['start']} às {e['end']}" if e['start'] != "Dia todo" else "dia todo"
        msg += f"{i}. {e['title']} ({tipo_label}) {hora}. "
    speak(msg)


def action_bloquear_pc(cmd):
    """Bloqueia o computador (Windows + L)."""
    _speak_response(cmd, "Bloqueando o computador senhor.")
    ctypes.windll.user32.LockWorkStation()


def action_desligar_pc(cmd):
    """Desliga o computador de forma graciosa."""
    _speak_response(cmd, "Desligando o computador senhor.")
    subprocess.run(["shutdown", "/s", "/t", "5"], creationflags=0x08000000)


def action_suspender_pc(cmd):
    """Suspende o computador (modo dormir) via .NET SetSuspendState."""
    _speak_response(cmd, "Suspendendo o computador senhor.")
    time.sleep(1)  # aguarda a fala terminar antes de suspender
    # Usa PowerShell + .NET para suspensão confiável:
    # Suspend = modo dormir (não hibernate)
    # $false = não forçar (apps podem salvar dados)
    # $false = permitir acordar por teclado/mouse
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Add-Type -AssemblyName System.Windows.Forms; "
         "[System.Windows.Forms.Application]::SetSuspendState("
         "'Suspend', $false, $false)"],
        creationflags=0x08000000,
    )


# Mapa de tipo -> funcao executora
ACTION_HANDLERS = {
    "abrir_url": action_abrir_url,
    "hora": action_hora,
    "data": action_data,
    "desligar": action_desligar,
    "saudacao": action_saudacao,
    "fechar_programa": action_fechar_programa,
    "volume": action_volume,
    "proxima_reuniao": action_proxima_reuniao,
    "listar_reunioes_hoje": action_listar_reunioes_hoje,
    "reunioes_data": action_reunioes_data,
    "eventos_data": action_eventos_data,
    "bloquear_pc": action_bloquear_pc,
    "desligar_pc": action_desligar_pc,
    "suspender_pc": action_suspender_pc,
}


# ─────────────────────────────────────────
# CARREGAMENTO DE COMANDOS
# ─────────────────────────────────────────

def load_commands():
    """Carrega comandos do arquivo comandos.json."""
    if not os.path.exists(COMMANDS_FILE):
        print(f"ERRO: Arquivo de comandos nao encontrado: {COMMANDS_FILE}")
        print("  Crie o arquivo comandos.json na pasta do projeto.")
        sys.exit(1)

    with open(str(COMMANDS_FILE), encoding="utf-8") as f:
        commands = json.load(f)

    for cmd in commands:
        tipo = cmd.get("tipo")
        if tipo not in ACTION_HANDLERS:
            print(f"  AVISO: Tipo desconhecido '{tipo}' no comando "
                  f"'{cmd.get('triggers', ['?'])[0]}', ignorado.")

    return commands


# Mapa de palavras faladas para números (o Google Speech transcreve por extenso)
WORD_TO_NUMBER = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
    "quatro": 4, "cinco": 5, "seis": 6, "meia": 6, "sete": 7,
    "oito": 8, "nove": 9, "dez": 10,
}


def _extract_number(text):
    """Extrai um número de 0 a 10 do texto (dígito ou por extenso)."""
    # Tenta dígito primeiro
    match = re.search(r'\b(\d{1,2})\b', text)
    if match:
        n = int(match.group(1))
        if 0 <= n <= 10:
            return n
    # Tenta por extenso
    for word, n in WORD_TO_NUMBER.items():
        if word in text.lower():
            return n
    return None


def _enrich_command(cmd, text_lower):
    """Adiciona dados extras ao comando conforme o tipo (volume, datas, etc.)."""
    tipo = cmd.get("tipo")
    if tipo == "volume":
        nivel = _extract_number(text_lower)
        if nivel is not None:
            cmd = dict(cmd)
            cmd["_nivel"] = nivel
    elif tipo in ("reunioes_data", "eventos_data"):
        cmd = dict(cmd)
        cmd["_date_ref"] = text_lower
    return cmd


def match_command(text, commands):
    """
    Encontra o comando correspondente ao texto falado.

    Comandos com match_case=true exigem que o texto seja idêntico a um dos
    triggers (proteção contra ativação acidental de ações críticas).

    Comandos com match_case=false (maioria) são ranqueados por semântica:
      1. Match exato por substring → score 1.0 (prioridade máxima)
      2. Fuzzy matching (SequenceMatcher) → score 0..1

    O comando com maior score acima do limiar mínimo (0.5) é escolhido.
    """
    text_lower = text.lower().strip()

    # ── Fase 1: comandos com match_case=true (exigem texto idêntico) ──
    for cmd in commands:
        if not cmd.get("match_case", False):
            continue
        for trigger in cmd["triggers"]:
            if text_lower == trigger:
                return _enrich_command(cmd, text_lower)

    # ── Fase 2: comandos com match_case=false (ranqueados por semântica) ──
    best_match = None
    best_score = 0.5  # limiar mínimo de similaridade

    for cmd in commands:
        if cmd.get("match_case", False):
            continue

        for trigger in cmd["triggers"]:
            # Substring exata ganha score máximo
            if trigger in text_lower:
                score = 1.0
            else:
                score = SequenceMatcher(None, text_lower, trigger).ratio()

            if score > best_score:
                best_score = score
                best_match = cmd
                if score == 1.0:
                    break  # substring match, não precisa testar outros triggers

    if best_match:
        return _enrich_command(best_match, text_lower)

    return None


def execute_command(cmd):
    """Executa a acao de um comando."""
    handler = ACTION_HANDLERS.get(cmd["tipo"])
    if handler:
        handler(cmd)
    else:
        speak(f"Tipo de ação '{cmd['tipo']}' não implementado senhor.")


def listar_comandos(commands):
    """Exibe todos os comandos disponiveis."""
    print("\n  Comandos disponiveis:")
    print("  " + "-" * 55)
    for cmd in commands:
        principal = cmd["triggers"][0]
        aliases = cmd["triggers"][1:]
        print(f'  "{principal}"')
        print(f"    -> {cmd['descricao']}")
        if aliases:
            print(f"    Alternativas: {', '.join(aliases)}")
        respostas = cmd.get("respostas", [])
        if respostas:
            print(f"    Respostas possiveis: {len(respostas)}")
        print()


# ─────────────────────────────────────────
# RECONHECIMENTO DE VOZ
# ─────────────────────────────────────────

COMMAND_COOLDOWN = 2.0      # segundos de espera após executar um comando
DEDUP_WINDOW = 4.0          # segundos para ignorar comando idêntico repetido
LISTEN_HARD_TIMEOUT = LISTEN_TIMEOUT + PHRASE_TIME_LIMIT + 5  # timeout absoluto do listen


KEEPALIVE_INTERVAL = 60     # segundos entre pings do microfone para mantê-lo ativo


class JarvisAssistant:
    def __init__(self, commands):
        self.commands = commands
        self._command_count = 0
        self._last_command_type = None
        self._last_command_time = 0.0
        self._last_listen_time = time.time()
        self._init_recognizer()
        self._init_microphone()

    def _init_recognizer(self):
        """Inicializa (ou reinicializa) o recognizer."""
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = COMMAND_PAUSE
        self.recognizer.phrase_threshold = 0.2
        self.recognizer.non_speaking_duration = 0.4

    def _init_microphone(self):
        """Cria (ou recria) o objeto Microphone."""
        if AUDIO_DEVICE is not None:
            self.mic = sr.Microphone(device_index=AUDIO_DEVICE, sample_rate=SAMPLE_RATE)
        else:
            self.mic = sr.Microphone(sample_rate=SAMPLE_RATE)

    def _terminate_pyaudio(self):
        """Encerra a instância interna do PyAudio para liberar o dispositivo."""
        try:
            if hasattr(self, 'mic') and self.mic is not None:
                # sr.Microphone armazena a instância em mic.audio
                pa = getattr(self.mic, 'audio', None)
                if pa is not None:
                    pa.terminate()
        except Exception:
            pass

    def _reinit_audio(self):
        """Reinicializa todo o subsistema de áudio após falha (ex: retorno de suspensão)."""
        print("  [JARVIS] Reinicializando subsistema de áudio...")
        # 1. Fecha o PyAudio antigo para liberar o dispositivo de entrada
        self._terminate_pyaudio()
        # 2. Reinicializa pygame mixer (dispositivo de saída)
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        time.sleep(1)  # aguarda o Windows liberar os dispositivos
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
        except Exception as e:
            print(f"  [JARVIS] Erro ao reiniciar mixer: {e}")
        # 3. Recria recognizer e microfone com nova instância PyAudio
        self._init_recognizer()
        self._init_microphone()
        print("  [JARVIS] Subsistema de áudio reinicializado.")

    def calibrate(self):
        """Calibra o microfone para o ruido ambiente."""
        print("  [JARVIS] Calibrando microfone para ruido ambiente...")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"  [JARVIS] Calibracao concluida (energy_threshold={self.recognizer.energy_threshold:.0f}).")

    def _maybe_recalibrate(self):
        """Recalibra periodicamente para manter qualidade do áudio."""
        self._command_count += 1
        if self._command_count % RECALIBRATE_EVERY == 0:
            print("  [JARVIS] Recalibrando microfone...")
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def _keepalive(self):
        """Toca brevemente o microfone se ficou ocioso por muito tempo.

        Evita que o Windows libere o dispositivo de áudio por inatividade,
        reduzindo a necessidade de reinicializações após períodos ociosos.
        """
        now = time.time()
        if (now - self._last_listen_time) >= KEEPALIVE_INTERVAL:
            try:
                with self.mic as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                self._last_listen_time = now
            except (OSError, IOError):
                pass  # será tratado pelo loop principal

    def _flush_mic_buffer(self):
        """Descarta áudio residual do microfone após executar um comando.

        Abre o microfone brevemente para consumir qualquer áudio que ficou
        no buffer do PyAudio (eco da resposta TTS, reverberação, etc.),
        evitando que o próximo listen() capture áudio antigo.
        """
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=COMMAND_COOLDOWN)

    def _is_duplicate_command(self, cmd_type):
        """Verifica se o mesmo tipo de comando foi executado há pouco tempo."""
        now = time.time()
        if cmd_type == self._last_command_type and (now - self._last_command_time) < DEDUP_WINDOW:
            return True
        return False

    def _mark_command_executed(self, cmd_type):
        """Registra o comando executado para dedup."""
        self._last_command_type = cmd_type
        self._last_command_time = time.time()

    def listen_loop(self):
        """Escuta uma frase completa e retorna o texto transcrito.

        Executa o listen() em uma thread separada com timeout absoluto.
        Se o PyAudio travar (ex: após retorno de suspensão), o timeout
        real dispara e levanta RuntimeError para acionar a recuperação.
        """
        self._keepalive()
        result = [None]
        error = [None]

        def _listen_worker():
            try:
                with self.mic as source:
                    audio = self.recognizer.listen(
                        source,
                        timeout=LISTEN_TIMEOUT,
                        phrase_time_limit=PHRASE_TIME_LIMIT,
                    )
                    result[0] = self.recognizer.recognize_google(audio, language=LANGUAGE)
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"  [JARVIS] Erro no servico de reconhecimento: {e}")
            except Exception as e:
                error[0] = e

        self._last_listen_time = time.time()
        worker = threading.Thread(target=_listen_worker, daemon=True)
        worker.start()
        worker.join(timeout=LISTEN_HARD_TIMEOUT)

        if worker.is_alive():
            # Thread travou — stream de áudio morto (típico após suspensão)
            print("  [JARVIS] Timeout absoluto — microfone não respondeu.")
            raise RuntimeError("Microfone travado após suspensão")

        if error[0] is not None:
            raise error[0]

        return result[0]

    def extract_command(self, text):
        """Verifica se a frase contem a wake word e extrai o comando."""
        text_lower = text.lower().strip()
        if WAKE_WORD not in text_lower:
            return None

        # Remove a wake word e pontuacao ao redor para isolar o comando
        # Ex: "jarvis, entrar em daily" -> "entrar em daily"
        #     "jarvis entrar em daily"  -> "entrar em daily"
        parts = re.split(r'jarvis[,.]?\s*', text_lower, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()

        # Wake word foi dita sozinha, sem comando
        return ""

    def _safe_startup(self):
        """Calibra e anuncia que está online. Retenta em caso de falha de áudio."""
        while True:
            try:
                self.calibrate()
                speak("Sistemas online. Aguardando suas ordens senhor.")
                return
            except (OSError, Exception) as e:
                print(f"  [JARVIS] Falha na inicialização de áudio: {e}")
                print("  [JARVIS] Tentando novamente em 5 segundos...")
                time.sleep(5)
                self._reinit_audio()

    def run(self):
        """Loop principal — escuta frases completas com wake word + comando.

        Resiliente a suspensão/hibernação: detecta falhas no dispositivo de
        áudio e reinicializa automaticamente, mantendo o Jarvis sempre
        disponível enquanto o computador estiver ligado.
        """
        print('\n  [JARVIS] Online - diga "Jarvis" seguido do comando na mesma frase.')
        print('  [JARVIS] Exemplo: "Jarvis, entrar em daily"')
        print("  [JARVIS] Ctrl+C para encerrar.\n")

        listar_comandos(self.commands)
        self._safe_startup()

        while True:
            had_command = False  # indica se havia comando em andamento ao falhar
            try:
                text = self.listen_loop()

                if text is None:
                    continue

                command_text = self.extract_command(text)

                # Frase sem "Jarvis" — ignora silenciosamente
                if command_text is None:
                    continue

                print(f'  [JARVIS] Ouviu: "{text}"')

                # "Jarvis" sozinho, sem comando
                if command_text == "":
                    speak("Sim senhor?")
                    continue

                cmd = match_command(command_text, self.commands)
                if cmd:
                    cmd_type = cmd.get("tipo", "")
                    if self._is_duplicate_command(cmd_type):
                        print(f'  [JARVIS] Comando duplicado ignorado: "{cmd_type}"')
                        continue
                    had_command = True
                    print(f"  [JARVIS] Executando: {cmd['descricao']}")
                    execute_command(cmd)
                    had_command = False
                    self._mark_command_executed(cmd_type)
                    # Descarta áudio residual para evitar re-execução
                    self._flush_mic_buffer()
                else:
                    print(f'  [JARVIS] Comando nao reconhecido: "{command_text}"')
                    speak(random.choice(UNKNOWN_COMMAND_RESPONSES))

                self._maybe_recalibrate()
                print()

            except KeyboardInterrupt:
                speak("Encerrando. Até a próxima senhor.")
                break

            except Exception as e:
                print(f"  [JARVIS] Erro detectado: {e}")
                # Loop de recuperação: retenta até o áudio voltar
                recovered = False
                for attempt in range(1, 13):  # até ~1 min de tentativas
                    print(f"  [JARVIS] Tentativa de recuperação {attempt}/12...")
                    self._reinit_audio()
                    try:
                        self.calibrate()
                        if had_command:
                            speak("Senhor, tive uma falha mas já me recuperei. "
                                  "Pode repetir o comando por favor?")
                        else:
                            speak("Reinicialização concluída senhor. Estou de volta.")
                        recovered = True
                        break
                    except Exception as retry_err:
                        print(f"  [JARVIS] Áudio indisponível: {retry_err}")
                        time.sleep(5)
                if not recovered:
                    # Última tentativa falhou — reinicia o processo inteiro
                    print("  [JARVIS] Todas as tentativas falharam. Reiniciando processo...")
                    _restart_process()


# ─────────────────────────────────────────
# RESTART / MAIN
# ─────────────────────────────────────────

def _restart_process():
    """Reinicia o processo Python inteiro (última instância de recuperação)."""
    print("  [JARVIS] Substituindo processo por nova instância...")
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


def main():
    print("=" * 42)
    print("   JARVIS v3.0  -  ASSISTENTE DE VOZ")
    print("=" * 42)

    commands = load_commands()

    if "--listar" in sys.argv:
        listar_comandos(commands)
        return

    assistant = JarvisAssistant(commands)
    assistant.run()


if __name__ == "__main__":
    main()
