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

## ✨ Features

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
├── requirements/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
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

# Docker-Container starten
docker compose -f docker/docker-compose.yml up -d

# Datenbank-Migrationen ausführen
docker compose -f docker/docker-compose.yml exec web python manage.py migrate

# Superuser erstellen
docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser
```

### 💻 Lokale Entwicklung

```bash
# Repository klonen
git clone <repository-url>
cd br_manager

# Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Abhängigkeiten installieren
pip install -r requirements/development.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env        # Anpassen nach Bedarf

# Datenbank-Migrationen
python manage.py migrate

# Entwicklungsserver starten
python manage.py runserver
```

> 💡 **Tipp:** Die Anwendung ist dann unter `http://localhost:8000` erreichbar.

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

> 📚 Implementierungsleitfäden befinden sich unter [`docs/implementation/`](docs/implementation/00_uebersicht.md)

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
