# App: `minutes` - Protokollverwaltung

## Übersicht

Rechtssichere Protokollerstellung mit digitalem Unterschriften-Workflow, Versionierung und Freigabeprozess gemäß § 34 BetrVG.

## Hauptfunktionen

### 1. Protokollerstellung
- **Sitzungsmetadaten:** Start/Endzeit, Sitzungsart, Anwesenheit
- **TOP-basiert:** Notizen pro Tagesordnungspunkt (Rich-Text-Editor)
- **Auto-Übernahme:** TOPs, Anwesenheit, Beschlüsse automatisch integriert
- **Autosave:** Periodisches Speichern während Bearbeitung

### 2. Freigabe-Workflow
```
Entwurf → Protokollführung unterschreibt → Vorsitz unterschreibt → 
Vorläufig genehmigt → Sitzungsbeschluss → Finalisiert
```

### 3. Digitale Unterschriften
- **Kryptographische Signatur:** SHA-256-Hash (Inhalt + User-ID + Zeitstempel)
- **Felder:** signed_by_clerk, signed_by_chair + Zeitstempel + Signature-Hash
- **Unveränderlichkeit:** Nach Finalisierung schreibgeschützt

### 4. Versionierung
- Jede Speicherung = neue Version
- Diff-Ansicht zwischen Versionen
- Änderungsprotokoll (wer, wann, was)
- Wiederherstellung älterer Versionen (nur vor Finalisierung)

### 5. PDF-Export
- WeasyPrint oder xhtml2pdf
- Vollständiges Protokoll mit Unterschriften

## Datenmodell

### Minutes
- `id`, `meeting` (OneToOne → Meeting), `content` (TextField, HTML/JSON)
- `status` (DRAFT, CLERK_SIGNED, CHAIR_SIGNED, PRELIMINARILY_APPROVED, FINALIZED, REVISION_REQUIRED)
- `version` (IntegerField), `author` (FK → User)
- `signed_by_clerk`, `signed_by_clerk_at`, `clerk_signature_hash`
- `signed_by_chair`, `signed_by_chair_at`, `chair_signature_hash`
- `finalized_at`, `finalized_in_meeting` (FK → Meeting)

### MinutesVersion
- Snapshots aller Versionen: `version_number`, `content`, `changed_by`, `changed_at`, `change_description`

### MinutesItem
- TOP-spezifische Protokolleinträge: `minutes`, `agenda_item`, `content`, `position`

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/meetings/<uuid:id>/minutes/` | Protokoll anzeigen |
| `/meetings/<uuid:id>/minutes/create/` | Erstellen |
| `/minutes/<uuid:id>/edit/` | Bearbeiten |
| `/minutes/<uuid:id>/sign/clerk/` | Unterschrift Protokollführung |
| `/minutes/<uuid:id>/sign/chair/` | Unterschrift Vorsitz |
| `/minutes/<uuid:id>/finalize/` | Finalisieren |
| `/minutes/<uuid:id>/versions/` | Versionshistorie |
| `/minutes/<uuid:id>/diff/<v1>/<v2>/` | Diff-Ansicht |
| `/minutes/<uuid:id>/export/pdf/` | PDF-Export |

### HTMX
- `/minutes/<uuid:id>/autosave/` - Auto-Save
- `/minutes/<uuid:id>/preview/` - Live-Vorschau

## Abhängigkeiten

- **meetings** (Meeting)
- **agendas** (AgendaItem)
- **attendance** (AttendanceRecord für Anwesenheitsliste)
- **resolutions** (Resolution für Beschlüsse)
- **accounts** (User)

## Berechtigungen

- `minutes.create`, `minutes.edit`, `minutes.sign`
- `minutes.reject`, `minutes.finalize`
- `minutes.view`, `minutes.view_versions`, `minutes.export_pdf`

## Templates

- `minutes/minutes_detail.html`
- `minutes/minutes_form.html` (Rich-Text-Editor: CKEditor/TinyMCE)
- `minutes/minutes_versions.html`
- `minutes/minutes_diff.html`

## Implementierungshinweise

### Digitale Unterschrift
```python
def sign_protocol(minutes, user, role):  # role = 'clerk' or 'chair'
    import hashlib
    from django.utils import timezone
    
    timestamp = timezone.now()
    signature_data = f"{minutes.id}{minutes.content}{user.id}{timestamp.isoformat()}"
    signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
    
    if role == 'clerk':
        minutes.signed_by_clerk = user
        minutes.signed_by_clerk_at = timestamp
        minutes.clerk_signature_hash = signature_hash
        minutes.status = 'CLERK_SIGNED'
    elif role == 'chair':
        minutes.signed_by_chair = user
        minutes.signed_by_chair_at = timestamp
        minutes.chair_signature_hash = signature_hash
        minutes.status = 'CHAIR_SIGNED'
        # Beide unterschrieben → vorläufig genehmigt
        if minutes.signed_by_clerk:
            minutes.status = 'PRELIMINARILY_APPROVED'
    
    minutes.save()
```

### Automatische TOP-Erstellung für nächste Sitzung
Nach vorläufiger Genehmigung automatisch TOP "Genehmigung Protokoll vom [Datum]" auf nächste Sitzung setzen.

## Tests

- Unit-Tests für Signatur-Generierung
- Integration-Tests für Workflow
- Versionierungs-Tests
- PDF-Export-Tests
