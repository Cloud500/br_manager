# Testdaten-Konfiguration für seed_testdata Command

Diese Konfigurationsdatei steuert die Erstellung von Testdaten für die BR-Manager Anwendung.

## Verwendung

```bash
# Testdaten mit Konfiguration erstellen
python manage.py seed_testdata --config testdata_config.json

# Bestehende Daten löschen und neu erstellen
python manage.py seed_testdata --clear --config testdata_config.json

# Legacy-Modus (ohne Konfiguration)
python manage.py seed_testdata --users 10
```

## Konfigurationsstruktur

### Users (Benutzer)

```json
"users": {
  "male_count": 12,      // Anzahl männlicher Benutzer
  "female_count": 8,     // Anzahl weiblicher Benutzer
  "guest_count": 3       // Anzahl Gäste (für externe Ausschussmitglieder)
}
```

- **male_count**: Männliche User werden für Gremiumsmitglieder verwendet
- **female_count**: Weibliche User werden für Gremiumsmitglieder verwendet
- **guest_count**: User ohne spezifisches Geschlecht, werden nur als externe Mitglieder in Ausschüssen verwendet

### Main Committee (Hauptgremium)

```json
"main_committee": {
  "name": "Betriebsrat",
  "total_seats": 9,
  "minority_gender": "F",
  "minority_min_count": 3,
  "election_lists": [...]
}
```

- **name**: Name des Hauptgremiums
- **total_seats**: Gesamtanzahl der Sitze
- **minority_gender**: Minderheitengeschlecht ("M" oder "F", null für keine Quote)
- **minority_min_count**: Mindestanzahl für Minderheitengeschlecht (§ 15 Abs. 2 BetrVG)
- **election_lists**: Array mit Wahllistenkonfigurationen

### Election Lists (Wahllisten)

```json
"election_lists": [
  {
    "name": "Liste 1 - Gewerkschaft",
    "user_count": 5,              // Wie viele User auf diese Liste
    "seats_in_committee": 4        // Wie viele davon ins Gremium kommen
  }
]
```

- **name**: Name der Wahlliste
- **user_count**: Anzahl User auf dieser Liste (reguläre Mitglieder + Ersatzmitglieder)
- **seats_in_committee**: Anzahl User von dieser Liste, die reguläre Mitglieder werden

**Wichtig:**
- Die Summe aller `seats_in_committee` muss gleich `total_seats` sein
- Die Summe aller `user_count` darf nicht größer sein als `male_count + female_count`
- Der erste User der ersten Liste wird automatisch Vorsitzender (CHAIR)
- User mit den meisten `seats_in_committee` werden reguläre Mitglieder, Rest wird Ersatzmitglieder

### Subcommittees (Ausschüsse)

```json
"subcommittees": [
  {
    "name": "Wirtschaftsausschuss",
    "member_count": 4,      // Mitglieder aus dem Hauptgremium
    "external_count": 1     // Externe Gäste (aus guest_count Pool)
  }
]
```

- **name**: Name des Ausschusses
- **member_count**: Anzahl Mitglieder aus dem Hauptgremium
- **external_count**: Anzahl externe Gäste

**Wichtig:**
- Ausschüsse haben **keine** Ersatzmitglieder (substitute_logic_enabled=False)
- `member_count` darf nicht größer sein als `total_seats` des Hauptgremiums
- Die Summe aller `external_count` darf nicht größer sein als `guest_count`
- Externe Mitglieder haben keine Wahllisten-Informationen

## Beispielkonfiguration

Siehe `testdata_config.example.json` für eine vollständige Beispielkonfiguration.

## Validierung

Der Command validiert automatisch:
- Alle erforderlichen Felder sind vorhanden
- Summe der Sitze stimmt mit total_seats überein
- Genügend User vorhanden für alle Zuweisungen
- Minderheitenquote wird geprüft (Warnung, falls nicht erfüllt)
- Externe Mitglieder überschreiten nicht guest_count

## Erstellte Daten

Nach erfolgreicher Ausführung:
1. **Admin-User**: `admin@example.org` (Superuser)
2. **Regular Users**: Nach Konfiguration (männlich/weiblich/Gäste)
3. **Hauptgremium**: Mit regulären Mitgliedern und Ersatzmitgliedern
4. **Ausschüsse**: Mit Mitgliedern aus Hauptgremium + externe Gäste

Alle User haben:
- Password: `testpass123`
- 2FA aktiviert mit gemeinsamem TOTP-Secret
- 10 Recovery Codes

Die User-Liste wird in `testdata_users.txt` gespeichert.
