# JARVIS v3.0 - Assistente por Comando de Voz

Assistente de voz local para Windows. Escuta a wake word **"Jarvis"**, responde por voz com uma voz masculina humanizada (Microsoft Edge Neural TTS) e executa comandos. Respostas aleatorias a cada interacao para soar natural.

---

## Quick Start

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Usar um dos launchers (ou executar pelo Python)
python scripts/run.py         # Python launcher
# ou
scripts/run.bat               # Windows com console
# ou
scripts/run_hidden.vbs        # Windows silencioso
```

**Nota**: Na primeira vez, você será solicitado a autenticar com Google Calendar (caso queira usar recursos de agenda).

---

## Estrutura do Projeto

```
jarvis/
├── src/jarvis/              # Código-fonte principal
│   ├── __init__.py
│   ├── app.py              # Aplicação principal (assistente de voz + TTS)
│   └── calendar.py         # Integração com Google Calendar API
├── config/                  # Configuração e dados sensíveis
│   ├── commands.json       # Comandos, triggers e respostas (edite aqui)
│   ├── config.json         # Configurações (conta Google, caminhos)
│   ├── config.example.json # Template de configuração
│   └── credentials/        # Credenciais OAuth2 (não versionado)
│       ├── credentials.json # (você configura) Credenciais OAuth2 do Google Cloud
│       └── token.json      # (gerado automaticamente) Token de autenticação
├── scripts/                 # Scripts de inicialização
│   ├── run.py              # Launcher Python
│   ├── run.bat             # Launcher Windows (com console)
│   └── run_hidden.vbs      # Launcher Windows (modo oculto)
├── docs/                    # Documentação
│   └── CONTRIBUTING.md     # Guia de contribuição
├── .gitignore              # Git ignore rules
├── README.md               # Esta documentação
├── requirements.txt        # Dependências Python
└── setup.py               # Configuração de empacotamento
```

## Dependencias

| Pacote              | Funcao                                           |
|---------------------|--------------------------------------------------|
| `SpeechRecognition`         | Reconhecimento de voz (Google Speech API)         |
| `pyaudio`                   | Captura de audio do microfone                     |
| `edge-tts`                  | Sintese de voz neural masculina (Antonio, pt-BR)  |
| `pygame`                    | Reproducao do audio gerado pelo TTS               |
| `pycaw`                     | Controle de volume do Windows (API COM)            |
| `google-api-python-client`  | Acesso ao Google Calendar API                     |
| `google-auth-oauthlib`      | Autenticacao OAuth2 com Google                    |
| `google-auth-httplib2`      | Transporte HTTP para autenticacao Google          |

Instalar tudo:

```bash
pip install -r requirements.txt
```

> Se `pyaudio` falhar no Windows:
> ```bash
> pip install pipwin && pipwin install pyaudio
> ```

## Como Funciona

Fale tudo numa unica frase: **"Jarvis, entrar em daily"**. Se a frase nao contiver "Jarvis", e ignorada.

```
Microfone (escuta continua)
    |
    v
[1] Transcreve frase completa via Google Speech API
    |
    v
[2] Contem "Jarvis"?
    |        |
   NAO      SIM -> extrai o comando da frase
    |        |
  ignora     v
          [3] Busca correspondencia em comandos.json
              |
              v
          [4] Fala a resposta (aleatorio) e executa a acao
