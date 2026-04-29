# Wahlen-Quickstart

Kurzfassung für den Orchestrator.

## Auftrag

Implementiere Wahlen als **eigenen TOP-Typ** auf Basis von `AgendaItem`.
Wahlen sind **keine Beschlüsse**.

## Muss sofort gelten

- eigenes Modell `Election`
- Kandidaten als eigenes Modell `ElectionCandidate`
- Kandidatennamen als Freitext, kein `User`-FK
- Wahltyp zunächst nur Personenwahl
- Mehrheitsart: `absolute` / `relative`
- Status: `DRAFT` / `PUBLISHED`
- Erstellung nur aus dem Sitzungs-/Agenda-Kontext
- Löschen des TOPs löscht die Wahl mit
- nur vorbereitende CRUD-Permissions

## Nicht jetzt bauen

- Durchführung der Wahl
- Abstimmungen
- Ergebnislogik
- Protokollintegration
- Wahlgänge

## Implementierungsreihenfolge

1. Modell + Migration
2. Validierung
3. Agenda-Integration
4. Permissions
5. Views/Forms
6. Tests

## Referenz

Der vollständige Masterplan steht in `WAHLEN_MASTERPLAN.md`.
