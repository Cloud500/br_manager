# Testdaten-Konfiguration für `seed_testdata`

`seed_testdata` erzeugt lokale Entwicklungs- und Testdaten für BR Manager. Der Command liegt in `apps/accounts/management/commands/seed_testdata.py` und arbeitet mit Benutzern, Profilen, 2FA-Recovery-Codes, Gremien und Mitgliedschaften.

> Die Daten sind ausschließlich für lokale Entwicklung/Test gedacht. Alle erzeugten Benutzer verwenden dasselbe Entwicklungs-Passwort und dasselbe Entwicklungs-TOTP-Secret.

## Verwendung

```bash
# Konfigurierter Modus mit JSON-Datei aus dem Projektroot
python manage.py seed_testdata --config testdata_config.json

# Bestehende Testdaten löschen und danach neu erstellen
python manage.py seed_testdata --clear --config testdata_config.json

# Komitees/Mitgliedschaften überspringen, nur Benutzer erzeugen
python manage.py seed_testdata --config testdata_config.json --no-committees

# Legacy-Modus ohne JSON-Konfiguration
python manage.py seed_testdata --users 10

# Legacy-Modus mit Default: 10 reguläre Benutzer
python manage.py seed_testdata
```

## Optionen

| Option | Bedeutung |
|:---|:---|
| `--config <datei>` | Lädt eine JSON-Konfiguration relativ zum Projektroot. Wenn gesetzt, wird `--users` ignoriert. |
| `--clear` | Löscht vorhandene Benutzer, Gremien und Mitgliedschaften vor dem Seeding. Rollen und Permissions bleiben unverändert. |
| `--users <anzahl>` | Anzahl regulärer Benutzer im Legacy-Modus. Default ohne `--config`: `10`. |
| `--no-committees` | Erstellt nur Admin und Benutzer, aber keine Gremien/Mitgliedschaften. |

## Erzeugte Zugangsdaten

Alle erzeugten Benutzer haben:

- Passwort: `testpass123`
- aktivierte TOTP-2FA mit gemeinsamem Entwicklungs-Secret aus `apps.accounts.factories.DEV_TOTP_SECRET`
- 10 Recovery Codes

Der Command schreibt zusätzlich `testdata_users.txt` in den Projektroot. Diese Datei enthält Login-Hinweise und wird bei jedem Lauf überschrieben.

Hinweis: Der aktuelle Command gibt Zusammenfassung, TOTP-Hinweise und Dateihinweis doppelt aus, weil diese Ausgabeblöcke im `handle()` aktuell doppelt aufgerufen werden. Das ist ein Implementierungsstand der Ausgabe, nicht zwei separate Seed-Läufe.

## Konfigurierter Modus

Beispiel:

```bash
python manage.py seed_testdata --clear --config testdata_config.example.json
```

### `users`

```json
"users": {
  "male_count": 12,
  "female_count": 8,
  "guest_count": 3
}
```

- `male_count`: männliche Benutzer für den nicht-Gast-Pool.
- `female_count`: weibliche Benutzer für den nicht-Gast-Pool.
- `guest_count`: zusätzliche Gast-Benutzer. Sie sind normale Benutzerkonten, werden aber nicht für Wahllisten des Hauptgremiums verwendet und stehen bevorzugt als externe Ausschussmitglieder zur Verfügung.

### `main_committee`

```json
"main_committee": {
  "name": "Betriebsrat",
  "total_seats": 9,
  "minority_gender": "F",
  "minority_min_count": 3,
  "election_lists": []
}
```

- `name`: Name des Hauptgremiums.
- `total_seats`: Anzahl regulärer Sitze.
- `minority_gender`: `"M"`, `"F"` oder `null`.
- `minority_min_count`: Mindestzahl für das Minderheitengeschlecht.
- `election_lists`: Wahllisten mit Benutzer- und Sitzverteilung.

### `election_lists`

```json
"election_lists": [
  {
    "name": "Liste 1 - Gewerkschaft",
    "user_count": 5,
    "seats_in_committee": 4
  }
]
```

