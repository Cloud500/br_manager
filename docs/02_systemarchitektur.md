# 02 – Systemarchitektur

## 2.1 Architekturübersicht

Der BR Manager ist als **Django-Monolith** konzipiert – eine einheitliche Anwendung, die Frontend und Backend in einem System vereint. Die Benutzeroberfläche wird serverseitig über Django Templates gerendert und durch **HTMX** und **Alpine.js** um dynamische Interaktivität erweitert. Für spezielle Widgets (Kalender, Rich-Text-Editor) werden punktuell JavaScript-Bibliotheken eingebunden.

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (Browser)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │   Django Templates + HTMX + Alpine.js                  ││
│  │   (Server-Side Rendering mit dynamischer Interaktion)  ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────┴──────────────────────────────────┐
│                     Reverse Proxy (Nginx)                   │
│              SSL-Terminierung, Static Files, Rate Limiting  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│              Django Monolith (Gunicorn/WSGI)                │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Django   │ │ Views &  │ │ Auth &   │ │ Template      │  │
│  │ ORM      │ │ Business │ │ Sessions │ │ Engine        │  │
│  │          │ │ Logic    │ │ & RBAC   │ │ + HTMX        │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Audit-   │ │ Formular-│ │ Benach-  │ │ Dokumenten-   │  │
│  │ Logging  │ │ system   │ │ richtig. │ │ speicher      │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└─────┬──────────────┬─────────────┬──────────────────────────┘
      │              │             │
      ▼              ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │  │  Celery  │
│(Daten)   │  │ (Cache/  │  │ (Async   │
│          │  │ Sessions)│  │  Tasks)  │
└──────────┘  └──────────┘  └──────────┘
                optional       optional
