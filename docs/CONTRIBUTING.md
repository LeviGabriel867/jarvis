# Contributing to JARVIS

## Project Structure

```
jarvis/
├── Jarvis.bat               # Main launcher (double-click to start)
├── Jarvis.pyw               # Python entry point (no console)
├── src/jarvis/              # Main package
│   ├── __init__.py
│   ├── app.py              # Voice assistant application
│   └── calendar.py         # Google Calendar integration
├── config/                  # Configuration files
│   ├── commands.json       # Command definitions
│   ├── config.json         # Settings
│   ├── config.example.json # Configuration template
│   └── credentials/        # OAuth2 credentials (not in git)
├── docs/                    # Documentation
├── README.md               # Project documentation
├── requirements.txt        # Python dependencies
└── setup.py               # Package configuration
```

## Setting Up Development Environment

1. **Clone the repository**
   ```bash
   git clone <repository>
   cd jarvis
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google Calendar (optional)**
   - Create credentials at https://console.cloud.google.com
   - Place `credentials.json` in `config/credentials/`
   - First run will authenticate via browser

## Running the Application

### Option 1: Double-click launcher
Double-click `Jarvis.bat` in the project root.

### Option 2: Python (no console)
```bash
python Jarvis.pyw
```

### List available commands
```bash
python -c "import sys; sys.path.insert(0,'src'); from jarvis.app import main; sys.argv.append('--listar'); main()"
```

## Adding New Commands

Edit `config/commands.json`:

```json
{
  "tipo": "saudacao",
  "triggers": ["your trigger phrases"],
  "descricao": "Description of the command",
  "respostas": [
    "Response option 1",
    "Response option 2"
  ]
}
```

Command types available:
- `saudacao` - greeting responses
- `abrir_url` - open URL in browser
- `proxima_reuniao` - next meeting from calendar
- `listar_reunioes_hoje` - list today's meetings
- `reunioes_data` - meetings for a specific date
- `fechar_programa` - close application by process name
- `volume` - adjust system volume
- `bloquear_pc` - lock computer
- `desligar_pc` - shutdown computer
- `hora` - speak current time
- `data` - speak current date
- `desligar` - stop JARVIS

## Code Style

- Use Python 3.12+
- Follow PEP 8 guidelines
- Use type hints where applicable
- Document complex functions

## Reporting Issues

When reporting issues, include:
- Python version: `python --version`
- Operating System
- Error message/logs
- Steps to reproduce

## License

MIT License
