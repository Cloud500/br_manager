# App: `documents` - Dokumentenmanagementsystem (DMS)

## Übersicht

Zentrale Dokumentenverwaltung mit Versionierung, Zugriffssteuerung, Volltextsuche und Gastzugriff.

## Hauptfunktionen

- Upload, Download, Vorschau, Versionierung
- **Zugriffsebenen:** PUBLIC, COMMITTEE, RESTRICTED, CONFIDENTIAL
- **Externe Ausschussmitglieder:** Nur Zugriff auf Ausschuss-Dokumente
- **Gastzugriff:** Zeitbegrenzt mit Ablaufdatum
- Ordnerstruktur, Tags, Volltextsuche
- Verknüpfungen: TOPs, Protokolle, Beschlüsse, Personelle Maßnahmen

## Datenmodell

### Document
- `id`, `title`, `description`, `folder` (FK), `committee` (FK)
- `current_version`, `access_level`, `file_type`, `file_size`
- `uploaded_by`, `created_at`, `updated_at`, `is_archived`

### DocumentVersion
- `id`, `document` (FK), `version_number`, `file` (FileField)
- `uploaded_by`, `uploaded_at`, `change_description`, `checksum` (SHA-256)

### Folder
- Hierarchische Ordner-Struktur

### DocumentAccess (Gastzugriff)
- `document`, `granted_to`, `valid_from`, `valid_until`, `access_token`, `is_revoked`

### DocumentLink (Generische Verknüpfungen)
- `document`, `linked_object_type`, `linked_object_id`, `linked_by`
- Typen: AGENDA_ITEM, MINUTES, RESOLUTION, PERSONNEL_MEASURE

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/documents/` | Alle Dokumente |
| `/documents/upload/` | Upload |
| `/documents/<uuid:id>/` | Details |
| `/documents/<uuid:id>/download/` | Download |
| `/documents/<uuid:id>/preview/` | Vorschau |
| `/documents/<uuid:id>/share/` | Gastzugriff gewähren |
| `/documents/folders/` | Ordner verwalten |

### HTMX
- `/documents/search/` - Live-Suche
- `/documents/<uuid:id>/upload-progress/` - Upload-Fortschritt

## Abhängigkeiten

- **accounts** (User)
- **committees** (Committee, Membership für Zugriffskontrolle)
- ClamAV (Virus-Scan, optional)

## Berechtigungen

- `document.upload`, `document.view_committee`, `document.view_restricted`, `document.view_confidential`
- `document.edit_own`, `document.edit_all`, `document.manage_access`, `document.manage_folders`

## Implementierungshinweise

### Zugriffskontrolle
```python
def can_access_document(user, document):
    if document.access_level == 'PUBLIC':
        # Gremiumsmitglied?
        return Membership.objects.filter(
            user=user, committee=document.committee, is_active=True
        ).exists()
    
    elif document.access_level == 'CONFIDENTIAL':
        # Nur Vorsitz
        return Membership.objects.filter(
            user=user, committee=document.committee,
            role__codename__in=['CHAIR', 'VICE_CHAIR']
        ).exists()
    
    # Externe Ausschussmitglieder: nur Ausschuss-Docs
    membership = Membership.objects.filter(user=user, committee=document.committee).first()
    if membership and membership.member_type == 'EXTERNAL':
        return document.committee == membership.committee
    
    return False
```

### Virus-Scan
```python
import pyclamd
def scan_uploaded_file(file):
    cd = pyclamd.ClamdUnixSocket()
    result = cd.scan_stream(file.read())
    if result:
        raise ValidationError("Virus detected!")
```