```

### Vorteile der monolithischen Architektur

| Vorteil | Beschreibung |
|---------|-------------|
| **Einfachheit** | Ein Projekt, ein Deployment, ein Server-Prozess |
| **Djangos Stärken nutzen** | Templates, Forms, Auth, Sessions, CSRF-Schutz – alles integriert |
| **Keine CORS-Probleme** | Frontend und Backend laufen auf derselben Domain |
| **Session-basierte Auth** | Djangos bewährtes Session-System statt JWT-Handling |
| **Schnellere Entwicklung** | Kein separater Build-Prozess, kein Node.js/npm nötig |
| **Einfaches Debugging** | Ein Stack, ein Log, eine Fehlerquelle |
| **Passend für Zielgruppe** | 5–50 Betriebsratsmitglieder – keine SPA-Skalierung nötig |

## 2.2 Technologiestack

### Backend & Frontend (Django Monolith)

| Komponente | Technologie | Version | Begründung |
|-----------|-------------|---------|------------|
| Web-Framework | Django | ≥ 5.x | Bewährtes Python-Framework mit integriertem Auth, ORM, Templates, Forms |
| Template Engine | Django Templates | – | Server-seitiges Rendering, integrierte Sicherheit (Auto-Escaping) |
| Dynamische Interaktion | HTMX | ≥ 2.x | Dynamische UI ohne Full-Page-Reload, minimaler JavaScript-Bedarf |
| Leichtgewichtiges JS | Alpine.js | ≥ 3.x | Reaktive UI-Komponenten direkt im HTML (Dropdowns, Tabs, Modals) |
| CSS-Framework | Bootstrap 5 / Tailwind CSS | – | Responsives Design, konsistente UI-Komponenten |
| Datenbank | PostgreSQL | ≥ 16 | ACID-konform, JSON-Support, Volltextsuche, Row-Level Security |
| Cache / Sessions | Redis (optional) | ≥ 7.x | In-Memory-Cache für Sessions und häufige Abfragen; alternativ DB-Cache |
| Task Queue | Celery + Redis (optional) | ≥ 5.x | Asynchrone Verarbeitung (E-Mails, PDF-Generierung) |
| Authentication | django-allauth | – | SSO-Anbindung, OAuth2, Social Auth |
| 2FA | django-otp / pyotp | – | Zwei-Faktor-Authentifizierung für Anwesenheitsbestätigung |
| Dokumentenspeicher | Django FileField / S3-kompatibler Speicher | – | Lokale Dateispeicherung oder S3 für größere Installationen |
| Rich Text Editor | django-ckeditor / TinyMCE | – | WYSIWYG-Editor für Protokollerstellung in Templates |
| Kalender | FullCalendar (JS-Bibliothek) | – | Kalender-Widget, eingebunden in Django Templates |
| PDF-Generierung | WeasyPrint / xhtml2pdf | – | PDF-Erstellung aus Django Templates |
| Formulare | Django Forms / Crispy Forms | – | Serverseitige Validierung mit Template-Rendering |

### Infrastruktur

| Komponente | Technologie | Begründung |
|-----------|-------------|------------|
| Containerisierung | Docker + Docker Compose | Reproduzierbare Umgebungen |
| Reverse Proxy | Nginx | SSL-Terminierung, Static Files, Rate Limiting |
| WSGI-Server | Gunicorn | Produktions-tauglicher Python-WSGI-Server |
| CI/CD | GitHub Actions / GitLab CI | Automatisierte Tests und Deployments |
| Monitoring | Prometheus + Grafana (optional) | Metriken und Alerting |
| Logging | Django Logging + Logrotate | Einfaches, effektives Log-Management |
| Backup | pg_dump + lokaler/S3-Speicher | Automatisierte Datenbank-Backups |

## 2.3 Projektstruktur

```
br_manager/
├── manage.py
├── config/                     # Projektkonfiguration
│   ├── settings/
│   │   ├── base.py             # Gemeinsame Einstellungen
│   │   ├── development.py      # Entwicklungsumgebung
│   │   ├── production.py       # Produktionsumgebung
│   │   └── test.py             # Testumgebung
│   ├── urls.py                 # Root-URL-Konfiguration
│   ├── wsgi.py
│   └── celery.py               # Celery-Konfiguration (optional)
├── apps/
│   ├── accounts/               # Benutzerverwaltung & Authentifizierung
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py            # Django Forms
│   │   ├── urls.py
│   │   └── ...
│   ├── committees/             # Gremien- & Ausschussverwaltung
│   ├── agendas/                # Tagesordnungsverwaltung
│   ├── minutes/                # Protokollverwaltung
│   ├── attendance/             # Anwesenheitsverwaltung
│   ├── documents/              # Dokumentenmanagementsystem
│   ├── resolutions/            # Beschluss- & Abstimmungssystem
│   ├── calendar_mgmt/          # Kalenderintegration
│   ├── notifications/          # Benachrichtigungssystem
│   ├── roles/                  # Dynamische Rollen- & Rechteverwaltung
│   └── audit/                  # Audit-Logging
├── templates/                  # Globale Django Templates
│   ├── base.html               # Basis-Template (Layout, Navigation, HTMX-Einbindung)
│   ├── components/             # Wiederverwendbare Template-Fragmente
│   │   ├── _navbar.html
│   │   ├── _sidebar.html
│   │   ├── _modal.html
│   │   ├── _pagination.html
│   │   └── _messages.html
│   ├── accounts/               # Account-Templates
│   ├── agendas/                # Tagesordnungs-Templates
│   ├── minutes/                # Protokoll-Templates
│   ├── attendance/             # Anwesenheits-Templates
│   ├── documents/              # Dokumenten-Templates
│   ├── resolutions/            # Beschluss-Templates
│   ├── committees/             # Ausschuss-Templates
│   ├── calendar_mgmt/          # Kalender-Templates
│   ├── roles/                  # Rollen-Templates
│   └── emails/                 # E-Mail-Templates
├── static/                     # Statische Dateien
│   ├── css/                    # Eigene Stylesheets
│   ├── js/                     # Eigene JavaScript-Dateien
│   │   ├── htmx.min.js         # HTMX-Bibliothek
│   │   ├── alpine.min.js       # Alpine.js-Bibliothek
│   │   └── app.js              # Projektspezifisches JS (minimal)
│   ├── vendor/                 # Drittanbieter-Assets (FullCalendar, CKEditor etc.)
│   └── img/                    # Bilder und Icons
├── media/                      # Hochgeladene Dateien
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
└── docs/                       # Projektdokumentation
```

## 2.4 HTMX-Integrationsmuster

HTMX ermöglicht dynamische Interaktionen, ohne eine vollständige SPA zu entwickeln. Die Kommunikation erfolgt über **HTML-Fragmente** statt JSON:

### Prinzip

```
Benutzer-Aktion (Klick, Submit)
         │
         ▼ (HTMX-Request: AJAX mit HTML-Antwort)
┌────────────────────┐
│  Django View       │
│  - Logik ausführen │
│  - Template-       │
│    Fragment rendern │
└────────┬───────────┘
         │
         ▼ (HTML-Fragment)
