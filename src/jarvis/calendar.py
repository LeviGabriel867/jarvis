"""
Google Calendar Integration
Fetch meetings with Google Meet links from Google Calendar API.
"""

import os
import sys
import json
import datetime
from pathlib import Path


def _get_config_dir():
    """Retorna o diretório de configuração."""
    if getattr(sys, "frozen", False):
        project_root = Path(sys._MEIPASS)
    else:
        project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "config"
    return config_dir


def _load_config():
    """Carrega configurações do config.json."""
    config_dir = _get_config_dir()
    config_file = config_dir / "config.json"
    with open(config_file, encoding="utf-8") as f:
        return json.load(f)


def _get_credentials():
    """Obtém credenciais OAuth2, autenticando se necessário."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    config = _load_config()
    config_dir = _get_config_dir()
    creds_dir = config_dir / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)

    creds_file = creds_dir / config.get("credentials_file", "credentials.json")
    token_file = creds_dir / config.get("token_file", "token.json")

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise FileNotFoundError(
                    f"Arquivo '{creds_file}' não encontrado.\n"
                    "  Acesse https://console.cloud.google.com\n"
                    "  1. Crie um projeto\n"
                    "  2. Ative a Google Calendar API\n"
                    "  3. Crie credenciais OAuth2 (tipo Desktop)\n"
                    "  4. Configure redirect_uri: http://localhost:8080/\n"
                    f"  5. Baixe o JSON e salve em: {creds_file}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            # Tenta porta 8080, fallback para 0 (qualquer porta disponível)
            try:
                creds = flow.run_local_server(port=8080)
            except Exception:
                creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def get_next_meeting():
    """
    Fetch the next meeting with a Google Meet link from the calendar.

    Returns dict with:
        - "title": event name
        - "start": start time (str HH:MM)
        - "link": Google Meet URL
    Or None if no meeting with link found.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Busca eventos das próximas 12 horas
    end = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])

    for event in events:
        meet_link = _extract_meet_link(event)
        if meet_link:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            try:
                start_dt = datetime.datetime.fromisoformat(start_raw)
                start_str = start_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                start_str = start_raw

            return {
                "title": event.get("summary", "Reunião sem título"),
                "start": start_str,
                "link": meet_link,
            }

    return None


def _extract_meet_link(event):
    """Extrai o link do Google Meet de um evento do calendário."""
    import re

    # Tenta conferenceData primeiro (forma padrão)
    conf = event.get("conferenceData", {})
    for entry in conf.get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            return entry.get("uri")

    # Fallback: hangoutLink
    hangout = event.get("hangoutLink")
    if hangout:
        return hangout

    # Fallback: procura meet.google.com na descrição ou localização
    for field in ["description", "location"]:
        text = event.get(field, "")
        if text and "meet.google.com/" in text:
            match = re.search(r'https://meet\.google\.com/[a-z\-]+', text)
            if match:
                return match.group(0)

    return None


def _extract_event_info(event):
    """
    Extrai informações de um evento do calendário sem filtrar por Meet link.

    Retorna dict com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM ou "Dia todo")
        - "end": horário de término (str HH:MM ou "Dia todo")
        - "type": "meeting" (tem Meet link) ou "event" (genérico)
        - "link": URL do Meet ou None
    """
    from datetime import datetime

    # Extrai título
    title = event.get("summary", "Evento sem título")

    # Extrai Meet link (se houver)
    meet_link = _extract_meet_link(event)
    event_type = "meeting" if meet_link else "event"

    # Extrai horários
    start_raw = event["start"].get("dateTime", event["start"].get("date"))
    end_raw = event["end"].get("dateTime", event["end"].get("date"))

    # Verifica se é evento de dia todo (tem apenas "date", não "dateTime")
    is_all_day = "dateTime" not in event["start"]

    if is_all_day:
        start_str = "Dia todo"
        end_str = "Dia todo"
    else:
        # Converte para HH:MM
        try:
            start_dt = datetime.fromisoformat(start_raw)
            start_str = start_dt.strftime("%H:%M")
        except (ValueError, TypeError):
            start_str = "?"

        try:
            end_dt = datetime.fromisoformat(end_raw)
            end_str = end_dt.strftime("%H:%M")
        except (ValueError, TypeError):
            end_str = "?"

    return {
        "title": title,
        "start": start_str,
        "end": end_str,
        "type": event_type,
        "link": meet_link,
    }