```

Se disser apenas "Jarvis" sem comando, ele responde "Sim, senhor?".

### Voz Humanizada

- Motor: **Microsoft Edge Neural TTS** via `edge-tts`
- Voz: **pt-BR-AntonioNeural** (masculina, brasileira, neural)
- Humanizacao via prosódia variada:
  - Cada fala sorteia um entre **5 perfis** de ritmo (`rate`) e entonacao (`pitch`)
  - Mesma frase soa ligeiramente diferente a cada vez
- Cada comando tem multiplas respostas possiveis — o JARVIS escolhe uma aleatoriamente

---

## Comandos Disponiveis

Todos os comandos ficam em **`comandos.json`**:

| Voce diz                             | O JARVIS responde (exemplo)                         | Acao                          |
|--------------------------------------|------------------------------------------------------|-------------------------------|
| "Jarvis, bom dia"                    | "Bom dia senhor. Pronto para mais um dia produtivo." | Saudacao                      |
| "Jarvis, boa tarde"                  | "Boa tarde! Como posso ajuda-lo senhor?"             | Saudacao                      |
| "Jarvis, boa noite"                  | "Boa noite senhor."                                  | Saudacao                      |
| "Jarvis, abrir reunião"              | "Entrando na Daily Standup das 09:30 senhor."        | Busca próxima reunião na agenda |
| "Jarvis, o que tenho pra hoje"       | "Você tem 3 reuniões com videoconferência hoje..."   | Lista reuniões do dia          |
| "Jarvis, reuniões de amanhã"         | "Você tem 2 reuniões com videoconferência amanhã..." | Lista reuniões de amanhã       |
| "Jarvis, reuniões de segunda"        | "Você tem 1 reunião segunda-feira..."                | Lista reuniões de segunda-feira|
| "Jarvis, reuniões da próxima quarta" | "Você tem reuniões na próxima quarta..."             | Lista reuniões de quarta      |
| "Jarvis, reuniões semana que vem"    | "Você tem reuniões para a semana que vem..."        | Lista reuniões da próxima semana|
| "Jarvis, abrir navegador"            | "Navegador aberto senhor."                           | Abre Google no browser        |
| "Jarvis, fechar navegador"           | "Fechando o navegador senhor."                       | Fecha o navegador             |
| "Jarvis, volume 7"                   | "Volume ajustado para 7 senhor."                     | Define volume em 70%          |
| "Jarvis, volume zero"                | "Volume ajustado para 0 senhor."                     | Muta o sistema                |
| "Jarvis, volume dez"                 | "Volume ajustado para 10 senhor."                    | Volume maximo                 |
| "Jarvis, bloquear computador"        | "Bloqueando o computador senhor."                    | Windows + L                   |
| "Jarvis, desligar computador"        | "Desligando o computador em 5 segundos senhor."      | Shutdown gracioso             |
| "Jarvis, que horas sao"              | "Agora sao 14 e 30 senhor."                          | Fala a hora atual             |
| "Jarvis, que dia e hoje"             | "Hoje e segunda-feira, 14 de abril de 2026 senhor."  | Fala a data atual             |
| "Jarvis, encerrar"                   | "Ate logo senhor. Foi um prazer."                    | Encerra o JARVIS              |

Cada comando aceita alternativas (veja `triggers` no JSON). Para listar no terminal:

```bash
python jarvis.py --listar
```

---

## Editando Comandos e Respostas (comandos.json)

Abra `comandos.json` e edite diretamente. Nao precisa mexer no codigo Python.

### Estrutura de um comando

```json
{
  "tipo": "abrir_url",
  "triggers": ["entrar em daily", "abrir daily"],
  "descricao": "Abre a Daily Meeting no Google Meet",
  "url": "https://meet.google.com/xxx-xxxx-xxx",
  "respostas": [
    "Conectando voce a daily agora, senhor.",
    "Daily meeting aberta. Bom trabalho hoje, senhor.",
    "Abrindo a daily. Todos ja devem estar esperando."
  ]
}
```

### Campos

| Campo        | Obrigatorio    | Descricao                                                    |
|--------------|----------------|--------------------------------------------------------------|
| `tipo`       | Sim            | Tipo da acao (ver tabela abaixo)                             |
| `triggers`   | Sim            | Frases que ativam o comando (case-insensitive, por substring)|
| `descricao`  | Sim            | Texto exibido no terminal                                    |
| `respostas`  | Sim            | Lista de frases que o JARVIS fala (escolha aleatoria)        |
| `url`        | Tipo `abrir_url` | URL a abrir no navegador                                   |
| `processos`  | Tipo `fechar_programa` | Lista de nomes de processo a encerrar (ex: `chrome.exe`) |

### Variaveis nas respostas

Alguns tipos substituem variaveis nas respostas:

- `{hora}` - hora atual (ex: "14 e 30") — tipo `hora`
- `{data}` - data atual (ex: "segunda-feira, 14 de abril de 2026") — tipo `data`
- `{nivel}` - nível de volume falado, de 0 a 10 — tipo `volume`
- `{reuniao}` - nome da reunião (ex: "Daily Standup") — tipo `proxima_reuniao`
- `{horario}` - horário de início da reunião (ex: "09:30") — tipo `proxima_reuniao`

Exemplo:
```json
"respostas": ["Agora sao {hora}, senhor.", "O relogio marca {hora}."]
```

### Tipos de comando

| Tipo               | Descricao                                             | Campos extras     |
|--------------------|-------------------------------------------------------|-------------------|
| `saudacao`         | Apenas fala a resposta                                | -                 |
| `abrir_url`        | Abre uma URL no navegador                             | `url`             |
| `proxima_reuniao`  | Busca próxima reunião no Google Agenda e abre o Meet  | -                 |
| `listar_reunioes_hoje` | Lista reuniões com videoconferência de hoje        | -                 |
| `reunioes_data`    | Lista reuniões para uma data específica (inteligência em português) | -                 |
| `fechar_programa`  | Fecha programa(s) pelo processo                       | `processos`       |
| `volume`           | Define volume de 0 a 10 (usa `{nivel}`, `pycaw`)     | -                 |
| `bloquear_pc`      | Bloqueia o computador (Win+L)                         | -                 |
| `desligar_pc`      | Desliga o computador (gracioso, 5s) — exige match exato | -                 |
| `hora`             | Fala a hora atual (usa `{hora}`)                      | -                 |
| `data`             | Fala a data atual (usa `{data}`)                      | -                 |
| `desligar`         | Encerra o JARVIS                                      | -                 |

#### Exemplos

Saudacao:
```json
{
  "tipo": "saudacao",
  "triggers": ["bom dia"],
  "descricao": "Responde bom dia",
  "respostas": ["Bom dia, senhor!", "Bom dia! Pronto para mais um dia."]
}
```

Abrir URL:
```json
{
  "tipo": "abrir_url",
  "triggers": ["abrir spotify", "tocar musica"],
  "descricao": "Abre o Spotify Web",
  "url": "https://open.spotify.com",
  "respostas": ["Abrindo o Spotify, senhor.", "Musica a caminho, senhor."]
}
```

Fechar programa:
```json
{
  "tipo": "fechar_programa",
  "triggers": ["fechar navegador"],
  "descricao": "Fecha o navegador",
  "processos": ["chrome.exe", "msedge.exe", "firefox.exe"],
  "respostas": ["Fechando o navegador, senhor."]
}
```

Controle do sistema:
```json
{
  "tipo": "bloquear_pc",
  "triggers": ["bloquear computador", "trancar pc"],
  "descricao": "Bloqueia o computador",
  "respostas": ["Bloqueando o computador, senhor."]
}
```

---

## Setup do Google Calendar (para comando "abrir reunião")

Para que o JARVIS busque reuniões automaticamente na sua agenda:

### 1. Criar projeto no Google Cloud

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um novo projeto (ex: "JARVIS")
3. No menu lateral, va em **APIs e servicos** > **Biblioteca**
4. Busque **Google Calendar API** e clique em **Ativar**

### 2. Criar credenciais OAuth2

1. Va em **APIs e servicos** > **Credenciais**
2. Clique em **Criar credenciais** > **ID do cliente OAuth**
3. Se pedir, configure a **Tela de consentimento** (tipo: Externo, preencha nome e email)
4. Tipo de aplicativo: **App para computador**
5. Baixe o JSON e salve como `credentials.json` na pasta do JARVIS

### 3. Configurar a conta

Edite `config.json`:

```json
{
  "google_account": "nelson@starbridge.com.br",
  "credentials_file": "credentials.json",
  "token_file": "token.json"
}
```

### 4. Primeira autenticação

Na primeira vez que disser "Jarvis, abrir reunião", o navegador abre para autorizar o acesso. Depois, o `token.json` é salvo e não precisa autorizar novamente.

---

## Inteligência de Data em Português

O comando `reunioes_data` entende referências de data em português natural:

### Referências de data suportadas

| Você diz | Interpretação |
|----------|---------------|
| "reuniões de amanhã" | Reuniões do dia seguinte |
| "reuniões de segunda" | Reuniões da próxima segunda-feira |
| "reuniões de quarta" | Reuniões da próxima quarta-feira |
| "reuniões da próxima segunda" | Reuniões da próxima segunda-feira (explícito) |
| "reuniões semana que vem" | Todas as reuniões da próxima semana (seg-dom) |
| "reuniões dia 15" | Reuniões do dia 15º do mês (atual ou próximo se já passou) |
| "reuniões 15/12" | Reuniões de 15 de dezembro |

### Como funciona a interpretação

- **Dias da semana**: Procura a próxima ocorrência do dia mencionado
- **"Semana que vem"**: Retorna todas as reuniões de segunda a domingo da próxima semana
- **Datas numéricas**: Entende "dia 15" ou só "15" (pega do próximo mês se já passou)
- **Formato DD/MM**: Interpreta como 15º dia do 12º mês (dezembro), com fallback para próximo ano se já passou
- **Acentos**: Tolera variações com ou sem acentos (segunda, segunda, segunda-feira)

---

O JARVIS é robusto contra erros de transcrição do Google Speech:

- **Substring matching**: Se você disser "abrir r" e existe um comando "abrir reunião", ele encontra
- **Fuzzy matching**: Se disser "arbir reunão" (com erros), ele encontra a correspondência mais próxima (similaridade > 50%)
- **Exceção de segurança**: Comando "desligar computador" exige match EXATO — não pode ser ativado acidentalmente

Exemplos de frases que funcionam:
- "Jarvis, abrr reuião" → encontra "abrir reunião" (fuzzy)
- "Jarvis, volu 5" → encontra "volume 5" (fuzzy)
- "Jarvis, que h sao" → encontra "que horas sao" (fuzzy)
- "Jarvis, deslgar" → NÃO funciona para "desligar computador" (requer match exato)

### Passo 1 - Instalar Python 3.12+

Baixe em [python.org](https://www.python.org/downloads/). Marque **"Add Python to PATH"**.

### Passo 2 - Instalar dependencias

```bash
pip install -r requirements.txt
```

### Passo 3 - Diagnostico do microfone (opcional)

Se o microfone padrão não funcionar, configure `AUDIO_DEVICE` em `src/jarvis/app.py` (linha ~30).

### Passo 4 - Iniciar

```bash
python scripts/run.py
```

Ou via launchers:
- **Windows com console**: `scripts/run.bat`
- **Windows silencioso**: `scripts/run_hidden.vbs`

### Passo 5 - Usar

Diga tudo numa frase so: **"Jarvis, entrar em daily"**

- Ele responde por voz e executa a acao
- Se disser apenas **"Jarvis"**, ele responde *"Sim, senhor?"* e aguarda a proxima frase
- Frases sem "Jarvis" sao ignoradas (pode conversar normalmente no ambiente)

Para encerrar: `Ctrl+C` ou diga **"Jarvis, desligar"**

---

## Configuracoes do Assistente

Definidas em `src/jarvis/app.py` (linhas ~26-40):

| Parametro          | Valor Padrao             | Descricao                                    |
|--------------------|--------------------------|----------------------------------------------|
| `AUDIO_DEVICE`      | `None`                   | Indice do microfone (None = padrao Windows)   |
| `WAKE_WORD`         | `"jarvis"`               | Palavra de ativacao                           |
| `LISTEN_TIMEOUT`    | `10`                     | Segundos aguardando frase                     |
| `PHRASE_TIME_LIMIT` | `8`                      | Duracao maxima da frase capturada             |
| `COMMAND_PAUSE`     | `2`                      | Segundos de silencio para finalizar frase     |
| `LANGUAGE`          | `"pt-BR"`                | Idioma do reconhecimento de voz               |
| `VOICE`             | `"pt-BR-AntonioNeural"`  | Voz do TTS (masculina, neural, brasileira)    |

## Requisitos

- Windows 10/11
- Python 3.12+
- Microfone funcional
- Conexao com internet (Google Speech API + Edge TTS)