┌────────────────────┐
│  Browser           │
│  - DOM-Element     │
│    ersetzen/       │
│    ergänzen        │
└────────────────────┘
```

### Typische Anwendungsfälle

| Anwendungsfall | HTMX-Attribut | Beschreibung |
|---------------|---------------|-------------|
| Formular absenden ohne Reload | `hx-post` | Formular wird per AJAX gesendet, Antwort ersetzt Bereich |
| Inline-Bearbeitung | `hx-get` + `hx-swap` | Klick auf Element lädt Bearbeitungsformular |
| Suchfeld mit Live-Ergebnissen | `hx-get` + `hx-trigger="keyup"` | Suchergebnisse werden live nachgeladen |
| Modale Dialoge | `hx-get` + `hx-target="#modal"` | Modal-Inhalt wird vom Server geladen |
| Tabellenzeilen löschen | `hx-delete` + `hx-swap="outerHTML"` | Zeile wird entfernt ohne Seitenreload |
| Unendliches Scrollen | `hx-get` + `hx-trigger="revealed"` | Weitere Einträge werden beim Scrollen geladen |
| Abstimmung | `hx-post` | Abstimmungsergebnis wird live aktualisiert |

### Beispiel: Tagesordnungspunkt inline bearbeiten

```html
<!-- Template: agendas/agenda_detail.html -->
<div id="item-{{ item.id }}">
  <h3>{{ item.title }}</h3>
  <p>{{ item.description }}</p>
  <button hx-get="{% url 'agendas:item-edit' item.id %}"
          hx-target="#item-{{ item.id }}"
          hx-swap="outerHTML"
          class="btn btn-sm btn-outline-primary">
    Bearbeiten
  </button>
</div>
```

```python
# views.py
def agenda_item_edit(request, item_id):
    item = get_object_or_404(AgendaItem, id=item_id)
    if request.method == 'POST':
        form = AgendaItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return render(request, 'agendas/_item_row.html', {'item': item})
    else:
        form = AgendaItemForm(instance=item)
    return render(request, 'agendas/_item_edit_form.html', {'form': form, 'item': item})
```

## 2.5 Alpine.js-Integrationsmuster

Alpine.js wird für **clientseitige Interaktivität** eingesetzt, die keinen Serveraufruf erfordert:

| Anwendungsfall | Beschreibung |
|---------------|-------------|
| Dropdowns / Menüs | Auf-/Zuklappen ohne Server-Request |
| Tabs | Tab-Wechsel rein clientseitig |
| Modale Dialoge (einfach) | Öffnen/Schließen eines Modals |
| Formular-Validierung (clientseitig) | Sofortige Rückmeldung bei Eingaben |
| Toggle-Elemente | Sichtbarkeit von Bereichen steuern |
| Zähler / Counter | Abstimmungszähler clientseitig aktualisieren |

### Beispiel: Dropdown-Menü

```html
<div x-data="{ open: false }" class="relative">
  <button @click="open = !open" class="btn btn-primary">
    Aktionen <span x-text="open ? '▲' : '▼'"></span>
  </button>
  <div x-show="open" @click.outside="open = false" class="dropdown-menu">
    <a href="#" class="dropdown-item">Bearbeiten</a>
    <a href="#" class="dropdown-item">Duplizieren</a>
    <a href="#" class="dropdown-item text-danger">Löschen</a>
  </div>
</div>
```

## 2.6 Kommunikation zwischen Komponenten

### Request-Verarbeitung

- **Protokoll:** HTTPS (TLS 1.3)
- **Rendering:** Server-Side Rendering (Django Templates)
- **Dynamik:** HTMX für partielle Seitenupdates (HTML-Fragmente statt JSON)
- **Authentifizierung:** Django Sessions (Cookie-basiert, CSRF-geschützt)
- **Formulare:** Django Forms mit serverseitiger Validierung

### Asynchrone Verarbeitung (optional)

Zeitintensive Aufgaben werden über **Celery** asynchron verarbeitet:

- E-Mail-Versand (Einladungen, Benachrichtigungen)
- PDF-Generierung (Protokolle, Tagesordnungen)
- Dokumentenkonvertierung
- Geplante Aufgaben (z. B. automatische Tagesordnungspunkte für nächste Sitzung)

Falls kein Redis/Celery gewünscht ist, können diese Aufgaben auch **synchron** im Request-Zyklus verarbeitet werden (für kleine Installationen ausreichend).

### WebSocket (optional, Phase 2)

- Echtzeit-Benachrichtigungen über Django Channels
- Live-Updates während Sitzungen (z. B. Abstimmungsergebnisse)

## 2.7 Skalierbarkeit

Das System ist für eine typische Betriebsratsgröße von 5–50 Mitgliedern ausgelegt. Die monolithische Architektur ist für diese Größe optimal. Bei Bedarf kann skaliert werden durch:

- **Vertikal:** Mehr RAM/CPU für den Django-Server
- **Horizontal:** Mehrere Gunicorn-Worker hinter Nginx
- **Caching:** Redis-Cache für häufig abgefragte Daten (Mitgliederlisten, Berechtigungen) – oder Djangos eingebauter DB-Cache
- **Datenbank:** PostgreSQL Connection Pooling (pgBouncer) bei Bedarf
- **Dateispeicher:** Lokaler Speicher oder S3-kompatibler Object Storage für Dokumente