def get_today_meetings():
    """
    Lista todas as reuniões de hoje com link do Google Meet.

    Retorna list de dicts com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM)
        - "end": horário de término (str HH:MM)
        - "link": URL do Google Meet
    Ou lista vazia se não houver.
    """
    from googleapiclient.discovery import build
    from datetime import date as date_class

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    today = date_class.today().isoformat()
    tomorrow = (datetime.datetime.fromisoformat(today) + datetime.timedelta(days=1)).date().isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=f"{today}T00:00:00Z",
        timeMax=f"{tomorrow}T00:00:00Z",
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    meetings = []

    for event in events:
        meet_link = _extract_meet_link(event)
        if meet_link:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            end_raw = event["end"].get("dateTime", event["end"].get("date"))

            try:
                start_dt = datetime.datetime.fromisoformat(start_raw)
                start_str = start_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                start_str = "?"

            try:
                end_dt = datetime.datetime.fromisoformat(end_raw)
                end_str = end_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                end_str = "?"

            meetings.append({
                "title": event.get("summary", "Reunião sem título"),
                "start": start_str,
                "end": end_str,
                "link": meet_link,
            })

    return meetings


def get_today_events():
    """
    Lista todos os eventos (com ou sem videoconferência) agendados para hoje.

    Retorna list de dicts com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM ou "Dia todo")
        - "end": horário de término (str HH:MM ou "Dia todo")
        - "type": "meeting" ou "event"
        - "link": URL do Meet ou None
    Ou lista vazia se não houver eventos.
    """
    from googleapiclient.discovery import build
    from datetime import date as date_class

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    today = date_class.today().isoformat()
    tomorrow = (datetime.datetime.fromisoformat(today) + datetime.timedelta(days=1)).date().isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=f"{today}T00:00:00Z",
        timeMax=f"{tomorrow}T00:00:00Z",
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    result = []

    for event in events:
        # Inclui TODOS os eventos, não apenas os com Meet link
        event_info = _extract_event_info(event)
        result.append(event_info)

    return result


