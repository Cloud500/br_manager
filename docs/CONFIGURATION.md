# Konfiguration

## Umgebungsvariablen mit pydantic-settings

Das Projekt verwendet jetzt `pydantic-settings` zur Verwaltung von Umgebungsvariablen. Alle Einstellungen sind in `config/settings/env_config.py` definiert.

### Vorteile:
- **Typsicherheit**: Alle Umgebungsvariablen werden validiert und haben definierte Typen
- **Automatische Validierung**: Pydantic überprüft automatisch die Werte
- **Zentrale Verwaltung**: Alle Umgebungsvariablen an einem Ort
- **Bessere Dokumentation**: Jede Variable hat eine Beschreibung
- **Default-Werte**: Standardwerte sind klar definiert

### Verwendung:

```python
from config.settings.env_config import settings

# Zugriff auf Einstellungen
secret_key = settings.django_secret_key
db_name = settings.db_name
```

### .env Datei:

Kopieren Sie `.env.example` nach `.env` und passen Sie die Werte an:

```bash
cp .env.example .env
```

## Logging mit loguru

Das Projekt verwendet `loguru` für das Logging anstelle des Standard-Python-Logging-Moduls.

### Vorteile:
- **Einfachere API**: Intuitivere Verwendung
- **Farbige Konsolen-Ausgabe**: Bessere Lesbarkeit während der Entwicklung
- **Automatische Rotation**: Log-Dateien werden automatisch rotiert
- **Kompression**: Alte Logs werden automatisch komprimiert
- **Thread-sicher**: Sicheres Logging in Multi-Threading-Umgebungen

### Verwendung:

```python
from loguru import logger

# Einfaches Logging
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")

# Mit Kontext
logger.bind(user_id=123).info("User logged in")

# Exception-Tracking
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")
```

### Konfiguration:

Die Logging-Konfiguration befindet sich in `config/settings/logging_config.py`.

**Einstellbare Parameter:**
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL (Default: INFO)
- `DJANGO_LOG_FILE`: Pfad zur Log-Datei (Default: /var/log/br_manager/django.log)

**Features:**
- Konsolen-Ausgabe: Farbig formatiert für bessere Lesbarkeit
- Datei-Ausgabe: Strukturiert mit automatischer Rotation (10 MB)
- Retention: Logs werden 30 Tage aufbewahrt
- Kompression: Alte Logs werden als ZIP archiviert

## Migration von bestehendem Code

### Umgebungsvariablen:

**Vorher:**
```python
import os
secret_key = os.environ.get("DJANGO_SECRET_KEY", "default")
```

**Nachher:**
```python
from config.settings.env_config import settings
secret_key = settings.django_secret_key
```

### Logging:

**Vorher:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message")
```

**Nachher:**
```python
from loguru import logger
logger.info("Message")
```
