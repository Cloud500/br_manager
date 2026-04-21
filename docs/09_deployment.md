# 09 – Deployment & Betrieb

## 9.1 Übersicht

Der BR Manager wird als containerisierte Anwendung über Docker bereitgestellt. Dieses Dokument beschreibt die Deployment-Strategie, Infrastruktur-Anforderungen und betriebliche Aspekte.

## 9.2 Umgebungen

| Umgebung | Zweck | Zugang |
|----------|-------|--------|
| **Development** | Lokale Entwicklung | Entwickler (lokal) |
| **Staging** | Test und Abnahme | Entwickler, QA, Product Owner |
| **Production** | Produktivbetrieb | Endbenutzer |

### Umgebungsspezifische Konfiguration

Die Konfiguration erfolgt über Umgebungsvariablen (12-Factor-App-Prinzip):

```env
# .env.example
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<random-secret>
DEBUG=False
ALLOWED_HOSTS=brmanager.example.com

# Datenbank
DATABASE_URL=postgres://user:password@db:5432/br_manager

# Redis
REDIS_URL=redis://redis:6379/0

# E-Mail
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=<smtp-password>

# OAuth2
OAUTH2_CLIENT_ID=<client-id>
OAUTH2_CLIENT_SECRET=<client-secret>
OAUTH2_AUTHORIZATION_URL=https://idp.example.com/authorize
OAUTH2_TOKEN_URL=https://idp.example.com/token

# Dateispeicher
AWS_S3_ENDPOINT_URL=https://s3.example.com
AWS_STORAGE_BUCKET_NAME=br-manager-docs
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>

# Sicherheit
CSRF_TRUSTED_ORIGINS=https://brmanager.example.com
```

## 9.3 Docker-Konfiguration

### 9.3.1 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/ssl:/etc/nginx/ssl:ro
      - static_files:/var/www/static:ro
    depends_on:
      - django
    restart: always

  django:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120
    env_file:
      - .env
    volumes:
      - static_files:/app/static
      - media_files:/app/media
    depends_on:
      - db
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: celery -A config worker -l info --concurrency=2
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: always

  celery-beat:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file:
      - .env
    depends_on:
      - db
      - redis
    restart: always

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: br_manager
      POSTGRES_USER: br_manager
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    secrets:
      - db_password
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U br_manager"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: always

volumes:
  postgres_data:
  redis_data:
  static_files:
  media_files:

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### 9.3.2 Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .

# Static files
RUN python manage.py collectstatic --noinput

