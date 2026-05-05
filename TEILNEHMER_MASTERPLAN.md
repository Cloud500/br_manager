# Teilnehmer-Masterplan

Dieses Dokument ist die **einzige verbindliche Planungsquelle** für die spätere Umsetzung der Meeting-Teilnehmerverwaltung.
Es ist so geschrieben, dass ein Orchestrator-Agent die Funktion **autonom** implementieren kann, ohne weitere Rückfragen, solange keine fachlichen Widersprüche zu bestehenden Modellen/Mustern auftauchen.

## Zielbild

Für jedes Meeting gibt es eine **eigenständige, meeting-scoped Teilnehmerverwaltung**.
Teilnehmer sind **kein** permanenter Bestandteil der Committee-Mitgliedschaft, sondern eine Momentaufnahme pro Meeting.

Wichtig:

- Teilnehmer werden als **eigene Meeting-Daten** modelliert.
- Die Teilnehmerliste wird beim Anlegen des Meetings initial erzeugt.
- Einladungen werden **nicht** automatisch beim Erstellen verschickt.
- Der bestehende Einladungsschritt ist der fachliche Trigger für den Versand.
- Abwesenheit und Ersatz sind **generell** möglich, nicht nur im DRAFT.
- Ersatz gilt **nur für das konkrete Meeting**.
- Änderungen nach dem Versand müssen nachvollziehbar sein und E-Mail-Folgen auslösen.

## Fachlicher Scope

### In Scope

- automatische Initialisierung der Meeting-Teilnehmer beim Meeting-Anlegen
- Teilnehmerverwaltung im Meeting-Detail
- Abwesenheit markieren
- Ersatz / Nachrücken mit Vorschlagslogik
- Unterscheidung zwischen `nachladefähig` und `nicht nachladefähig`
- Einladung per bestehendem Send-Invitation-Flow
- Folge-E-Mails bei späteren Änderungen nach Versand
- Storno-/Cancel-E-Mails für entfernte bzw. ersetzte Teilnehmer
- Unterstützung für interne Nutzer und externe Mitglieder ohne Account
- vollständige Änderungshistorie je Teilnehmer
- serverseitige RBAC-Absicherung über das bestehende Rollen-System

### Out of Scope

- allgemeines Anwesenheits-Tracking während der Sitzung
- Stimmrecht-/Beschlusslogik
- Kalenderintegration
- separate Teilnehmer-Übersichtslisten außerhalb des Meeting-Kontexts
- permanente Änderung von Committee-Mitgliedschaften

## Leitentscheidungen

1. **Eigenes Meeting-Teilnehmermodell** statt Erweiterung von `Membership`.
2. **Meeting-scoped Historie** statt nur aktueller Flags.
3. **Ersatzlogik wird für alle relevanten Meeting-Phasen unterstützt**, nicht nur im DRAFT.
4. **Vorschlag durch System, Bestätigung durch User**.
5. **Ersatz ist keine dauerhafte Mitgliedschaftsänderung**.
6. **E-Mail-Versand folgt dem Meeting-Workflow** und nicht dem Initial-Create.
7. **Custom RBAC** aus `apps.roles`, keine Django-Default-Permissions.
8. Standardzugriff für Bearbeitung bleibt **CHAIR / VICE_CHAIR**, alle anderen read-only, sofern nicht explizit berechtigt.

## Fachmodell

### `MeetingParticipant`

Ein Teilnehmerdatensatz gehört genau zu einem Meeting.

Erwartete fachliche Felder:

- `meeting` (FK)
- `membership` (FK, optional je nach Teilnehmerart)
- `user` (FK, optional)
- `email` (für externe Empfänger oder Snapshot)
- `display_name`
- `participant_type`
  - interner Teilnehmer
  - externer Teilnehmer
  - nachgerückter Ersatz
- `status`
  - eingeladen
  - abwesend
  - ersetzt
  - ersetzt durch Ersatz
  - storniert / entfernt
