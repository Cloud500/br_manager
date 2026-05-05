# Teilnehmer-Quickstart

Kurzfassung für den Orchestrator.

## Auftrag

Implementiere eine **eigene Meeting-Teilnehmerverwaltung** als meeting-scoped Funktion.
Teilnehmer sind **keine** permanente Committee-Mitgliedschaft.

## Muss sofort gelten

- eigenes Modell `MeetingParticipant`
- eigenes Modell `MeetingParticipantChangeLog`
- Teilnehmer werden beim Meeting-Anlegen initial erzeugt
- aktive Mitglieder + externe Mitglieder übernehmen
- Einladung **nicht** beim Create versenden
- Versand erst über den bestehenden Einladungsschritt
- Abwesenheit und Ersatz gelten **generell**, nicht nur im DRAFT
- `nachladefähig` triggert Ersatzvorschlag
- `nicht nachladefähig` markiert nur abwesend
- Ersatz nur für das konkrete Meeting
- nach Versand: neue / ersetzende Teilnehmer bekommen Agenda-Mail
- nach Versand: entfernte / ersetzte-out Teilnehmer bekommen Storno-Mail
- interne und externe Empfänger müssen unterstützt werden
- nur Custom-RBAC über `apps.roles`
- Standardbearbeitung für CHAIR und VICE_CHAIR

## Nicht jetzt bauen

- permanente Änderungen an Committee-Mitgliedschaften
- Anwesenheits-Tracking während der Sitzung
- Stimm- oder Beschlusslogik
- Kalenderintegration
- separate Teilnehmer-Listen außerhalb des Meetings

## Implementierungsreihenfolge

1. Modell + Migration
2. Initialerzeugung beim Meeting-Create
3. Abwesenheit / Ersatz / ChangeLog
4. Versandlogik + Mail-Templates
5. Permissions
6. Meeting-Detail-UI
7. Tests

## Referenz

Der vollständige Masterplan steht in `TEILNEHMER_MASTERPLAN.md`.
