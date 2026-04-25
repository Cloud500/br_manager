# App: `agendas` - Tagesordnungsverwaltung

## Übersicht

Verwaltung von Tagesordnungspunkten (TOPs) für Sitzungen inkl. Vorlagen und Drag-and-Drop-Sortierung.

## Hauptfunktionen

- TOPs hinzufügen, bearbeiten, löschen, umsortieren (Drag & Drop)
- **TOP-Typen:** REGULAR, RESOLUTION, ELECTION, PERSONNEL_MEASURE, PROTOCOL_APPROVAL
- Anhänge an TOPs (Dokumente)
- Tagesordnungsvorlagen erstellen und verwenden
- Automatische TOP-Erstellung (z.B. Protokollgenehmigung)

## Datenmodell

### AgendaItem
- `id`, `meeting` (FK → Meeting), `position`, `title`, `description`
- `item_type` (REGULAR, RESOLUTION, ELECTION, PERSONNEL_MEASURE, PROTOCOL_APPROVAL)
- `duration_minutes`, `presenter` (FK → User)
- `created_by`, `is_auto_generated`
- `related_minutes` (FK → Minutes, für PROTOCOL_APPROVAL)
- `related_personnel_measure` (FK → PersonnelMeasure)

### AgendaTemplate / AgendaTemplateItem
- Wiederverwendbare Vorlagen für Tagesordnungen
- Standard-TOPs (z.B. "Genehmigung letztes Protokoll")

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/meetings/<uuid:id>/agenda/add/` | TOP hinzufügen |
| `/meetings/<uuid:id>/agenda/<uuid:aid>/edit/` | TOP bearbeiten |
| `/meetings/<uuid:id>/agenda/<uuid:aid>/delete/` | TOP löschen |
| `/meetings/<uuid:id>/agenda/reorder/` | Umsortieren (HTMX) |
| `/meetings/templates/` | Vorlagen verwalten |

## Abhängigkeiten

- **meetings** (Meeting)
- **accounts** (User)
- **documents** (DocumentLink für Anhänge)
- **personnel** (PersonnelMeasure)
- **minutes** (Minutes für PROTOCOL_APPROVAL)

## Berechtigungen

- `agenda.add_item`, `agenda.edit_item`, `agenda.delete_item`
- `agenda.reorder`, `agenda.manage_templates`

## Templates

- `agendas/_item_list.html` (Drag & Drop mit Sortable.js)
- `agendas/item_form.html` (dynamisch je nach item_type)
- `agendas/_item_row.html` (HTMX-Fragment)

## Implementierungshinweise

- Drag-and-Drop mit **Sortable.js** + HTMX für Persistierung
- Bei Statuswechsel auf "Versandt": Benachrichtigung an alle Teilnehmer
- Automatische TOP-Erstellung nach Protokoll-Genehmigung
