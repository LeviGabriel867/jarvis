"""
Integração com Google Calendar API.
Busca a próxima reunião com link de videoconferência (Google Meet).
"""

import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def _load_config():
    """Carrega configurações do config.json."""
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def _get_credentials():
    """Obtém credenciais OAuth2, autenticando se necessário."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    config = _load_config()
    creds_file = os.path.join(BASE_DIR, config.get("credentials_file", "credentials.json"))
    token_file = os.path.join(BASE_DIR, config.get("token_file", "token.json"))

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_file):
                raise FileNotFoundError(
                    f"Arquivo '{creds_file}' não encontrado.\n"
                    "  Acesse https://console.cloud.google.com\n"
                    "  1. Crie um projeto\n"
                    "  2. Ative a Google Calendar API\n"
                    "  3. Crie credenciais OAuth2 (tipo Desktop)\n"
                    "  4. Configure redirect_uri: http://localhost:8080/\n"
                    "  5. Baixe o JSON e salve como 'credentials.json' na pasta do JARVIS"
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
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
    Busca a próxima reunião com link do Google Meet no calendário.

    Retorna dict com:
        - "title": nome do evento
        - "start": horário de início (str HH:MM)
        - "link": URL do Google Meet
    Ou None se não houver reunião com link.
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
            import re
            match = re.search(r'https://meet\.google\.com/[a-z\-]+', text)
            if match:
                return match.group(0)

    return None


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

    # Data numérica no formato dd/mm - verificar PRIMEIRO (mais específica)
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