- `absence_reason`
- `nachladefaehig` (bool)
- `is_initially_invited` (bool)
- `replaced_by` (FK auf `MeetingParticipant`, optional)
- `replaces` (FK auf `MeetingParticipant`, optional)
- `invite_sent_at`
- `last_notified_at`

Hinweise:

- Der Datensatz muss einen verlässlichen Snapshot der relevanten Empfängerdaten enthalten.
- Für externe Mitglieder darf kein User-Account erforderlich sein.
- Ein Teilnehmer kann später mehrfach in Historienereignissen auftauchen, aber die Beziehung zum Meeting bleibt stabil.

### `MeetingParticipantChangeLog`

Eigenes Historienmodell pro Meeting-Teilnehmer.

Erwartete Felder:

- `meeting_participant` (FK)
- `changed_at`
- `changed_by`
- `action`
  - initial angelegt
  - eingeladen
  - abwesend gesetzt
  - ersatz vorgeschlagen
  - ersatz bestätigt
  - ersetzt
  - storniert
  - reaktiviert / angepasst
- `old_state` / `new_state` oder äquivalente Snapshot-Felder
- `note`

Validierung:

- jede fachlich relevante Änderung muss protokolliert werden

## Initiale Teilnehmererzeugung

Beim Anlegen eines Meetings werden automatisch Teilnehmerdatensätze erzeugt für:

- alle aktiven Committee-Mitglieder
- alle bestehenden externen Mitglieder des Committees

Dabei gilt:

- noch **keine E-Mail** versenden
- Teilnehmer nur initial speichern
- die finale Einladung erfolgt erst über den bestehenden Send-Invitation-Flow

## Workflow

### Grundzustand

Jeder Teilnehmer hat eine eigene Lebenszykluslogik innerhalb des Meetings.

Mögliche Fachzustände:

- initial angelegt
- eingeladen
- abwesend
- Ersatz vorgeschlagen
- Ersatz bestätigt
- ersetzt
- storniert

### Abwesenheit und Ersatz

Die Logik gilt **generell** für das Meeting, nicht nur im DRAFT.

#### `nachladefähig`

- Teilnehmer wird als abwesend markiert.
- System ermittelt einen Ersatzvorschlag.
- Vorschlag basiert konzeptionell auf der bestehenden Substitute-Logik:
  - Listenposition
  - minority-gender quota
  - aktive Ersatzmitglieder
- User bestätigt den Vorschlag explizit im UI.
- Nach Bestätigung wird nur die Meeting-Teilnehmerliste geändert, nicht die Committee-Mitgliedschaft.

#### `nicht nachladefähig`

- Teilnehmer wird nur als abwesend markiert.
- Kein Ersatz vorgeschlagen.
- Kein Nachrücken.

### Nach Versand / nach Einladung

Wenn bereits Einladungen verschickt wurden, dann gilt:

- neu hinzugefügte Teilnehmer erhalten die Agenda erneut per E-Mail
- ersetzende Teilnehmer erhalten die Agenda
- entfernte oder ersetzte-out Teilnehmer erhalten eine Storno-/Cancel-E-Mail

## UI / Einbindung in das Meeting-Detail

- Teilnehmerliste direkt im Meeting-Detail anzeigen
- Aktionen nur für berechtigte User sichtbar und serverseitig abgesichert
- Abwesenheit markieren
- Ersatz vorschlagen und bestätigen
- Storno/Entfernung dokumentieren
- Historie je Teilnehmer einsehbar machen
- bestehende Buttons für Einladung/Senden bleiben der zentrale Workflow-Entry-Point

## E-Mail-Verhalten

Es werden mindestens folgende Mail-Typen benötigt:

- Einladung mit Agenda
- Storno / Cancellation

Anforderungen:

- Versand an interne User und externe Empfänger
- keine Abhängigkeit von einem Account als Versandvoraussetzung
- Mailtext und Template müssen meetingbezogene Daten enthalten
- nachträgliche Änderungen im `SEND`-Kontext müssen die passenden Folge-Mails auslösen

