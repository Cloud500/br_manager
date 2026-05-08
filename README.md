<div align="center">

# 🏛️ BR Manager

**Digitales Betriebsrats-Management-System**

[![Python](https://img.shields.io/badge/Python-≥3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-≥5.x-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-≥16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![HTMX](https://img.shields.io/badge/HTMX-≥2.x-3366CC?style=for-the-badge&logo=htmx&logoColor=white)](https://htmx.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

[![Status](https://img.shields.io/badge/Status-Work_in_Progress-orange?style=flat-square)](#)
[![Licence](https://img.shields.io/badge/Lizenz-EUPL--1.2-blue?style=flat-square)](#-lizenz)
[![BetrVG](https://img.shields.io/badge/BetrVG-pending-red?style=flat-square)](#-sicherheit--compliance)
[![DSGVO](https://img.shields.io/badge/DSGVO-pending-red?style=flat-square)](#-sicherheit--compliance)

---

Eine webbasierte Anwendung zur umfassenden digitalen Unterstützung der Betriebsratsarbeit – unter vollständiger Einhaltung des **Betriebsverfassungsgesetzes (BetrVG)** und der **Datenschutz-Grundverordnung (DSGVO)**.

[Features](#-features) · [Technologiestack](#%EF%B8%8F-technologiestack) · [Installation](#%EF%B8%8F-installation--setup) · [Dokumentation](#-dokumentation)

> ### ⚠️ Work in Progress
> **Dieses Projekt befindet sich in aktiver Entwicklung und ist noch nicht produktionsreif.**
> Funktionen, APIs und Dokumentation können sich jederzeit ändern. Nutzung auf eigene Gefahr.


</div>

---

## ✨ Geplante Features

<table>
  <tr>
    <td>📋 <b>Sitzungsverwaltung</b></td>
    <td>Online-, Hybrid- und Präsenzsitzungen mit Vorsitz, Protokollführung und Vertretungsregelungen</td>
  </tr>
  <tr>
    <td>📝 <b>Tagesordnungen</b></td>
    <td>Erstellung, Vorlagen, Drag-and-Drop-Sortierung und Status-Workflow</td>
  </tr>
  <tr>
    <td>📄 <b>Protokolle</b></td>
    <td>WYSIWYG-Editor, digitaler Unterschrifts-Workflow, Versionierung und Diff-Ansicht</td>
  </tr>
  <tr>
    <td>✅ <b>Anwesenheit</b></td>
    <td>2FA-gestützte Bestätigung, druckbare Listen, automatische Ersatzmitglieder-Vorschläge nach § 25 BetrVG</td>
  </tr>
  <tr>
    <td>🗳️ <b>Beschlüsse & Abstimmungen</b></td>
    <td>Automatische Beschlussfähigkeitsprüfung, Beschlussnummern, PDF-Versand an Arbeitgeber</td>
  </tr>
  <tr>
    <td>🏆 <b>Wahlen</b></td>
    <td>Dokumentation von Wahlergebnissen (nur bei Präsenzsitzungen)</td>
  </tr>
  <tr>
    <td>📁 <b>Dokumentenmanagement</b></td>
    <td>Versionierung, Volltextsuche, Vorschau, granulare Zugriffssteuerung</td>
  </tr>
  <tr>
    <td>🏢 <b>Ausschussverwaltung</b></td>
    <td>Gremien, Fachausschüsse, Ad-hoc-Ausschüsse mit eigenständigen Bereichen</td>
  </tr>
  <tr>
    <td>🔑 <b>Rollen & Rechte</b></td>
    <td>Konfigurierbare Rollen, Berechtigungsmatrix, Privilege-Escalation-Prevention</td>
  </tr>
  <tr>
    <td>📅 <b>Kalenderintegration</b></td>
    <td>Sitzungskalender, Abwesenheiten, Reisedaten, iCal-Export, Terminkollisionsprüfung</td>
  </tr>
  <tr>
    <td>🔔 <b>Benachrichtigungen</b></td>
    <td>E-Mail und In-App – Einladungen, Erinnerungen, Fristwarnungen, Beschluss-Versand</td>
  </tr>
  <tr>
    <td>☑️ <b>To-Do-Verwaltung</b></td>
    <td>Aufgaben mit Zuordnung, Fälligkeitsdaten, Verknüpfung zu Sitzungen/Beschlüssen</td>
  </tr>
  <tr>
    <td>👤 <b>Personelle Maßnahmen</b></td>
    <td>§§ 99–101 BetrVG, Fristenüberwachung, Status-Workflow, Ergebnisversand</td>
  </tr>
  <tr>
    <td>🔍 <b>Audit-Logging</b></td>
    <td>Lückenlose Protokollierung aller sicherheitsrelevanten Aktionen</td>
  </tr>
</table>

### ✅ Bereits umgesetzt

<table>
  <tr>
    <td>👤 <b>Benutzer & Auth</b></td>
    <td>E-Mail-Login mit Custom User Model, Profil, Passwortänderung, Einladungen/Registrierung, 2FA mit TOTP und Recovery Codes.</td>
  </tr>
  <tr>
    <td>🔑 <b>Rollen & Rechte</b></td>
    <td>Eigenes RBAC-System mit Rollen, Permissions, Rollenverwaltung, Permission-Zuweisung und Seed-Migrationen.</td>
  </tr>
  <tr>
    <td>🏢 <b>Gremien & Ausschüsse</b></td>
    <td>Hauptgremien, Ausschüsse, Mitgliedschaften, Ersatzmitglieder, externe Mitglieder, Soft Delete und Betriebsausschuss-Automatik.</td>
  </tr>
  <tr>
    <td>📋 <b>Sitzungen</b></td>
    <td>CRUD, Sitzungsnummern, Online-/Präsenz-/Hybrid-Validierung, Einladungsversand sowie Workflow von Entwurf bis versenden der Einladungen.</td>
  </tr>
  <tr>
    <td>✅ <b>Teilnehmer</b></td>
    <td>Teilnehmerdatensätze, Hinzufügen/Entfernen, Abwesenheiten, Ersatz-/Teilnehmeraktionen und serverseitige Berechtigungsprüfung.</td>
  </tr>
  <tr>
    <td>📝 <b>Tagesordnungen</b></td>
    <td>Automatisch angelegte Tagesordnungen je Sitzung, reguläre TOPs, Beschluss-TOPs, Nummerierung, Hierarchie und Reordering.</td>
  </tr>
  <tr>
    <td>🗳️ <b>Beschlüsse</b></td>
    <td>Beschlussentwürfe, Vorschlagen, Annehmen/Ablehnen, Beschlussnummern und Verknüpfung mit Beschluss-TOPs.</td>
  </tr>
  <tr>
    <td>🏆 <b>Wahlen</b></td>
    <td>Wahl- und Kandidatenmodelle, Kandidaten-Formsets, CRUD und Veröffentlichung mit serverseitigen Permission-Prüfungen.</td>
  </tr>
  <tr>
    <td>🔔 <b>E-Mail-Vorlagen</b></td>
    <td>CRUD für E-Mail-Vorlagen, HTML-Sanitizing, Text-Extraktion, gerenderte E-Mail-Hilfsdaten und eigene Template-Permission.</td>
  </tr>
  <tr>
    <td>📊 <b>Dashboard</b></td>
    <td>Login-geschütztes Dashboard mit Navigation zu den implementierten Modulen.</td>
  </tr>
</table>

---

## 🏗️ Technologiestack

<details>
<summary><b>Backend & Frontend</b></summary>
<br>

| Komponente | Technologie |
|:---|:---|
| Web-Framework | ![Django](https://img.shields.io/badge/Django-≥5.x-092E20?style=flat-square&logo=django&logoColor=white) |
| Template Engine | Django Templates (Server-Side Rendering) |
| Dynamische Interaktion | ![HTMX](https://img.shields.io/badge/HTMX-≥2.x-3366CC?style=flat-square&logo=htmx&logoColor=white) |
| Client-seitige Reaktivität | ![Alpine.js](https://img.shields.io/badge/Alpine.js-≥3.x-8BC0D0?style=flat-square&logo=alpinedotjs&logoColor=white) |
| CSS-Framework | ![Bootstrap](https://img.shields.io/badge/Bootstrap_5-7952B3?style=flat-square&logo=bootstrap&logoColor=white) / ![Tailwind](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) |
| Datenbank | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-≥16-4169E1?style=flat-square&logo=postgresql&logoColor=white) |
| Cache / Sessions | ![Redis](https://img.shields.io/badge/Redis-≥7.x-DC382D?style=flat-square&logo=redis&logoColor=white) *(optional)* |
| Task Queue | ![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white) + Redis *(optional)* |
| Authentifizierung | django-allauth (OAuth2, SSO) |
| 2FA | django-otp / pyotp |
| Rich-Text-Editor | django-ckeditor / TinyMCE |
| Kalender-Widget | FullCalendar |
| PDF-Generierung | WeasyPrint / xhtml2pdf |

</details>

<details>
<summary><b>Infrastruktur</b></summary>
<br>

| Komponente | Technologie |
|:---|:---|
| Containerisierung | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) + Docker Compose |
| Reverse Proxy | ![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat-square&logo=nginx&logoColor=white) |
| WSGI-Server | ![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=flat-square&logo=gunicorn&logoColor=white) |
| Monitoring | ![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white) + ![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat-square&logo=grafana&logoColor=white) *(optional)* |
| Backup | pg_dump + lokaler/S3-Speicher |

</details>

---

## 📁 Projektstruktur

<details>
<summary><b>Verzeichnisübersicht anzeigen</b></summary>

```
br_manager/
├── manage.py
├── config/                     # Projektkonfiguration
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py               # optional
├── apps/
│   ├── accounts/               # 👤 Benutzerverwaltung & Auth
│   ├── committees/             # 🏢 Gremien & Ausschüsse
│   ├── meetings/               # 📋 Sitzungsverwaltung
│   ├── agendas/                # 📝 Tagesordnungen
│   ├── minutes/                # 📄 Protokolle
│   ├── attendance/             # ✅ Anwesenheit
│   ├── documents/              # 📁 DMS
│   ├── resolutions/            # 🗳️ Beschlüsse & Abstimmungen
│   ├── calendar_mgmt/          # 📅 Kalender
│   ├── notifications/          # 🔔 Benachrichtigungen
│   ├── roles/                  # 🔑 Rollen & Rechte
│   ├── todos/                  # ☑️ To-Dos
│   ├── personnel/              # 👤 Personelle Einzelmaßnahmen
│   └── audit/                  # 🔍 Audit-Logging
├── templates/                  # Globale Django Templates
├── static/                     # CSS, JS, Vendor-Assets
├── media/                      # Hochgeladene Dateien
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
└── docs/                       # Projektdokumentation
```

</details>

---

## 🚀 Voraussetzungen

| Anforderung | Version |
|:---|:---|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) Python | ≥ 3.12 |
| ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) PostgreSQL | ≥ 16 |
| ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) Docker + Compose | empfohlen |
| 🌐 Webbrowser | Chrome, Firefox, Edge, Safari |
| 📧 SMTP-Server | für E-Mail-Benachrichtigungen |
| 🔐 SSL/TLS-Zertifikate | erforderlich |
| 🔑 OAuth2 Identity Provider | z. B. Azure AD, Keycloak |

---

## ⚙️ Installation & Setup

### 🐳 Mit Docker (empfohlen)

```bash
# Repository klonen
git clone <repository-url>
cd br_manager

# Development-Container starten (SQLite, Hot Reload)
docker compose -f docker/docker-compose.dev.yml up --build

# Production-Container starten (PostgreSQL)
cp .env.example .env
# .env anpassen: DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DB_PASSWORD,
# optional DJANGO_CSRF_TRUSTED_ORIGINS, ROOT_USER_EMAIL und ROOT_USER_PASSWORD setzen
docker compose --env-file .env -f docker/docker-compose.prod.yml up -d --build
```

Docker startet die Anwendung als ASGI-App. Development nutzt Uvicorn mit Reload,
Production nutzt Gunicorn als Prozessmanager mit Uvicorn-Worker. Beim Containerstart
läuft automatisch: Datenbank-Verfügbarkeit prüfen, `migrate`, in Production zusätzlich
`collectstatic`, danach optional die initiale Root-User-Erstellung.

Der Development-Container führt nach den Migrationen einmalig `seed_testdata` aus,
solange die Datenbank noch keine Benutzer enthält. Standardmäßig wird
`testdata_config_small.json` verwendet; bei Bedarf kann die Datei über
`DJANGO_SEED_TESTDATA_CONFIG` überschrieben werden.

Wenn `ROOT_USER_EMAIL` und `ROOT_USER_PASSWORD` gesetzt sind, wird ein initialer
Superuser erstellt, sofern die E-Mail-Adresse noch nicht existiert. Existiert die
Adresse bereits, wird kein Passwort überschrieben und ein normaler Benutzer wird nicht
stillschweigend zum Superuser hochgestuft.

> ⚠️ Die Production-Compose bindet Port 8000 nur an `127.0.0.1` und erwartet einen
> TLS-terminierenden Reverse Proxy, der `X-Forwarded-Proto: https` setzt.

> 💡 Development erzeugt seine Admin- und Testbenutzer über `seed_testdata`.
> Für Production müssen initiale Root-User-Werte bewusst über `.env` gesetzt werden.

### 💻 Lokale Entwicklung

```bash
# Repository klonen
git clone <repository-url>
cd br_manager

# Abhängigkeiten für die Entwicklung installieren
uv sync --group dev

# Umgebungsvariablen konfigurieren (lokal nach Bedarf anpassen)
cp .env.example .env

# Datenbank-Migrationen
uv run python manage.py migrate

# Optionale lokale Testdaten erzeugen
uv run python manage.py seed_testdata --clear --config testdata_config_small.json

# Entwicklungsserver starten (ASGI/Uvicorn)
uv run uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --reload
```

> 💡 **Tipp:** Die Anwendung ist dann unter `http://localhost:8000` erreichbar.
> `manage.py` nutzt standardmäßig `config.settings.development`; lokal wird dadurch SQLite (`db.sqlite3`) verwendet.
> Weitere Details zu Testdaten, Konfigurationsdateien und Optionen wie `--no-committees` stehen in [`TESTDATA_CONFIG_README.md`](TESTDATA_CONFIG_README.md).

---

## 🔒 Sicherheit & Compliance

| | Feature | Beschreibung |
|:---:|:---|:---|
| ⚖️ | **BetrVG-konform** | Vollständige Abbildung der gesetzlichen Anforderungen (u. a. §§ 25, 33, 99–101 BetrVG) |
| 🛡️ | **DSGVO-konform** | Datenschutz by Design, Zugangsbeschränkungen, Audit-Fähigkeit |
| 🔐 | **Verschlüsselung** | TLS 1.3 für alle Verbindungen, verschlüsselte Datenspeicherung |
| 🪪 | **Authentifizierung** | OAuth2/SSO, Zwei-Faktor-Authentifizierung |
| 🔍 | **Audit-Logging** | Lückenlose Protokollierung aller sicherheitsrelevanten Aktionen |
| 🔑 | **Berechtigungssystem** | Dynamische, konfigurierbare Rollen mit Privilege-Escalation-Prevention |

---

## 📖 Dokumentation

Die vollständige Projektdokumentation befindet sich im Verzeichnis [`docs/`](docs/README.md):

| | Dokument | Beschreibung |
|:---:|:---|:---|
| 🔭 | [Projektüberblick](docs/01_projektueberblick.md) | Zielsetzung, Stakeholder und Projektumfang |
| 🏗️ | [Systemarchitektur](docs/02_systemarchitektur.md) | Technologiestack, Architektur und Komponenten |
| ⚙️ | [Funktionalitäten](docs/03_funktionalitaeten.md) | Detaillierte Beschreibung aller Module |
| 🗄️ | [Datenmodell](docs/04_datenmodell.md) | Datenbankschema und Entitäten |
| 🔗 | [URL- und View-Konzept](docs/05_api_konzept.md) | Django URL-Routing, Views und HTMX-Fragmente |
| 🔑 | [Berechtigungskonzept](docs/06_berechtigungskonzept.md) | Rollen, Rechte und Zugriffssteuerung |
| ⚖️ | [Rechtliche Rahmenbedingungen](docs/07_rechtliche_rahmenbedingungen.md) | BetrVG- und DSGVO-Konformität |
| 🔒 | [Sicherheitskonzept](docs/08_sicherheitskonzept.md) | Sicherheitsmaßnahmen und Verschlüsselung |

---

## 🎯 Zielgruppe

Das System ist für eine typische Betriebsratsgröße von **5–50 Mitgliedern** ausgelegt und richtet sich an:

- 👔 Betriebsratsvorsitzende und -mitglieder
- 🔄 Ersatzmitglieder
- ✍️ Protokollführung
- 🏢 Ausschussmitglieder (inkl. externe)

---

## 📄 Lizenz

Dieses Projekt ist unter der **European Union Public License 1.2 (EUPL-1.2)** lizenziert – siehe [LICENSE](LICENSE) für Details.

Die EUPL ist eine von der Europäischen Kommission entwickelte Open-Source-Lizenz, kompatibel mit vielen anderen OSS-Lizenzen und in allen EU-Amtssprachen rechtsgültig.

---

## 🤝 Mitwirken

*Contribution-Guidelines folgen.*

---

<div align="center">

**[⬆ Nach oben](#%EF%B8%8F-br-manager)**

Erstellt mit ❤️ für die Betriebsratsarbeit

</div>
