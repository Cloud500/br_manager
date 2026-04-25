# App: `committees` - Gremienverwaltung

## Übersicht

Die `committees`-App verwaltet Gremien (Betriebsrat, Ausschüsse) und deren Mitgliedschaften. Sie ist zentral für die Strukturierung der Betriebsratsarbeit.

## Hauptfunktionen

### 1. Gremienverwaltung
- **Gremien-Typen:**
  - MAIN - Betriebsrat (Hauptgremium)
  - COMMITTEE - Betriebsausschuss
  - SUBCOMMITTEE - Fachausschüsse (z.B. Wirtschaftsausschuss, Personalausschuss)
  - ADHOC - Ad-hoc-Ausschüsse
- Hierarchische Struktur (Ausschüsse unterhalb Betriebsrat)
- Konfiguration pro Gremium:
  - Gesamtanzahl Sitze
  - Quorum-Typ (einfache/qualifizierte Mehrheit)
  - Personelle Einzelmaßnahmen aktiviert/deaktiviert

### 2. Mitgliederverwaltung
- **Mitgliedstypen:**
  - REGULAR - Reguläres Mitglied
  - SUBSTITUTE - Ersatzmitglied
  - EXTERNAL - Externes Ausschussmitglied (nicht im Hauptgremium)
- **Rollenzuweisung:** Jedes Mitglied erhält eine Gremiumsrolle (aus `roles`-App)
- **Wahlinfo-Felder:**
  - `election_list_name` - Listenname bei Listenwahl
  - `election_list_position` - Listenplatz
  - `election_votes` - Stimmenzahl bei Wahl
- Mitgliedschaftszeitraum (start_date, end_date)

### 3. Externe Ausschussmitglieder
- Personen, die nicht dem Hauptgremium angehören
- Haben nur Zugriff auf ihren Ausschuss
- Kein Zugriff auf Daten des Hauptgremiums oder anderer Ausschüsse
- Zugriff besteht solange Mitgliedschaft aktiv ist

### 4. Ersatzmitglieder
- Zuordnung zur Wahlliste (election_list_name)
- Listenplatz und Stimmenzahl für Nachrück-Reihenfolge
- Dauerhafter Zugriff auf Kalender (unabhängig vom Einsatzstatus)
- Temporärer Vollzugriff nur während Einsatzzeit

## Datenmodell

### Committee
- `id` (UUID, PK)
- `name` (CharField(200)) - Name des Gremiums
- `committee_type` (CharField(20)) - MAIN, COMMITTEE, SUBCOMMITTEE, ADHOC
- `parent` (ForeignKey → Committee, NULL) - Übergeordnetes Gremium
- `description` (TextField, optional)
- `created_at` (DateTimeField)
- `is_active` (BooleanField) - Aktiv/Inaktiv
- `total_seats` (IntegerField) - Gesamtanzahl Sitze
- `quorum_type` (CharField(20)) - SIMPLE_MAJORITY, QUALIFIED
- `personnel_enabled` (BooleanField) - Personelle Einzelmaßnahmen aktiviert

### Membership
- `id` (UUID, PK)
- `user` (ForeignKey → User)
- `committee` (ForeignKey → Committee)
- `role` (ForeignKey → Role) - Zugewiesene Gremiumsrolle
- `is_active` (BooleanField)
- `member_type` (CharField(20)) - REGULAR, SUBSTITUTE, EXTERNAL
- `start_date` (DateField)
- `end_date` (DateField, optional)
- `election_list_name` (CharField(100), optional) - Listenname bei Listenwahl
- `election_list_position` (IntegerField, optional) - Listenplatz
- `election_votes` (IntegerField, optional) - Stimmenzahl bei Wahl
- **Constraint:** UNIQUE(user, committee)

## URLs und Views

| URL | View | Beschreibung |
|-----|------|--------------|
| `/committees/` | CommitteeListView | Alle Gremien auflisten |
| `/committees/create/` | CommitteeCreateView | Neues Gremium erstellen |
| `/committees/<uuid:id>/` | CommitteeDetailView | Gremiumsdetails anzeigen |
| `/committees/<uuid:id>/edit/` | CommitteeEditView | Gremium bearbeiten |
| `/committees/<uuid:id>/members/` | MemberListView | Mitglieder auflisten |
| `/committees/<uuid:id>/members/add/` | MemberAddView | Mitglied hinzufügen |
| `/committees/<uuid:id>/members/<uuid:mid>/edit/` | MemberEditView | Mitgliedschaft bearbeiten |
| `/committees/<uuid:id>/members/<uuid:mid>/remove/` | MemberRemoveView | Mitglied entfernen |
| `/committees/<uuid:id>/substitutes/` | SubstituteListView | Ersatzmitglieder anzeigen |

### HTMX-Fragmente

| URL | Trigger | Beschreibung |
|-----|---------|--------------|
| `/committees/<uuid:id>/members/search/` | hx-get (Suchfeld) | Live-Suche in Mitgliederliste |
| `/committees/<uuid:id>/members/<uuid:mid>/inline-edit/` | hx-get/post | Inline-Bearbeitung |