## Permissions

Nur Custom-RBAC über `apps.roles`.

Erwartete neue Rechte:

- Teilnehmer sehen
- Teilnehmer bearbeiten
- Teilnehmer als abwesend markieren
- Ersatz vorschlagen / bestätigen
- Teilnehmer versenden / nachbenachrichtigen

Standardverhalten:

- CHAIR und VICE_CHAIR dürfen Teilnehmer- und Agenda-nahe Aktionen ausführen
- alle anderen standardmäßig read-only
- zusätzliche Rechte können explizit über Rollen vergeben werden

## Daten- und Löschverhalten

- Meeting ist fachlicher Parent.
- Teilnehmerdatensätze gehören ausschließlich zum Meeting.
- Änderungshistorie wird mit dem Teilnehmer mitgeführt.
- Beim Löschen des Meetings werden Teilnehmer und Historie mit gelöscht.
- Permanente Committee-Daten dürfen durch Meeting-Teilnehmeraktionen nicht verändert werden.

## Integration in bestehende Systeme

### `apps.meetings`

- Meeting-Detail als UI-Anker
- bestehender Send-Invitation-Flow als Versand-Trigger
- Status `SEND` bleibt der relevante Zustand nach Versand

### `apps.committees`

- Quelle für aktive Mitglieder, externe Mitglieder und Substitute
- bestehende Ersatzlogik als konzeptionelle Vorlage

### `apps.roles`

- neue explizite Permissions
- Seed über bestehende `9999_*`-Migrationslogik

### `apps.accounts`

- interne User und E-Mail-Adressen
- externe Empfänger ohne Account

## Tests

Erforderliche Tests:

- Initialerzeugung beim Meeting-Anlegen
- Teilnehmerliste / ChangeLog
- Abwesenheit mit und ohne Nachladefähigkeit
- Ersatzvorschlag und Bestätigung
- E-Mail-Versand bei Send und Folgeänderungen
- Cancel-/Storno-Versand
- Permission-Tests
- View-/Form-/Workflow-Tests
- externe Empfänger ohne User-Account

## Implementierungsreihenfolge

### Phase 1: Modellierung

- `MeetingParticipant` anlegen
- `MeetingParticipantChangeLog` anlegen
- Beziehungen, Snapshots und Statusfelder definieren

### Phase 2: Initialisierung

- automatische Erzeugung beim Meeting-Create einbauen
- aktive Mitglieder und externe Mitglieder übernehmen

### Phase 3: Workflow / Ersatz

- Abwesenheit und Ersatzlogik implementieren
- Vorschlagsmechanik an vorhandene Substitute-Logik anbinden
- Meeting-scoped Bestätigung umsetzen

### Phase 4: Versandlogik

- Einladung an den bestehenden Send-Flow hängen
- Agenda-/Storno-E-Mails bei späteren Änderungen auslösen

### Phase 5: UI

- Teilnehmerbereich im Meeting-Detail
- Aktionen für Abwesenheit / Ersatz / Historie

### Phase 6: Permissions

- neue Custom-Permissions ergänzen
- Seed-Migration und Matrix anpassen

### Phase 7: Tests

- Modelltests
- Workflowtests
- Permissions-Tests
- Mail-Tests

## Orchestrator-Anweisung

Ein späterer Agent soll mit diesem Plan autonom arbeiten und in folgender Reihenfolge starten:

1. vorhandene Muster in `apps/meetings`, `apps/committees`, `apps/roles` und `apps/accounts` prüfen
2. fachliche Datenstruktur für Teilnehmer und Historie entwerfen
3. Migrations-/Model-Implementierung vornehmen
4. Meeting-Initialisierung und Ersatzworkflow bauen
5. Versand- und Follow-up-E-Mails integrieren
6. Permissions ergänzen
7. UI im Meeting-Detail ergänzen
8. Tests schreiben und ausführen

Dabei strikt nach `CODE_STYLE_GUIDE.md` arbeiten und die vorhandenen Projektmuster bevorzugen.