- `user_count`: Anzahl nicht-Gast-Benutzer auf dieser Liste.
- `seats_in_committee`: Anzahl der ersten Listenbenutzer, die reguläre Mitglieder werden.
- Weitere Listenbenutzer werden Ersatzmitglieder.
- Die ersten drei regulären Mitglieder insgesamt erhalten `CHAIR`, `VICE_CHAIR` und `CLERK`; danach erhalten reguläre Mitglieder `MEMBER`.
- Die Reihenfolge der verfügbaren Benutzer wird vor der Listenverteilung zufällig gemischt.

Validierungen:

- Summe aller `seats_in_committee` muss `main_committee.total_seats` entsprechen.
- Summe aller `user_count` darf `users.male_count + users.female_count` nicht überschreiten. Gäste zählen hierfür nicht mit.
- Die Minderheitenquote wird nach der Zuweisung geprüft und als Warnung ausgegeben, wenn sie nicht erfüllt ist.

### `subcommittees`

```json
"subcommittees": [
  {
    "name": "Wirtschaftsausschuss",
    "member_count": 4,
    "external_count": 1
  }
]
```

- `member_count`: Anzahl Mitglieder aus dem Hauptgremium.
- `external_count`: Anzahl externer Mitglieder aus dem Gast-Pool.
- `total_seats` des Ausschusses wird als `member_count + external_count` angelegt.
- Ausschüsse werden mit `substitute_logic_enabled=False` erstellt.
- Hauptgremiumsmitglieder werden Round-Robin auf Ausschüsse verteilt.
- Innerhalb jedes Ausschusses erhalten die ersten drei internen Mitglieder `CHAIR`, `VICE_CHAIR` und `CLERK`; weitere erhalten `MEMBER`.
- Externe Mitglieder erhalten `EXTERNAL_MEMBER`.

Validierungen:

- `member_count` darf `main_committee.total_seats` nicht überschreiten.
- Summe aller `external_count` darf `users.guest_count` nicht überschreiten.

## Legacy-Modus

Ohne `--config` erstellt der Command eine feste Struktur:

- Admin `admin@example.org`.
- Standardmäßig 10 reguläre Benutzer oder die über `--users` angegebene Anzahl.
- Hauptgremium `Betriebsrat` mit 9 Sitzen, Ersatzlogik, Minderheitengeschlecht `F` und Mindestzahl `3`.
- Rollenverteilung im Hauptgremium: erster Benutzer `CHAIR`, zweiter `VICE_CHAIR`, dritter `CLERK`, weitere reguläre Mitglieder `MEMBER`, übrige Benutzer bis maximal 10 als `SUBSTITUTE`.
- Feste Ausschüsse: `Wirtschaftsausschuss`, `Personalausschuss`, `Arbeitsschutzausschuss`, `Gleichstellungsausschuss`.
- Ausschussrollen: erstes internes Mitglied `CHAIR`, zweites `VICE_CHAIR`, drittes `CLERK`, weitere `MEMBER`.
- Bei ausreichend vielen Benutzern kann der Wirtschaftsausschuss ein externes Mitglied erhalten.

## Betriebsausschuss-Automatik

Wenn durch die Gremienlogik ein Betriebsausschuss automatisch erzeugt wird, sucht der Command diesen Ausschuss und füllt fehlende Sitze mit weiteren regulären BR-Mitgliedern auf. Vorsitz und Stellvertretung werden dabei durch die bestehenden Signale/Regeln erwartet.

## Voraussetzungen

- Rollen müssen vorhanden sein (`CHAIR`, `VICE_CHAIR`, `CLERK`, `MEMBER`, `SUBSTITUTE`, `EXTERNAL_MEMBER`). Sind sie nicht vorhanden, wird die Gremienerstellung übersprungen. Üblicherweise kommen Rollen/Permissions über Migrationen bzw. `seed_roles`.
- `--clear` löscht Benutzer, Gremien und Mitgliedschaften hart, verändert aber keine Rollen/Permissions.

## Beispieldateien

- `testdata_config.example.json`: vollständiges Beispiel.
- `testdata_config.json`: größere lokale Beispielkonfiguration.
- `testdata_config_small.json`: kleine Smoke-Test-Konfiguration.

## Aktuelle Testabdeckung

Für den Command selbst gibt es derzeit keine dedizierten Command-Tests. Änderungen an Validierung, Rollenverteilung oder Datei-/Ausgabeformat sollten daher mit gezielten Tests ergänzt werden.