def _parse_date_reference(text_lower):
    """
    Interpreta referências de data em português natural.
    Retorna uma tupla (date_inicio, date_fim) ambos como datetime.date.

    Exemplos:
    - "hoje" -> (hoje, hoje)
    - "amanha" / "amanhã" -> (amanhã, amanhã)
    - "segunda" -> (próxima segunda-feira, próxima segunda-feira)
    - "proxima segunda" / "próxima segunda" -> (próxima segunda-feira, próxima segunda-feira)
    - "dia 15" / "15" -> (15º dia do mês atual, 15º dia do mês atual)
    - "5/12" -> (5 de dezembro do ano atual, 5 de dezembro do ano atual)
    - "semana que vem" / "proxima semana" -> (segunda-feira da próxima semana até domingo)
    """
    from datetime import date as date_class, timedelta
    import re

    hoje = date_class.today()
    amanha = hoje + timedelta(days=1)

    # Mapeamento de dias da semana para índice (segunda=0, domingo=6)
    dias_semana = {
        "segunda": 0, "terça": 1, "quarta": 2, "quinta": 3,
        "sexta": 4, "sábado": 5, "domingo": 6,
    }

    text = text_lower.replace("ã", "a").replace("é", "e").replace("á", "a")

    # Verificações simples first
    if "hoje" in text:
        return (hoje, hoje)

    if "amanha" in text or "amanhã" in text:
        return (amanha, amanha)

    # Semana que vem / próxima semana
    if "semana que vem" in text or "proxima semana" in text:
        dias_ate_segunda = (7 - hoje.weekday()) % 7
        if dias_ate_segunda == 0:
            dias_ate_segunda = 7
        segunda_proxima = hoje + timedelta(days=dias_ate_segunda)
        domingo_proxima = segunda_proxima + timedelta(days=6)
        return (segunda_proxima, domingo_proxima)

    # Dia da semana com modificadores (próximo, próxima, etc.)
    for dia_nome, dia_idx in dias_semana.items():
        if dia_nome in text:
            if "proxima" in text or "proximo" in text or "que vem" in text:
                # Próxima ocorrência
                dias_ate = (dia_idx - hoje.weekday()) % 7
                if dias_ate <= 0:
                    dias_ate += 7
                data_alvo = hoje + timedelta(days=dias_ate)
            else:
                # Próxima ocorrência mesmo que seja hoje
                dias_ate = (dia_idx - hoje.weekday()) % 7
                if dias_ate == 0 and "esta" not in text and "esse" not in text:
                    # Se é hoje, mas o usuário não especificou "esta", pega próxima
                    dias_ate = 7
                elif dias_ate == 0:
                    dias_ate = 0
                data_alvo = hoje + timedelta(days=dias_ate)
            return (data_alvo, data_alvo)

    # Mapeamento de meses em português
    meses_pt = {
        "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
        "outubro": 10, "novembro": 11, "dezembro": 12,
    }

    # Data com "do próximo mês": "15 do próximo mês" (ANTES de "próximo mês" sozinho)
    match = re.search(r'(\d{1,2})\s+(?:do\s+)?(?:proximo|próximo)\s+(?:mes|mês)', text)
    if match:
        dia = int(match.group(1))
        primeiro_prox = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
        if 1 <= dia <= 31:
            try:
                # Tenta criar data no próximo mês
                data_alvo = date_class(primeiro_prox.year, primeiro_prox.month, dia)
                return (data_alvo, data_alvo)
            except ValueError:
                # Se o dia não existe neste mês (ex: 31 de fevereiro), usa o último dia
                ultimo_dia = (date_class(primeiro_prox.year, primeiro_prox.month + 1, 1) - timedelta(days=1)).day
                data_alvo = date_class(primeiro_prox.year, primeiro_prox.month, min(dia, ultimo_dia))
                return (data_alvo, data_alvo)

    # Próximo mês (semanal, "próximo mês" / "mês que vem")
    if "proximo mes" in text or "mes que vem" in text or "proxima mes" in text:
        primeiro_prox = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
        ultimo_prox = (primeiro_prox + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return (primeiro_prox, ultimo_prox)

    # Data com nome de mês: "15 de abril" ou "15 de março" etc
    # Padrão: "(\d{1,2})\s+(?:de\s+)?([a-z]+)" para capturar "15 de abril" ou "15 abril"
    match = re.search(r'(\d{1,2})\s+(?:de\s+)?([a-z]+)', text)
    if match:
        dia = int(match.group(1))
        mes_nome = match.group(2).strip()
        if mes_nome in meses_pt and 1 <= dia <= 31:
            mes = meses_pt[mes_nome]
            try:
                data_alvo = date_class(hoje.year, mes, dia)
                if data_alvo < hoje:
                    data_alvo = date_class(hoje.year + 1, mes, dia)
                return (data_alvo, data_alvo)
            except ValueError:
                pass

    # Data numérica no formato dd/mm - verificar (mais específica que day alone)
    match = re.search(r'(\d{1,2})/(\d{1,2})', text)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        if 1 <= dia <= 31 and 1 <= mes <= 12:
            try:
                data_alvo = date_class(hoje.year, mes, dia)
                if data_alvo < hoje:
                    data_alvo = date_class(hoje.year + 1, mes, dia)
                return (data_alvo, data_alvo)
            except ValueError:
                pass

    # Data numérica: "dia 15" ou só "15"
    match = re.search(r'\bdia\s+(\d{1,2})\b', text)
    if not match:
        match = re.search(r'\b(\d{1,2})\b', text)
    if match:
        dia = int(match.group(1))
        if 1 <= dia <= 31:
            try:
                data_alvo = date_class(hoje.year, hoje.month, dia)
                if data_alvo < hoje:
                    # Se a data já passou neste mês, pega do próximo
                    if hoje.month == 12:
                        data_alvo = date_class(hoje.year + 1, 1, dia)
                    else:
                        data_alvo = date_class(hoje.year, hoje.month + 1, dia)
                return (data_alvo, data_alvo)
            except ValueError:
                pass

    # Padrão não reconhecido, retorna hoje
    return (hoje, hoje)


def get_meetings_for_date(date_text):
    """
    Lista reuniões com link do Google Meet para a data especificada.

    date_text: string em português natural (ex: "amanhã", "segunda", "dia 15")

    Retorna list de dicts com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM)
        - "end": horário de término (str HH:MM)
        - "link": URL do Google Meet
    Ou lista vazia se não houver.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    date_inicio, date_fim = _parse_date_reference(date_text.lower())

    # Converte para ISO format com hora
    time_min = f"{date_inicio.isoformat()}T00:00:00Z"
    time_max = f"{(date_fim + datetime.timedelta(days=1)).isoformat()}T00:00:00Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    meetings = []

    for event in events:
        meet_link = _extract_meet_link(event)
        if meet_link:
            start_raw = event["start"].get("dateTime", event["start"].get("date"))
            end_raw = event["end"].get("dateTime", event["end"].get("date"))

            try:
                start_dt = datetime.datetime.fromisoformat(start_raw)
                start_str = start_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                start_str = "?"

            try:
                end_dt = datetime.datetime.fromisoformat(end_raw)
                end_str = end_dt.strftime("%H:%M")
            except (ValueError, TypeError):
                end_str = "?"

            meetings.append({
                "title": event.get("summary", "Reunião sem título"),
                "start": start_str,
                "end": end_str,
                "link": meet_link,
            })

    return meetings


def get_all_events_for_date(date_text):
    """
    Lista TODOS os eventos (com ou sem videoconferência) para a data especificada.

    date_text: string em português natural (ex: "amanhã", "segunda", "dia 15")

    Retorna list de dicts com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM ou "Dia todo")
        - "end": horário de término (str HH:MM ou "Dia todo")
        - "type": "meeting" (tem Meet link) ou "event" (genérico)
        - "link": URL do Meet ou None
    Ou lista vazia se não houver.
    """
    from googleapiclient.discovery import build

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    date_inicio, date_fim = _parse_date_reference(date_text.lower())

    # Converte para ISO format com hora
    time_min = f"{date_inicio.isoformat()}T00:00:00Z"
    time_max = f"{(date_fim + datetime.timedelta(days=1)).isoformat()}T00:00:00Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    result = []

    for event in events:
        # Inclui TODOS os eventos, não apenas os com Meet link
        event_info = _extract_event_info(event)
        result.append(event_info)

    return result
