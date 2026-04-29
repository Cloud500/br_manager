# Wahlen-Masterplan

Dieses Dokument ist die **einzige verbindliche Planungsquelle** für die spätere Umsetzung von Wahlen.
Es ist so geschrieben, dass ein Orchestrator-Agent die Funktion **autonom** implementieren kann, ohne weitere Rückfragen, solange keine fachlichen Widersprüche zu bestehenden Modellen/Mustern auftauchen.

## Zielbild

Wahlen sollen im System als **eigener TOP-Typ** neben normalen Tagesordnungspunkten und Beschlüssen existieren.
Eine Wahl ist **kein Beschluss**.
Sie wird aber aus der Tagesordnung heraus angelegt und gehört fachlich zum Sitzungs-/Tagesordnungskontext.

Wichtig:

- Wahlen werden nicht als erweiterter Beschluss modelliert.
- Wahlen sind ein **eigenes Modell**.
- Das Modell soll sich an den vorhandenen AgendaItem-Vererbungen orientieren, analog zu `Resolution`.
- Pro Wahl existiert genau **ein** zugehöriger TOP.
- Wird der TOP gelöscht, wird die Wahl mit gelöscht.

## Fachlicher Scope

### In Scope

- Wahl als auswählbarer TOP-Typ in der Tagesordnung
- eigenständiges Wahlmodell
- Personenwahlen mit Freitext-Kandidaten
- Auswahl zwischen absoluter und relativer Mehrheit
- vorbereitender Status-Workflow
- serverseitige Berechtigungen für Vorbereitung
- saubere BetrVG-konforme Vorstrukturierung

### Out of Scope

- Durchführung der Wahl in der Sitzung
- Abstimmungslogik
- Ergebnisermittlung
- Protokollintegration
- Wahlgänge / Runde-n-Logik
- separate Wahlübersichten außerhalb von Sitzung/Protokoll

## Leitentscheidungen

1. **Eigenes Modell** statt Erweiterung von Beschlüssen.
2. **Vererbung von `AgendaItem`** statt lockerer FK-Anbindung.
3. **Kandidaten ohne User-FK**.
4. **Nur Freitext-Namen** für Kandidaten.
5. **Nur Sitzungskontext** darf Wahlen anlegen.
6. **Nur vorbereitende Rechte** werden jetzt angelegt.
7. **PUBLISHED** ist der veröffentlichte, read-only Zustand.

## Fachmodell

### `Election`

`Election` erbt von `AgendaItem`.

Erwartete fachliche Felder:

- `election_type`
  - zunächst nur: Personenwahl
- `majority_type`
  - absolute Mehrheit
  - relative Mehrheit
- `status`
  - `DRAFT`
  - `PUBLISHED`

Hinweise:

- Titel und Beschreibung kommen aus `AgendaItem`.
- Die Wahl ist immer an genau einen TOP gebunden.
- Die Wahl soll nur in einem vorbereitenden Sitzungszustand erzeugt werden können.

### `ElectionCandidate`

Eigenes Kandidatenmodell.

Erwartete Felder:

- `election` (FK)
- `name` (Freitext)

Validierung:

- mindestens ein Kandidat pro Wahl

## Workflow

### Status

- `DRAFT`
  - bearbeitbar
- `PUBLISHED`
  - veröffentlicht / read-only

### Vorbereitung

1. Wahl wird aus der Sitzungs-/Agendaansicht erstellt.
2. In `DRAFT` darf sie bearbeitet werden.
3. Bei Veröffentlichung wird sie schreibgeschützt.
4. Die eigentliche Durchführung erfolgt später in einem separaten Konzept.

### Sitzungsbindung

- Erstellung nur aus dem Sitzungs-/Tagesordnungskontext.
- Sinnvoll nur, solange die Sitzung im vorbereitenden oder laufenden Kontext ist.
- Für diese Version reicht die Einschränkung auf die erlaubten Sitzungskontexte, die im bestehenden System am ehesten `DRAFT` / `IN_PROGRESS` entsprechen.

## UI / Anlegen

- In der TOP-Auswahl kann zusätzlich `Wahl` gewählt werden.
- Die Wahl wird aus der Sitzungsansicht heraus angelegt.
- Es gibt keine separate Wahl-Verwaltungsliste.
- Die Wahl lebt im Sitzungskontext weiter und wird später im Protokollkontext wieder aufgegriffen.

## Permissions

Nur vorbereitende Rechte:

- anlegen
- einsehen
- bearbeiten
- löschen

Explizit **nicht** jetzt:

- durchführen
- Ergebnis festhalten
- Abstimmung erfassen

## Daten- und Löschverhalten

- Der TOP ist der fachliche Parent.
- Wird der TOP gelöscht, muss die Wahl mit gelöscht werden.
- Cascade/Delete-Verhalten muss in Modellen bzw. Beziehungen eindeutig abgesichert werden.

## Erweiterbarkeit

Die Struktur soll spätere Erweiterung nicht blockieren:

- mehrere Wahlgänge später möglich
- späteres `ElectionRound`-Modell soll ohne Refactoring-Hölle ergänzbar sein
- Protokoll-/Ergebnisdaten bleiben jetzt bewusst außen vor

## BetrVG-Leitlinie

Die spätere Implementierung muss von Anfang an BetrVG-konform gedacht werden.
Das bedeutet für diese Phase:

- keine künstlichen Vereinfachungen, die spätere Rechtskonformität erschweren
- saubere Trennung zwischen Vorbereitung und Durchführung
- keine Vermischung von Wahl und Beschluss

## Implementierungsreihenfolge

### Phase 1: Modellierung

- `Election` als `AgendaItem`-Kind anlegen
- `ElectionCandidate` anlegen
- Felder für Typ, Mehrheit, Status ergänzen

### Phase 2: Validierung

- mindestens einen Kandidaten erzwingen
- nur erlaubte Wahltypen zulassen
- Statusübergänge absichern

### Phase 3: Agenda-Integration

- Wahl als TOP-Typ auswählbar machen
- Erstellung nur aus dem Sitzungskontext erlauben
- Löschkaskade von TOP zur Wahl sicherstellen

### Phase 4: Permissions

- vorbereitende CRUD-Rechte ergänzen
- keine Rechte für Durchführung/Ergebnisverwaltung

### Phase 5: Views / Forms

- Wahl-Erstellungsformular im Agenda-Kontext
- Kandidaten-Freitextfelder
- Bearbeitung nur im passenden Sitzungsstatus

### Phase 6: Tests

- Modelltests
- Status-Tests
- Delete-Tests
- Permissions-Tests
- View-/Form-Tests

## Orchestrator-Anweisung

Ein späterer Agent soll mit diesem Plan autonom arbeiten und in folgender Reihenfolge starten:

1. vorhandene Muster in `apps/agendas` und `apps/resolutions` prüfen
2. Modellstruktur für `Election` und `ElectionCandidate` entwerfen
3. Migrations-/Model-Implementierung vornehmen
4. Validierung und Statusworkflow ergänzen
5. Agenda-Integration bauen
6. Permissions ergänzen
7. Tests schreiben und ausführen

Dabei strikt nach `CODE_STYLE_GUIDE.md` arbeiten und die vorhandenen Projektmuster bevorzugen.