# Non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000
```

### 9.3.3 Nginx-Konfiguration

```nginx
# docker/nginx.conf (Auszug)
server {
    listen 80;
    server_name brmanager.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name brmanager.example.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols       TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # Static Files (von collectstatic gesammelt)
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media Files (hochgeladene Dokumente)
    location /media/ {
        alias /var/www/media/;
        expires 7d;
    }

    # Login Rate Limiting
    location /accounts/login/ {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Alle Requests an Django weiterleiten
    location / {
        limit_req zone=general burst=20 nodelay;
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Upload Limit
    client_max_body_size 50M;
}
```

## 9.4 CI/CD-Pipeline

### 9.4.1 Pipeline-Übersicht

```
Code Push / Pull Request
         │
         ▼
┌────────────────────┐
│ 1. Lint & Format   │  Python: ruff, black, isort
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ 2. Unit Tests      │  pytest + coverage
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ 3. Security Scans  │  SAST: bandit
│                    │  Dependencies: safety
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ 4. Integration     │  Tests gegen Test-DB
│    Tests           │  
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ 5. Build           │  Docker Image bauen
│                    │  collectstatic
└────────┬───────────┘
         │
         ▼ (nur main/release Branch)
┌────────────────────┐
│ 6. Deploy Staging  │  Automatisches Deployment
└────────┬───────────┘
         │
         ▼ (manueller Trigger)
┌────────────────────┐
│ 7. Deploy Prod     │  Manuelles Deployment
└────────────────────┘
```

### 9.4.2 GitHub Actions Beispiel

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install ruff black isort
      - run: ruff check .
      - run: black --check .
      - run: isort --check .

  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements/test.txt
      - run: pytest --cov=apps --cov-report=xml
        env:
          DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit safety
      - run: bandit -r apps/
      - run: safety check -r requirements/production.txt

  deploy-staging:
    needs: [lint, test-backend, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.prod.yml build
      - run: echo "Deploy to staging..."
```

## 9.5 Monitoring & Observability

### 9.5.1 Metriken (Prometheus + Grafana)

| Metrik | Beschreibung | Alert-Schwellwert |
|--------|-------------|-------------------|
| HTTP Response Time (p95) | 95. Perzentil der Antwortzeit | > 2 Sekunden |
| HTTP Error Rate (5xx) | Anteil der 5xx-Fehler | > 1 % |
| CPU-Auslastung | Container CPU Usage | > 80 % |
| Speicher-Auslastung | Container Memory Usage | > 85 % |
| Datenbank-Verbindungen | Aktive PostgreSQL-Connections | > 80 % des Pools |
| Celery Queue Length | Wartende Tasks in der Queue | > 100 |
| Disk Usage | Festplattennutzung | > 85 % |
| SSL-Zertifikat Ablauf | Tage bis Zertifikatsablauf | < 30 Tage |

### 9.5.2 Logging

- **Anwendungslogs:** JSON-formatiert, strukturiert mit Request-ID für Tracing (Django Logging).
- **Access-Logs:** Nginx Access Logs für Traffic-Analyse.
- **Audit-Logs:** Separate Datenbanktabelle für unveränderliche Audit-Daten.
- **Error-Tracking:** Sentry-Integration für Echtzeit-Fehlerbenachrichtigungen (optional).
- **Log-Rotation:** Über Logrotate oder Docker-eigene Log-Rotation.

### 9.5.3 Health Checks

```
GET /health/              → System-Gesamtstatus
GET /health/db/           → Datenbank-Verbindung
GET /health/redis/        → Redis-Verbindung (falls aktiv)
GET /health/celery/       → Celery-Worker-Status (falls aktiv)
GET /health/storage/      → Dateispeicher-Verfügbarkeit
```

## 9.6 Skalierung

### 9.6.1 Horizontale Skalierung

```yaml
# Beispiel: Skalierung der Django-Worker
docker compose -f docker-compose.prod.yml up --scale django=3
```

- **Nginx:** Load Balancing über upstream-Block.
- **Django:** Mehrere Gunicorn-Worker-Container.
- **Celery:** Separate Worker für verschiedene Queues (email, pdf, default).
- **Redis:** Cluster-Modus bei Bedarf.

### 9.6.2 Ressourcen-Empfehlungen

| Komponente | CPU | RAM | Speicher | Für ~50 Benutzer |
|-----------|-----|-----|----------|-------------------|
| Nginx | 1 Core | 512 MB | 1 GB | 1 Instanz |
| Django (Gunicorn) | 2 Cores | 1 GB | 5 GB | 2 Worker |
| Celery Worker | 1 Core | 512 MB | 1 GB | 1 Instanz |
| Celery Beat | 0.5 Core | 256 MB | 500 MB | 1 Instanz |
| PostgreSQL | 2 Cores | 2 GB | 20 GB | 1 Instanz |
| Redis | 1 Core | 512 MB | 1 GB | 1 Instanz |
| **Gesamt** | **~7.5 Cores** | **~4.8 GB** | **~28.5 GB** | – |

## 9.7 Datenbank-Management

### 9.7.1 Migrationen

```bash
# Migrationen erstellen
python manage.py makemigrations

# Migrationen anwenden (im Deployment-Prozess)
python manage.py migrate --noinput

# Migrationsstatus prüfen
python manage.py showmigrations
```

**Deployment-Reihenfolge:**

1. Datenbank-Migrationen ausführen
2. Static Files sammeln
3. Neue Container starten
4. Health Check bestätigen
5. Alte Container stoppen

### 9.7.2 Backup-Automatisierung

```bash
# Tägliches Backup (als Celery-Beat-Task oder Cron)
pg_dump -U br_manager -Fc br_manager | \
  gpg --encrypt --recipient backup@example.com | \
  aws s3 cp - s3://br-manager-backups/$(date +%Y%m%d).dump.gpg
```

## 9.8 Wartung & Updates

### 9.8.1 Update-Prozess

1. **Vorbereitung:**
   - Changelog prüfen
   - Backup erstellen
   - Staging-Deployment und -Test

2. **Deployment:**
   - Wartungsfenster kommunizieren (bei Breaking Changes)
   - Zero-Downtime-Deployment über Rolling Updates
   - Migrationen ausführen
   - Neue Container deployen

3. **Verifizierung:**
   - Health Checks bestätigen
   - Smoke Tests durchführen
   - Monitoring prüfen

4. **Rollback-Plan:**
   - Vorherige Docker-Images bleiben verfügbar
   - Datenbank-Rollback über reversible Migrationen
   - Schneller Rollback: `docker compose up -d --force-recreate` mit vorherigem Image-Tag

### 9.8.2 Wartungsplan

| Aufgabe | Frequenz |
|---------|----------|
| Security-Updates (OS, Dependencies) | Wöchentlich / bei Bedarf |
| Feature-Releases | Monatlich (Sprint-Zyklus) |
| Datenbank-Wartung (VACUUM, REINDEX) | Wöchentlich (automatisiert) |
| SSL-Zertifikat-Erneuerung | Automatisch (Let's Encrypt / Cert-Manager) |
| Log-Rotation | Täglich |
| Backup-Verifizierung | Monatlich |
| Disaster-Recovery-Test | Quartalsweise |
| Penetrationstest | Jährlich |

## 9.9 Lokale Entwicklungsumgebung

### 9.9.1 Schnellstart

```bash
# Repository klonen
git clone https://github.com/example/br-manager.git
cd br-manager

# Backend Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements/development.txt
cp .env.example .env.development

# Datenbank starten (Docker)
docker compose -f docker-compose.dev.yml up -d db redis

# Migrationen und Testdaten
python manage.py migrate
python manage.py loaddata initial_data

# Entwicklungsserver starten
python manage.py runserver
```

### 9.9.2 Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: br_manager_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
    volumes:
      - dev_postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web-UI

volumes:
  dev_postgres_data:
```
