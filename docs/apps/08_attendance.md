# App: `attendance` - Anwesenheitsverwaltung

## Übersicht

Digitale Anwesenheitserfassung mit 2FA-gesicherter Bestätigung (Online/Hybrid) oder manueller Eintragung (Präsenz), Ersatzmitglieder-Nachrückung und Beschlussfähigkeitsprüfung.

## Hauptfunktionen

### 1. Anwesenheitsbestätigung (Online/Hybrid)
- **2FA-gesichert:** TOTP oder Push-Benachrichtigung
- **Zeitstempel:** confirmed_at, arrival_time, departure_time
- **IP-Adresse:** Für Audit-Dokumentation
- Status: PRESENT, LATE, LEFT_EARLY

### 2. Präsenzerfassung
- **Druckbare Anwesenheitsliste** mit allen erwarteten Mitgliedern
- **Unterschrift vor Ort**
- **Digitalisierung:** Gescannte Liste als Dokument anhängen
- **Manuelle Eintragung:** Protokollführung trägt ein

### 3. Ersatzmitglieder-Nachrückung (§ 25 BetrVG)
- **Intelligente Vorschläge:**
  1. Listenzugehörigkeit (election_list_name)
  2. Listenplatz (election_list_position)
  3. Stimmenzahl (election_votes)
  4. Geschlechterquote (§ 15 Abs. 2 BetrVG)
  5. Verfügbarkeit (Kalender-Check)
- **Zuweisungs-Workflow:** Vorsitz wählt Ersatzmitglied aus
- **Temporärer Zugriff:** Von Einladung bis Sitzungsende (verlängerbar)

### 4. Beschlussfähigkeitsprüfung (§ 33 BetrVG)
- **Automatisch:** ≥ 50% der Gesamtmitglieder anwesend
- **Ersatzmitglieder zählen:** Nachrückende sind stimmber

echtigt
- **Warnung:** Bei drohender Beschlussunfähigkeit
- **Dokumentation:** Im Protokoll

## Datenmodell

### AttendanceRecord
- `id`, `meeting` (FK → Meeting), `user` (FK → User)
- `status` (PRESENT, LATE, LEFT_EARLY, EXCUSED, UNEXCUSED, SUBSTITUTED)
- `confirmed_at`, `arrival_time`, `departure_time`
- `confirmation_ip`, `confirmation_method` (TOTP, PUSH, MANUAL)
- `substituted_by` (FK → User, optional)
- `notes`
- **Constraint:** UNIQUE(meeting, user)

### SubstituteAssignment
- `id`, `meeting`, `absent_member`, `substitute`, `assigned_by`
- `assigned_at`, `access_granted_at`, `access_revoked_at`

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/meetings/<uuid:id>/attendance/` | Anwesenheitsliste |
| `/meetings/<uuid:id>/attendance/confirm/` | Anwesenheit bestätigen (2FA) |
| `/meetings/<uuid:id>/attendance/print/` | Druckbare Liste (Präsenz) |
| `/meetings/<uuid:id>/attendance/manual/` | Manuelle Eintragung |
| `/attendance/<uuid:id>/edit/` | Bearbeiten |
| `/meetings/<uuid:id>/substitute-suggestions/` | Ersatzmitglieder-Vorschläge |
| `/meetings/<uuid:id>/assign-substitute/` | Ersatzmitglied zuweisen |
| `/meetings/<uuid:id>/quorum/` | Beschlussfähigkeit prüfen |

### HTMX
- `/meetings/<uuid:id>/attendance/status/` - Live-Status
- `/meetings/<uuid:id>/quorum/check/` - Live-Quorum

## Abhängigkeiten

- **meetings** (Meeting)
- **committees** (Membership für Ersatzmitglieder)
- **accounts** (User, 2FA)
- **calendar_mgmt** (Verfügbarkeits-Check)

## Berechtigungen

- `attendance.confirm_own` - Eigene Anwesenheit bestätigen
- `attendance.view_list` - Liste einsehen
- `attendance.edit` - Bearbeiten
- `attendance.assign_substitute` - Ersatzmitglied zuweisen
- `attendance.view_suggestions` - Vorschläge einsehen

## Templates

- `attendance/attendance_list.html`
- `attendance/confirm_attendance.html` (2FA-Formular)
- `attendance/print_list.html` (druckbar)
- `attendance/substitute_suggestions.html`
- `attendance/_attendance_status.html` (HTMX)

## Implementierungshinweise

### Ersatzmitglieder-Vorschläge
```python
def get_substitute_suggestions(absent_member, meeting):
    from apps.calendar_mgmt.models import Absence
    
    # 1. Gleiche Liste
    substitutes = Membership.objects.filter(
        committee=absent_member.committee,
        member_type='SUBSTITUTE',
        is_active=True,
        election_list_name=absent_member.election_list_name
    ).order_by('election_list_position', '-election_votes')
    
    # 2. Verfügbarkeit prüfen
    available = []
    for sub in substitutes:
        # Keine Abwesenheit an diesem Tag
        if not Absence.objects.filter(
            user=sub.user,
            start_date__lte=meeting.date,
            end_date__gte=meeting.date
        ).exists():
            available.append(sub)
    
    # 3. Geschlechterquote
    # Minderheitengeschlecht nicht weiter unterrepräsentieren
    current_gender_balance = calculate_gender_balance(meeting)
    filtered = filter_by_gender_quota(available, current_gender_balance)
    
    return filtered
```

### Beschlussfähigkeitsprüfung
```python
def check_quorum(meeting):
    total_seats = meeting.committee.total_seats
    present_count = AttendanceRecord.objects.filter(
        meeting=meeting,
        status__in=['PRESENT', 'LATE']  # Verspätet zählt
    ).count()
    
    # Ersatzmitglieder zählen
    substitute_count = SubstituteAssignment.objects.filter(
        meeting=meeting,
        access_revoked_at__isnull=True
    ).count()
    
    total_present = present_count + substitute_count
    quorum_threshold = total_seats / 2
    
    return total_present >= quorum_threshold
```

## Tests

- Unit-Tests für Ersatzmitglieder-Logik
- Integration-Tests für 2FA-Bestätigung
- Geschlechterquoten-Tests
- Beschlussfähigkeits-Tests