## Abhängigkeiten

### Erforderliche Apps
- **accounts** (User-Modell)
- **roles** (Role-Modell für Mitgliedschaften)

### Optionale Apps
- **audit** (Audit-Logging für Gremien-/Mitgliedschaftsänderungen)

### Django-Pakete
- Django Standard (keine zusätzlichen Pakete erforderlich)

## Berechtigungen

- `committee.create` - Gremium erstellen
- `committee.edit` - Gremium bearbeiten
- `committee.view` - Gremiumsdetails einsehen
- `committee.manage_members` - Mitglieder hinzufügen/entfernen/bearbeiten
- `committee.view_members` - Mitgliederliste einsehen

## Templates

- `committees/committee_list.html` - Gremienübersicht
- `committees/committee_detail.html` - Gremiumsdetails
- `committees/committee_form.html` - Gremium erstellen/bearbeiten
- `committees/member_list.html` - Mitgliederliste
- `committees/member_form.html` - Mitglied hinzufügen/bearbeiten
- `committees/substitute_list.html` - Ersatzmitglieder-Übersicht
- `committees/_member_row.html` - HTMX-Fragment für Mitgliedszeile

## Implementierungshinweise

### 1. Hierarchie-Validierung
Beim Erstellen/Bearbeiten von Ausschüssen sicherstellen, dass:
- Nur MAIN-Gremien kein parent haben
- Alle anderen Gremien ein parent haben
- Keine Zirkelbezüge entstehen

```python
def clean(self):
    if self.committee_type == 'MAIN' and self.parent:
        raise ValidationError("Hauptgremium darf kein übergeordnetes Gremium haben")
    if self.committee_type != 'MAIN' and not self.parent:
        raise ValidationError("Ausschuss benötigt ein übergeordnetes Gremium")
```

### 2. Externe Ausschussmitglieder
Bei Zuweisung als EXTERNAL prüfen:
- Benutzer darf nicht bereits im Hauptgremium sein
- Zugriffsbeschränkung auf Ausschuss in Permissions implementieren

```python
def check_external_member_access(user, resource):
    """Externe Ausschussmitglieder haben nur Zugriff auf ihren Ausschuss"""
    if user.membership.member_type == 'EXTERNAL':
        return resource.committee == user.membership.committee
    return True
```

### 3. Ersatzmitglieder-Vorschläge
Helper-Funktion für Nachrück-Vorschläge (wird später in `attendance`-App genutzt):

```python
def get_substitute_suggestions(absent_member, meeting):
    """
    Ermittelt Ersatzmitglieder-Vorschläge nach:
    1. Listenzugehörigkeit
    2. Listenplatz
    3. Geschlechterquote
    4. Verfügbarkeit
    """
    # Gleiche Wahlliste
    substitutes = Membership.objects.filter(
        committee=absent_member.committee,
        member_type='SUBSTITUTE',
        is_active=True,
        election_list_name=absent_member.election_list_name
    )
    
    # Nach Listenplatz und Stimmenzahl sortieren
    substitutes = substitutes.order_by('election_list_position', '-election_votes')
    
    # Geschlechterquote prüfen (siehe § 15 Abs. 2 BetrVG)
    # Verfügbarkeit prüfen (Kalender-Check)
    
    return substitutes
```

### 4. Standard-Rollenzuweisung
Beim Hinzufügen eines Mitglieds automatisch passende Rolle vorschlagen:

```python
def suggest_default_role(member_type):
    if member_type == 'REGULAR':
        return Role.objects.get(codename='MEMBER')
    elif member_type == 'SUBSTITUTE':
        return Role.objects.get(codename='SUBSTITUTE')
    elif member_type == 'EXTERNAL':
        return Role.objects.get(codename='EXTERNAL_MEMBER')
```

## Verbindungen zu anderen Apps

### Ausgehende Abhängigkeiten
- **accounts:** User-Modell für Mitglieder
- **roles:** Role-Modell für Mitgliedschaftsrollen
- **audit:** Audit-Logging

### Eingehende Abhängigkeiten
- **meetings:** Sitzungen sind einem Gremium zugeordnet
- **agendas:** Tagesordnungen über Meeting → Committee
- **minutes:** Protokolle über Meeting → Committee
- **attendance:** Anwesenheit über Meeting → Committee
- **documents:** Dokumente einem Gremium zugeordnet
- **resolutions:** Beschlüsse über Meeting → Committee
- **calendar_mgmt:** Termine einem Gremium zugeordnet
- **todos:** Aufgaben optional einem Gremium zugeordnet
- **personnel:** Personelle Maßnahmen einem Gremium zugeordnet

## Tests

- Unit-Tests für Hierarchie-Validierung
- Integration-Tests für Mitgliedschaftsverwaltung
- Sicherheitstests für externe Ausschussmitglieder-Zugriff
- Tests für Ersatzmitglieder-Vorschläge
- Tests für Geschlechterquote-Berechnung
