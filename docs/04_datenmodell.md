# 04 – Datenmodell

## 4.1 Übersicht

Das Datenmodell bildet alle Entitäten des BR Managers ab. Die Datenbank ist PostgreSQL. Django ORM wird für die
Datenbankabstraktion verwendet.

## 4.2 Entity-Relationship-Diagramm (vereinfacht)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    User      │──M:N──│  Committee   │──1:N──│   Meeting    │
│  (accounts)  │       │ (committees) │       │  (meetings)  │
└──────┬───────┘       └──────┬───────┘       └───┬────┬─────┘
       │                      │                   │    │
       │                      │              ┌────┴┐  ┌┴──────┐
       │               ┌──────┴───────┐      │chair│  │clerk  │
       │               │ Membership   │      └─┬───┘  └───────┘
       │               │ (role → Role)│        │
       │               │ member_type: │   ┌────┴────┐
       │               │ REGULAR/     │   │         │
       │               │ SUBSTITUTE/  │┌──┴─────┐┌──┴─────┐
       │               │ EXTERNAL     ││AgendaIt││Attendan│
       │               │ election_    ││(TOP)   ││ce      │
       │               │  list_name   │└───┬────┘└────────┘
       │               └──────────────┘    │
       │                      │       ┌────┴───┬────────┬──────────┐
       │               ┌──────┴───────┐│       │        │          │
       │               │    Role      ││  ┌────┴───┐ ┌──┴───┐ ┌───┴────┐
       │               │   (roles)    ││  │Resolu- │ │Minut-│ │Document│
       │               └──────┬───────┘│  │tion    │ │es    │ └┬───────┘
       │                      │   ┌────┘  └───┬────┘ └───┬──┘  │
       │               ┌──────┴┐  │           │       ┌──┴─────┴───┐
       │               │RolePe.│  │Todo       │       │DocumentLink│
       │               └─┬─────┘  └───────────│       │(→AgendaItem│
       │              ┌──┴───────┐             │       │ →Minutes   │
       │              │Permission│        ┌────┴──────┐│ →Resolution│
  ┌────┴─────┐   ┌────┴──────┐   │       │  AgendaIt ││ →Personnel │
  │AuditLog  │   │Personnel  │←──────────│(related_  ││  Measure)  │
  └──────────┘   │Measure    │           │ personnel_│└────────────┘
                 └───────────┘           │  measure) │
                                         └───────────┘
```

## 4.3 Entitäten im Detail

### 4.3.1 Benutzer & Authentifizierung (`accounts`)

#### User (erweitertes Django-User-Modell)

| Feld               | Typ            | Beschreibung           | Constraints      |
|--------------------|----------------|------------------------|------------------|
| id                 | UUID           | Primärschlüssel        | PK, auto         |
| email              | EmailField     | E-Mail-Adresse (Login) | UNIQUE, NOT NULL |
| first_name         | CharField(100) | Vorname                | NOT NULL         |
| last_name          | CharField(100) | Nachname               | NOT NULL         |
| gender             | CharField(1)   | Geschlecht (m/w/d)     | NOT NULL         |
| phone              | CharField(20)  | Telefonnummer          | NULL             |
| is_active          | BooleanField   | Konto aktiv            | DEFAULT TRUE     |
| date_joined        | DateTimeField  | Registrierungsdatum    | auto             |
| two_factor_enabled | BooleanField   | 2FA aktiviert          | DEFAULT FALSE    |
| last_login         | DateTimeField  | Letzte Anmeldung       | NULL             |
| password           | CharField      | Passwort (gehashed)    | NOT NULL         |

#### UserProfile

| Feld                     | Typ                  | Beschreibung                   | Constraints      |
|--------------------------|----------------------|--------------------------------|------------------|
| id                       | UUID                 | Primärschlüssel                | PK               |
| user                     | OneToOneField → User | Benutzerreferenz               | UNIQUE, NOT NULL |
| department               | CharField(200)       | Abteilung                      | NULL             |
| employee_id              | CharField(50)        | Personalnummer                 | NULL             |
| notification_preferences | JSONField            | Benachrichtigungseinstellungen | DEFAULT {}       |
| avatar                   | ImageField           | Profilbild                     | NULL             |

---

### 4.3.2 Gremien & Ausschüsse (`committees`)

#### Committee

| Feld              | Typ                    | Beschreibung                                            | Constraints                |
|-------------------|------------------------|---------------------------------------------------------|----------------------------|
| id                | UUID                   | Primärschlüssel                                         | PK                         |
| name              | CharField(200)         | Name des Gremiums                                       | NOT NULL                   |
| committee_type    | CharField(20)          | Typ (MAIN, COMMITTEE, SUBCOMMITTEE, ADHOC)              | NOT NULL                   |
| parent            | ForeignKey → Committee | Übergeordnetes Gremium                                  | NULL (NULL = Hauptgremium) |
| description       | TextField              | Beschreibung                                            | NULL                       |
| created_at        | DateTimeField          | Erstellungsdatum                                        | auto                       |
| is_active         | BooleanField           | Aktiv/Inaktiv                                           | DEFAULT TRUE               |
| total_seats       | IntegerField           | Gesamtanzahl Sitze                                      | NOT NULL                   |
| quorum_type       | CharField(20)          | Quorum-Berechnung (SIMPLE_MAJORITY, QUALIFIED)          | DEFAULT SIMPLE_MAJORITY    |
| personnel_enabled | BooleanField           | Personelle Einzelmaßnahmen für diesen Ausschuss aktiviert | DEFAULT FALSE              |

#### Membership

| Feld                   | Typ                    | Beschreibung                                 | Constraints               |
|------------------------|------------------------|----------------------------------------------|---------------------------|
| id                     | UUID                   | Primärschlüssel                              | PK                        |
| user                   | ForeignKey → User      | Benutzer                                     | NOT NULL                  |
| committee              | ForeignKey → Committee | Gremium                                      | NOT NULL                  |
| role                   | ForeignKey → Role      | Zugewiesene Gremiumsrolle                    | NOT NULL                  |
| is_active              | BooleanField           | Aktive Mitgliedschaft                        | DEFAULT TRUE              |
| member_type            | CharField(20)          | Mitgliedstyp (REGULAR, SUBSTITUTE, EXTERNAL) | NOT NULL, DEFAULT REGULAR |
| start_date             | DateField              | Beginn der Mitgliedschaft                    | NOT NULL                  |
| end_date               | DateField              | Ende der Mitgliedschaft                      | NULL                      |
| election_list_name     | CharField(100)         | Listenname bei Listenwahl (z. B. „Liste 1")  | NULL                      |
| election_list_position | IntegerField           | Listenplatz (für Ersatzmitglieder)           | NULL                      |
| election_votes         | IntegerField           | Stimmenzahl bei Wahl                         | NULL                      |

**Constraints:** UNIQUE(user, committee) – ein Benutzer kann pro Gremium nur eine aktive Rolle haben.

---

### 4.3.3 Rollen & Berechtigungen (`roles`)

#### Role

| Feld           | Typ               | Beschreibung                               | Constraints               |
|----------------|-------------------|--------------------------------------------|---------------------------|
| id             | UUID              | Primärschlüssel                            | PK                        |
| name           | CharField(100)    | Rollenname                                 | NOT NULL                  |
| codename       | CharField(50)     | Eindeutiger Kurzname (z. B. CHAIR, MEMBER) | UNIQUE, NOT NULL          |
| description    | TextField         | Beschreibung der Rolle                     | NULL                      |
| role_type      | CharField(20)     | Typ (SYSTEM, COMMITTEE)                    | NOT NULL                  |
| is_system_role | BooleanField      | Standard-Rolle (nicht löschbar)            | DEFAULT FALSE             |
| created_by     | ForeignKey → User | Erstellt von                               | NULL (NULL = System-Seed) |
| created_at     | DateTimeField     | Erstellungszeitpunkt                       | auto                      |
| updated_at     | DateTimeField     | Letzte Änderung                            | auto                      |

**Hinweis:** Rollen mit `is_system_role = TRUE` können nicht gelöscht, aber in ihren Berechtigungen angepasst werden.

#### Permission

| Feld        | Typ            | Beschreibung                                             | Constraints      |
|-------------|----------------|----------------------------------------------------------|------------------|
| id          | UUID           | Primärschlüssel                                          | PK               |
| codename    | CharField(100) | Eindeutiger Berechtigungs-Code (z. B. `meeting.create`)  | UNIQUE, NOT NULL |
| name        | CharField(200) | Anzeigename                                              | NOT NULL         |
| description | TextField      | Beschreibung                                             | NULL             |
| category    | CharField(50)  | Kategorie/Modul (z. B. `meeting`, `minutes`, `document`) | NOT NULL, INDEX  |

**Hinweis:** Berechtigungen werden bei der Erstinstallation per Datenmigration angelegt und sind nicht durch Benutzer
erstellbar – nur zuweisbar.

#### RolePermission

| Feld        | Typ                     | Beschreibung        | Constraints |
|-------------|-------------------------|---------------------|-------------|
| id          | UUID                    | Primärschlüssel     | PK          |
| role        | ForeignKey → Role       | Rolle               | NOT NULL    |
| permission  | ForeignKey → Permission | Berechtigung        | NOT NULL    |
| assigned_by | ForeignKey → User       | Zugewiesen von      | NULL        |
| assigned_at | DateTimeField           | Zuweisungszeitpunkt | auto        |

**Constraints:** UNIQUE(role, permission) – eine Berechtigung kann einer Rolle nur einmal zugewiesen werden.

---

### 4.3.4 Sitzungen (`meetings`)

Das Sitzungsmodell ist die zentrale Entität der Anwendung. Alle weiteren Module (Tagesordnungen, Protokolle,
Anwesenheiten, Beschlüsse) sind an das Sitzungsobjekt gebunden. Jede Sitzung verfügt über einen Sitzungstyp (Online,
Hybrid, Präsenz), einen Vorsitz und eine Protokollführung.

#### Meeting

| Feld              | Typ                    | Beschreibung                                              | Constraints                 |
|-------------------|------------------------|-----------------------------------------------------------|-----------------------------|
| id                | UUID                   | Primärschlüssel                                           | PK                          |
| committee         | ForeignKey → Committee | Zugehöriges Gremium                                       | NOT NULL                    |
| title             | CharField(300)         | Titel der Sitzung                                         | NOT NULL                    |
| meeting_number    | CharField(20)          | Sitzungsnummer (z. B. "2026-05")                          | UNIQUE per Committee        |
| date              | DateField              | Sitzungsdatum                                             | NOT NULL                    |
| start_time        | TimeField              | Beginn                                                    | NOT NULL                    |
| end_time          | TimeField              | Ende (geplant)                                            | NULL                        |
| actual_start_time | TimeField              | Tatsächlicher Beginn                                      | NULL                        |
| actual_end_time   | TimeField              | Tatsächliches Ende                                        | NULL                        |
| meeting_type      | CharField(10)          | Sitzungsart (ONLINE, HYBRID, IN_PERSON)                   | NOT NULL, DEFAULT IN_PERSON |
| location_url      | URLField(500)          | Online-Teilnahmelink (bei ONLINE/HYBRID)                  | NULL                        |
| location_name     | CharField(200)         | Bezeichnung des Veranstaltungsorts (bei HYBRID/IN_PERSON) | NULL                        |
| location_street   | CharField(200)         | Straße und Hausnummer (bei HYBRID/IN_PERSON)              | NULL                        |
| location_zip      | CharField(10)          | Postleitzahl (bei HYBRID/IN_PERSON)                       | NULL                        |
| location_city     | CharField(100)         | Stadt (bei HYBRID/IN_PERSON)                              | NULL                        |
| location_room     | CharField(100)         | Raum / Stockwerk (bei HYBRID/IN_PERSON)                   | NULL                        |
| status            | CharField(20)          | Status (DRAFT, IN_PROGRESS, APPROVED, SENT, COMPLETED)    | NOT NULL                    |
| created_by        | ForeignKey → User      | Erstellt von                                              | NOT NULL                    |
| created_at        | DateTimeField          | Erstellungszeitpunkt                                      | auto                        |
| updated_at        | DateTimeField          | Letzte Änderung                                           | auto                        |
| is_quorate        | BooleanField           | Beschlussfähig                                            | NULL                        |
| chair             | ForeignKey → User      | Vorsitz der Sitzung                                       | NULL                        |
| clerk             | ForeignKey → User      | Protokollführung der Sitzung                              | NULL                        |

**Validierung nach Sitzungstyp:**

- **ONLINE:** Nur `location_url` wird verwendet. Adressfelder (`location_name`, `location_street`, `location_zip`,
  `location_city`, `location_room`) bleiben leer.
- **HYBRID:** `location_url` (Online-Link) **und** Adressfelder (`location_name`, `location_street`, `location_zip`,
  `location_city`, `location_room`) werden verwendet.
- **IN_PERSON:** Nur Adressfelder werden verwendet. `location_url` bleibt leer.

**Beziehungen:** Ein Meeting verknüpft Committee (1:N), AgendaItems (1:N), Minutes (1:1), AttendanceRecords (1:N) und
Resolutions (über AgendaItems).

---

### 4.3.5 Tagesordnungen (`agendas`)

#### AgendaItem (Tagesordnungspunkt / TOP)

| Feld                      | Typ                           | Beschreibung                                                              | Constraints   |
|---------------------------|-------------------------------|---------------------------------------------------------------------------|---------------|
| id                        | UUID                          | Primärschlüssel                                                           | PK            |
| meeting                   | ForeignKey → Meeting          | Zugehörige Sitzung                                                        | NOT NULL      |
| position                  | IntegerField                  | Reihenfolge                                                               | NOT NULL      |
| title                     | CharField(500)                | Titel des TOP                                                             | NOT NULL      |
| description               | TextField                     | Beschreibung / Erläuterung                                                | NULL          |
| item_type                 | CharField(20)                 | Typ (REGULAR, RESOLUTION, ELECTION, PERSONNEL_MEASURE, PROTOCOL_APPROVAL) | NOT NULL      |
| duration_minutes          | IntegerField                  | Geplante Dauer in Minuten                                                 | NULL          |
| presenter                 | ForeignKey → User             | Vortragende/r                                                             | NULL          |
| created_by                | ForeignKey → User             | Erstellt von                                                              | NOT NULL      |
| is_auto_generated         | BooleanField                  | Automatisch erzeugt                                                       | DEFAULT FALSE |
| related_minutes           | ForeignKey → Minutes          | Verknüpftes Protokoll (bei PROTOCOL_APPROVAL)                             | NULL          |
| related_personnel_measure | ForeignKey → PersonnelMeasure | Verknüpfte personelle Maßnahme (bei PERSONNEL_MEASURE)                    | NULL          |

#### AgendaTemplate

| Feld       | Typ                    | Beschreibung        | Constraints   |
|------------|------------------------|---------------------|---------------|
| id         | UUID                   | Primärschlüssel     | PK            |
| name       | CharField(200)         | Vorlagenname        | NOT NULL      |
| committee  | ForeignKey → Committee | Zugehöriges Gremium | NULL          |
| is_default | BooleanField           | Standard-Vorlage    | DEFAULT FALSE |
| created_by | ForeignKey → User      | Erstellt von        | NOT NULL      |

#### AgendaTemplateItem

| Feld        | Typ                         | Beschreibung                                                              | Constraints |
|-------------|-----------------------------|---------------------------------------------------------------------------|-------------|
| id          | UUID                        | Primärschlüssel                                                           | PK          |
| template    | ForeignKey → AgendaTemplate | Zugehörige Vorlage                                                        | NOT NULL    |
| position    | IntegerField                | Reihenfolge                                                               | NOT NULL    |
| title       | CharField(500)              | Titel                                                                     | NOT NULL    |
| item_type   | CharField(20)               | Typ (REGULAR, RESOLUTION, ELECTION, PERSONNEL_MEASURE, PROTOCOL_APPROVAL) | NOT NULL    |
| description | TextField                   | Beschreibung                                                              | NULL        |

**Beziehungen:** Ein AgendaItem gehört zu genau einem Meeting (N:1). Je nach `item_type` bestehen folgende
Verknüpfungen:

- **RESOLUTION:** Ein AgendaItem kann eine zugehörige Resolution besitzen (1:1, FK
  `Resolution.agenda_item → AgendaItem`).
- **ELECTION:** Ein AgendaItem kann über eine Resolution eine zugehörige Election besitzen (1:1:1,
  `Election.resolution → Resolution.agenda_item → AgendaItem`).
- **PROTOCOL_APPROVAL:** Verknüpfung mit einem bestehenden Protokoll über `related_minutes` (FK → Minutes).
- **PERSONNEL_MEASURE:** Verknüpfung mit einer bestehenden personellen Maßnahme über `related_personnel_measure` (FK →
  PersonnelMeasure).

Zusätzlich verknüpft ein AgendaItem optional MinutesItems (1:N), TodoItems (1:N) und DocumentLinks (1:N).

---

### 4.3.6 Protokolle (`minutes`)

#### Minutes

| Feld                 | Typ                     | Beschreibung                                                                                     | Constraints      |
|----------------------|-------------------------|--------------------------------------------------------------------------------------------------|------------------|
| id                   | UUID                    | Primärschlüssel                                                                                  | PK               |
| meeting              | OneToOneField → Meeting | Zugehörige Sitzung                                                                               | UNIQUE, NOT NULL |
| content              | TextField               | Protokollinhalt (HTML/JSON)                                                                      | NULL             |
| status               | CharField(30)           | Status (DRAFT, CLERK_SIGNED, CHAIR_SIGNED, PRELIMINARILY_APPROVED, FINALIZED, REVISION_REQUIRED) | NOT NULL         |
| version              | IntegerField            | Aktuelle Versionsnummer                                                                          | DEFAULT 1        |
| author               | ForeignKey → User       | Protokollführer/in                                                                               | NOT NULL         |
| signed_by_clerk      | ForeignKey → User       | Digital unterschrieben durch Protokollführung                                                    | NULL             |
| signed_by_clerk_at   | DateTimeField           | Unterschriftszeitpunkt Protokollführung                                                          | NULL             |
| clerk_signature_hash | CharField(128)          | Kryptographische Signatur Protokollführung                                                       | NULL             |
| signed_by_chair      | ForeignKey → User       | Digital unterschrieben durch Vorsitz                                                             | NULL             |
| signed_by_chair_at   | DateTimeField           | Unterschriftszeitpunkt Vorsitz                                                                   | NULL             |
| chair_signature_hash | CharField(128)          | Kryptographische Signatur Vorsitz                                                                | NULL             |
| finalized_at         | DateTimeField           | Finalisierungszeitpunkt                                                                          | NULL             |
| finalized_in_meeting | ForeignKey → Meeting    | Finalisiert in Sitzung                                                                           | NULL             |
| created_at           | DateTimeField           | Erstellungszeitpunkt                                                                             | auto             |
| updated_at           | DateTimeField           | Letzte Änderung                                                                                  | auto             |

#### MinutesVersion

| Feld               | Typ                  | Beschreibung          | Constraints |
|--------------------|----------------------|-----------------------|-------------|
| id                 | UUID                 | Primärschlüssel       | PK          |
| minutes            | ForeignKey → Minutes | Zugehöriges Protokoll | NOT NULL    |
| version_number     | IntegerField         | Versionsnummer        | NOT NULL    |
| content            | TextField            | Inhalt dieser Version | NOT NULL    |
| changed_by         | ForeignKey → User    | Geändert von          | NOT NULL    |
| changed_at         | DateTimeField        | Änderungszeitpunkt    | auto        |
| change_description | CharField(500)       | Änderungsbeschreibung | NULL        |

#### MinutesItem

| Feld        | Typ                     | Beschreibung          | Constraints |
|-------------|-------------------------|-----------------------|-------------|
| id          | UUID                    | Primärschlüssel       | PK          |
| minutes     | ForeignKey → Minutes    | Zugehöriges Protokoll | NOT NULL    |
| agenda_item | ForeignKey → AgendaItem | Zugehöriger TOP       | NOT NULL    |
| content     | TextField               | Protokolltext zum TOP | NULL        |
| position    | IntegerField            | Reihenfolge           | NOT NULL    |

---

### 4.3.7 Anwesenheit (`attendance`)

#### AttendanceRecord

| Feld                | Typ                   | Beschreibung                                                        | Constraints |
|---------------------|-----------------------|---------------------------------------------------------------------|-------------|
| id                  | UUID                  | Primärschlüssel                                                     | PK          |
| meeting             | ForeignKey → Meeting  | Zugehörige Sitzung                                                  | NOT NULL    |
| user                | ForeignKey → User     | Teilnehmer                                                          | NOT NULL    |
| status              | CharField(20)         | Status (PRESENT, LATE, LEFT_EARLY, EXCUSED, UNEXCUSED, SUBSTITUTED) | NOT NULL    |
| confirmed_at        | DateTimeField         | Bestätigungszeitpunkt (2FA)                                         | NULL        |
| arrival_time        | TimeField             | Ankunftszeit                                                        | NULL        |
| departure_time      | TimeField             | Gehzeit                                                             | NULL        |
| confirmation_ip     | GenericIPAddressField | IP-Adresse bei Bestätigung                                          | NULL        |
| confirmation_method | CharField(20)         | Bestätigungsmethode (TOTP, PUSH, MANUAL)                            | NULL        |
| substituted_by      | ForeignKey → User     | Ersetzt durch                                                       | NULL        |
| notes               | TextField             | Bemerkungen                                                         | NULL        |

**Constraints:** UNIQUE(meeting, user)

#### SubstituteAssignment

| Feld              | Typ                  | Beschreibung             | Constraints |
|-------------------|----------------------|--------------------------|-------------|
| id                | UUID                 | Primärschlüssel          | PK          |
| meeting           | ForeignKey → Meeting | Zugehörige Sitzung       | NOT NULL    |
| absent_member     | ForeignKey → User    | Abwesendes Mitglied      | NOT NULL    |
| substitute        | ForeignKey → User    | Ersatzmitglied           | NOT NULL    |
| assigned_by       | ForeignKey → User    | Zugewiesen von (Vorsitz) | NOT NULL    |
| assigned_at       | DateTimeField        | Zuweisungszeitpunkt      | auto        |
| access_granted_at | DateTimeField        | Zugriff gewährt ab       | auto        |
| access_revoked_at | DateTimeField        | Zugriff entzogen um      | NULL        |

---

### 4.3.8 Dokumente (`documents`)

#### Document

| Feld            | Typ                    | Beschreibung                                                | Constraints   |
|-----------------|------------------------|-------------------------------------------------------------|---------------|
| id              | UUID                   | Primärschlüssel                                             | PK            |
| title           | CharField(500)         | Dokumententitel                                             | NOT NULL      |
| description     | TextField              | Beschreibung                                                | NULL          |
| folder          | ForeignKey → Folder    | Zugehöriger Ordner                                          | NULL          |
| committee       | ForeignKey → Committee | Zugehöriges Gremium                                         | NOT NULL      |
| current_version | IntegerField           | Aktuelle Version                                            | DEFAULT 1     |
| access_level    | CharField(20)          | Zugriffsebene (PUBLIC, COMMITTEE, RESTRICTED, CONFIDENTIAL) | NOT NULL      |
| file_type       | CharField(20)          | Dateityp                                                    | NOT NULL      |
| file_size       | BigIntegerField        | Dateigröße in Bytes                                         | NOT NULL      |
| uploaded_by     | ForeignKey → User      | Hochgeladen von                                             | NOT NULL      |
| created_at      | DateTimeField          | Erstellungszeitpunkt                                        | auto          |
| updated_at      | DateTimeField          | Letzte Änderung                                             | auto          |
| is_archived     | BooleanField           | Archiviert                                                  | DEFAULT FALSE |

#### DocumentVersion

| Feld               | Typ                   | Beschreibung          | Constraints |
|--------------------|-----------------------|-----------------------|-------------|
| id                 | UUID                  | Primärschlüssel       | PK          |
| document           | ForeignKey → Document | Zugehöriges Dokument  | NOT NULL    |
| version_number     | IntegerField          | Versionsnummer        | NOT NULL    |
| file               | FileField             | Datei                 | NOT NULL    |
| uploaded_by        | ForeignKey → User     | Hochgeladen von       | NOT NULL    |
| uploaded_at        | DateTimeField         | Upload-Zeitpunkt      | auto        |
| change_description | CharField(500)        | Änderungsbeschreibung | NULL        |
| checksum           | CharField(64)         | SHA-256 Prüfsumme     | NOT NULL    |

#### Folder

| Feld       | Typ                    | Beschreibung          | Constraints |
|------------|------------------------|-----------------------|-------------|
| id         | UUID                   | Primärschlüssel       | PK          |
| name       | CharField(200)         | Ordnername            | NOT NULL    |
| parent     | ForeignKey → Folder    | Übergeordneter Ordner | NULL        |
| committee  | ForeignKey → Committee | Zugehöriges Gremium   | NOT NULL    |
| created_by | ForeignKey → User      | Erstellt von          | NOT NULL    |

#### DocumentAccess (Gastzugriff)

| Feld         | Typ                   | Beschreibung                 | Constraints   |
|--------------|-----------------------|------------------------------|---------------|
| id           | UUID                  | Primärschlüssel              | PK            |
| document     | ForeignKey → Document | Dokument                     | NOT NULL      |
| granted_to   | ForeignKey → User     | Zugriff für                  | NOT NULL      |
| granted_by   | ForeignKey → User     | Zugriff durch                | NOT NULL      |
| access_type  | CharField(10)         | Zugriffstyp (VIEW, DOWNLOAD) | NOT NULL      |
| valid_from   | DateTimeField         | Gültig ab                    | NOT NULL      |
| valid_until  | DateTimeField         | Gültig bis                   | NOT NULL      |
| access_token | CharField(64)         | Einladungstoken              | UNIQUE        |
| is_revoked   | BooleanField          | Widerrufen                   | DEFAULT FALSE |

#### DocumentTag

| Feld      | Typ                        | Beschreibung          | Constraints |
|-----------|----------------------------|-----------------------|-------------|
| id        | UUID                       | Primärschlüssel       | PK          |
| name      | CharField(100)             | Tag-Name              | UNIQUE      |
| documents | ManyToManyField → Document | Zugeordnete Dokumente | –           |

#### DocumentLink (Dokument-Verknüpfungen)

Generische Verknüpfungstabelle, um Dokumente an verschiedene Objekte (TOPs, Protokolle, Beschlüsse, Personelle
Maßnahmen) anzuhängen (vgl. 3.3.1 Anhänge, 3.6.1 Verknüpfungen, 3.13 Dokumentenanhänge).

| Feld               | Typ                   | Beschreibung                                                                      | Constraints |
|--------------------|-----------------------|-----------------------------------------------------------------------------------|-------------|
| id                 | UUID                  | Primärschlüssel                                                                   | PK          |
| document           | ForeignKey → Document | Verknüpftes Dokument                                                              | NOT NULL    |
| linked_object_type | CharField(30)         | Typ des verknüpften Objekts (AGENDA_ITEM, MINUTES, RESOLUTION, PERSONNEL_MEASURE) | NOT NULL    |
| linked_object_id   | UUIDField             | ID des verknüpften Objekts                                                        | NOT NULL    |
| linked_by          | ForeignKey → User     | Verknüpft durch                                                                   | NOT NULL    |
| linked_at          | DateTimeField         | Verknüpfungszeitpunkt                                                             | auto        |

**Constraints:** UNIQUE(document, linked_object_type, linked_object_id) – ein Dokument kann pro Zielobjekt nur einmal
verknüpft werden.

**Hinweis:** Über diese Tabelle werden die in 3.3.1 (Anhänge an TOPs), 3.6.1 (Verknüpfungen mit TOPs, Protokollen,
Beschlüssen) und 3.13 (Dokumentenanhänge bei personellen Maßnahmen) beschriebenen Dokumentverknüpfungen abgebildet.

---

### 4.3.9 Beschlüsse & Wahlen (`resolutions`)

#### Resolution

| Feld                   | Typ                     | Beschreibung                                        | Constraints    |
|------------------------|-------------------------|-----------------------------------------------------|----------------|
| id                     | UUID                    | Primärschlüssel                                     | PK             |
| agenda_item            | ForeignKey → AgendaItem | Zugehöriger TOP                                     | NOT NULL       |
| resolution_number      | CharField(20)           | Beschlussnummer (z. B. BR-2026-042)                 | UNIQUE         |
| title                  | CharField(500)          | Beschlusstitel                                      | NOT NULL       |
| text                   | TextField               | Beschlusstext                                       | NOT NULL       |
| reasoning              | TextField               | Begründung                                          | NULL           |
| resolution_type        | CharField(20)           | Typ (STANDARD, ELECTION)                            | NOT NULL       |
| majority_type          | CharField(20)           | Mehrheitstyp (SIMPLE, QUALIFIED)                    | DEFAULT SIMPLE |
| votes_for              | IntegerField            | Stimmen dafür                                       | NOT NULL       |
| votes_against          | IntegerField            | Stimmen dagegen                                     | NOT NULL       |
| abstentions            | IntegerField            | Enthaltungen                                        | NOT NULL       |
| eligible_voters        | IntegerField            | Anwesende wahlberechtigte Mitglieder bei Abstimmung | NOT NULL       |
| is_quorate             | BooleanField            | Beschlussfähigkeit festgestellt (berechnet)         | NOT NULL       |
| is_quorate_override    | BooleanField            | Beschlussfähigkeit manuell überschrieben            | DEFAULT FALSE  |
| sent_to_employer       | BooleanField            | An Arbeitgeber versendet                            | DEFAULT FALSE  |
| sent_to_employer_at    | DateTimeField           | Versandzeitpunkt an Arbeitgeber                     | NULL           |
| sent_to_employer_email | EmailField              | E-Mail-Adresse des Empfängers                       | NULL           |
| result                 | CharField(20)           | Ergebnis (ACCEPTED, REJECTED)                       | NOT NULL       |
| result_override        | BooleanField            | Ergebnis manuell überschrieben                      | DEFAULT FALSE  |
| is_secret_vote         | BooleanField            | Geheime Abstimmung                                  | DEFAULT FALSE  |
| created_at             | DateTimeField           | Erstellungszeitpunkt                                | auto           |

#### Election

| Feld               | Typ                        | Beschreibung                                | Constraints      |
|--------------------|----------------------------|---------------------------------------------|------------------|
| id                 | UUID                       | Primärschlüssel                             | PK               |
| resolution         | OneToOneField → Resolution | Zugehöriger Beschluss                       | UNIQUE, NOT NULL |
| election_type      | CharField(20)              | Wahlverfahren (MAJORITY, PROPORTIONAL)      | NOT NULL         |
| position_title     | CharField(200)             | Zu besetzende Position                      | NOT NULL         |
| is_secret          | BooleanField               | Geheime Wahl                                | DEFAULT TRUE     |
| meeting_type_check | CharField(10)              | Sitzungsart-Prüfung (nur IN_PERSON erlaubt) | NOT NULL         |

#### ElectionCandidate

| Feld           | Typ                   | Beschreibung                                  | Constraints   |
|----------------|-----------------------|-----------------------------------------------|---------------|
| id             | UUID                  | Primärschlüssel                               | PK            |
| election       | ForeignKey → Election | Zugehörige Wahl                               | NOT NULL      |
| candidate_name | CharField(200)        | Name der Kandidatin/des Kandidaten (Freitext) | NOT NULL      |
| votes_received | IntegerField          | Erhaltene Stimmen                             | DEFAULT 0     |
| is_elected     | BooleanField          | Gewählt                                       | DEFAULT FALSE |

---

### 4.3.10 Kalender (`calendar_mgmt`)

#### CalendarEvent

| Feld            | Typ                    | Beschreibung                            | Constraints                |
|-----------------|------------------------|-----------------------------------------|----------------------------|
| id              | UUID                   | Primärschlüssel                         | PK                         |
| title           | CharField(300)         | Titel                                   | NOT NULL                   |
| event_type      | CharField(20)          | Typ (MEETING, ABSENCE, REMINDER, OTHER) | NOT NULL                   |
| start_datetime  | DateTimeField          | Beginn                                  | NOT NULL                   |
| end_datetime    | DateTimeField          | Ende                                    | NOT NULL                   |
| all_day         | BooleanField           | Ganztägig                               | DEFAULT FALSE              |
| user            | ForeignKey → User      | Benutzer                                | NULL (NULL = gremiumsweit) |
| committee       | ForeignKey → Committee | Zugehöriges Gremium                     | NULL                       |
| meeting         | ForeignKey → Meeting   | Verknüpfte Sitzung                      | NULL                       |
| recurrence_rule | CharField(200)         | Wiederholungsregel (iCal RRULE)         | NULL                       |
| notes           | TextField              | Notizen                                 | NULL                       |

#### Absence

| Feld         | Typ               | Beschreibung                                         | Constraints   |
|--------------|-------------------|------------------------------------------------------|---------------|
| id           | UUID              | Primärschlüssel                                      | PK            |
| user         | ForeignKey → User | Benutzer                                             | NOT NULL      |
| start_date   | DateField         | Von                                                  | NOT NULL      |
| end_date     | DateField         | Bis                                                  | NOT NULL      |
| absence_type | CharField(20)     | Typ (SUBSTITUTE_AVAILABLE, SUBSTITUTE_NOT_AVAILABLE) | NOT NULL      |
| is_approved  | BooleanField      | Zur Kenntnis genommen                                | DEFAULT FALSE |

---

### 4.3.11 To-Do-Verwaltung (`todos`)

#### Todo

| Feld            | Typ                     | Beschreibung                     | Constraints              |
|-----------------|-------------------------|----------------------------------|--------------------------|
| id              | UUID                    | Primärschlüssel                  | PK                       |
| title           | CharField(300)          | Titel der Aufgabe                | NOT NULL                 |
| description     | TextField               | Beschreibung                     | NULL                     |
| priority        | CharField(10)           | Priorität (HIGH, MEDIUM, LOW)    | NOT NULL, DEFAULT MEDIUM |
| status          | CharField(20)           | Status (OPEN, IN_PROGRESS, DONE) | NOT NULL, DEFAULT OPEN   |
| due_date        | DateField               | Fälligkeitsdatum                 | NULL                     |
| committee       | ForeignKey → Committee  | Zugeordnetes Gremium             | NULL                     |
| meeting         | ForeignKey → Meeting    | Verknüpfte Sitzung               | NULL                     |
| agenda_item     | ForeignKey → AgendaItem | Verknüpfter TOP                  | NULL                     |
| resolution      | ForeignKey → Resolution | Verknüpfter Beschluss            | NULL                     |
| document        | ForeignKey → Document   | Verknüpftes Dokument             | NULL                     |
| created_by      | ForeignKey → User       | Erstellt von                     | NOT NULL                 |
| created_at      | DateTimeField           | Erstellungszeitpunkt             | auto                     |
| updated_at      | DateTimeField           | Letzte Änderung                  | auto                     |
| is_recurring    | BooleanField            | Wiederkehrend                    | DEFAULT FALSE            |
| recurrence_rule | CharField(200)          | Wiederholungsregel (iCal RRULE)  | NULL                     |

#### TodoAssignment

| Feld        | Typ               | Beschreibung        | Constraints |
|-------------|-------------------|---------------------|-------------|
| id          | UUID              | Primärschlüssel     | PK          |
| todo        | ForeignKey → Todo | Aufgabe             | NOT NULL    |
| assigned_to | ForeignKey → User | Zugewiesen an       | NOT NULL    |
| assigned_at | DateTimeField     | Zuweisungszeitpunkt | auto        |

**Constraints:** UNIQUE(todo, assigned_to)

---

### 4.3.12 Personelle Einzelmaßnahmen (`personnel`)

#### PersonnelMeasure

| Feld             | Typ                     | Beschreibung                                                                           | Constraints |
|------------------|-------------------------|----------------------------------------------------------------------------------------|-------------|
| id               | UUID                    | Primärschlüssel                                                                        | PK          |
| measure_type     | CharField(30)           | Typ (HIRING, TRANSFER, RECLASSIFICATION, DISMISSAL, OTHER)                             | NOT NULL    |
| reference_number | CharField(50)           | Aktenzeichen / Referenznummer                                                          | UNIQUE      |
| subject_name     | CharField(200)          | Name der betroffenen Person (Klartext, da zur Nachfrage beim Arbeitgeber erforderlich) | NOT NULL    |
| description      | TextField               | Beschreibung der Maßnahme                                                              | NOT NULL    |
| received_at      | DateTimeField           | Eingang beim Betriebsrat                                                               | NOT NULL    |
| deadline         | DateTimeField           | Fristablauf (z. B. 1 Woche nach § 99 Abs. 3 BetrVG)                                    | NOT NULL    |
| status           | CharField(30)           | Status (RECEIVED, COMPLETE, IN_REVIEW, STATEMENT_DRAFTED, RESOLUTION_MADE, COMPLETED)  | NOT NULL    |
| resolution       | ForeignKey → Resolution | Verknüpfter Beschluss (Zustimmung/Verweigerung)                                        | NULL        |
| statement        | TextField               | Stellungnahme des Betriebsrats                                                         | NULL        |
| notes            | TextField               | Sitzungsnotizen zur Maßnahme                                                           | NULL        |
| committee        | ForeignKey → Committee  | Zuständiges Gremium                                                                    | NOT NULL    |
| result_sent_at   | DateTimeField           | Zeitpunkt des Ergebnisversands an Arbeitgeber                                          | NULL        |
| result_sent_to   | EmailField              | E-Mail-Adresse des Arbeitgebers für Ergebnisversand                                    | NULL        |
| created_by       | ForeignKey → User       | Erfasst von                                                                            | NOT NULL    |
| created_at       | DateTimeField           | Erstellungszeitpunkt                                                                   | auto        |
| updated_at       | DateTimeField           | Letzte Änderung                                                                        | auto        |

**Beziehungen:** PersonnelMeasure verknüpft Committee (N:1), Resolution (1:1 optional) und kann über AgendaItem (
related_personnel_measure) als TOP auf eine Tagesordnung gesetzt werden.

---

### 4.3.13 Benachrichtigungen (`notifications`)

#### Notification

| Feld                | Typ               | Beschreibung                                              | Constraints   |
|---------------------|-------------------|-----------------------------------------------------------|---------------|
| id                  | UUID              | Primärschlüssel                                           | PK            |
| recipient           | ForeignKey → User | Empfänger                                                 | NOT NULL      |
| notification_type   | CharField(30)     | Typ (MEETING_INVITATION, REMINDER, PROTOCOL_REVIEW, etc.) | NOT NULL      |
| title               | CharField(300)    | Titel                                                     | NOT NULL      |
| message             | TextField         | Nachricht                                                 | NOT NULL      |
| is_read             | BooleanField      | Gelesen                                                   | DEFAULT FALSE |
| is_email_sent       | BooleanField      | E-Mail versandt                                           | DEFAULT FALSE |
| related_object_type | CharField(50)     | Verknüpfter Objekttyp                                     | NULL          |
| related_object_id   | UUIDField         | Verknüpfte Objekt-ID                                      | NULL          |
| created_at          | DateTimeField     | Erstellungszeitpunkt                                      | auto          |

---

### 4.3.14 Audit-Log (`audit`)

#### AuditLog

| Feld          | Typ                   | Beschreibung                                                          | Constraints          |
|---------------|-----------------------|-----------------------------------------------------------------------|----------------------|
| id            | UUID                  | Primärschlüssel                                                       | PK                   |
| user          | ForeignKey → User     | Benutzer                                                              | NULL (NULL = System) |
| action        | CharField(20)         | Aktion (CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, APPROVE) | NOT NULL             |
| resource_type | CharField(50)         | Betroffener Ressourcentyp                                             | NOT NULL             |
| resource_id   | UUIDField             | Betroffene Ressource-ID                                               | NULL                 |
| description   | TextField             | Beschreibung der Aktion                                               | NOT NULL             |
| ip_address    | GenericIPAddressField | IP-Adresse                                                            | NULL                 |
| user_agent    | CharField(500)        | Browser/User-Agent                                                    | NULL                 |
| old_values    | JSONField             | Vorherige Werte                                                       | NULL                 |
| new_values    | JSONField             | Neue Werte                                                            | NULL                 |
| timestamp     | DateTimeField         | Zeitstempel                                                           | auto, INDEX          |

**Hinweis:** Audit-Logs sind unveränderlich (kein UPDATE oder DELETE möglich). Retention Policy gemäß DSGVO
konfigurierbar.

---

## 4.4 Indizes

| Tabelle          | Feld(er)                                       | Typ                       | Begründung                                      |
|------------------|------------------------------------------------|---------------------------|-------------------------------------------------|
| Role             | codename                                       | B-tree (UNIQUE)           | Rollensuche per Kurzname                        |
| Role             | role_type                                      | B-tree                    | Filterung nach Rollentyp                        |
| Permission       | codename                                       | B-tree (UNIQUE)           | Berechtigungssuche per Code                     |
| Permission       | category                                       | B-tree                    | Filterung nach Modul/Kategorie                  |
| RolePermission   | role, permission                               | B-tree (UNIQUE composite) | Zuordnungs-Abfragen                             |
| AuditLog         | timestamp                                      | B-tree                    | Häufige zeitbasierte Abfragen                   |
| AuditLog         | user, timestamp                                | B-tree (composite)        | Benutzeraktivitäts-Abfragen                     |
| AuditLog         | resource_type, resource_id                     | B-tree (composite)        | Ressourcen-Historie                             |
| Membership       | committee, election_list_name                  | B-tree (composite)        | Nachrück-Ermittlung nach Wahlliste              |
| Meeting          | committee, date                                | B-tree (composite)        | Sitzungslisten pro Gremium                      |
| Meeting          | status                                         | B-tree                    | Filterung nach Status                           |
| Resolution       | resolution_number                              | B-tree                    | Suche nach Beschlussnummer                      |
| Document         | committee, access_level                        | B-tree (composite)        | Dokumentenlisten                                |
| AttendanceRecord | meeting, user                                  | B-tree (UNIQUE)           | Anwesenheitsabfragen                            |
| Notification     | recipient, is_read                             | B-tree (composite)        | Ungelesene Benachrichtigungen                   |
| CalendarEvent    | start_datetime, end_datetime                   | B-tree (composite)        | Kalenderabfragen                                |
| CalendarEvent    | event_type                                     | B-tree                    | Filterung nach Eventtyp (MEETING, ABSENCE etc.) |
| Todo             | due_date, status                               | B-tree (composite)        | Fällige/offene Aufgaben                         |
| Todo             | committee                                      | B-tree                    | Gremienweite Aufgabenlisten                     |
| TodoAssignment   | assigned_to                                    | B-tree                    | Persönliche Aufgabenlisten                      |
| PersonnelMeasure | deadline, status                               | B-tree (composite)        | Fristenüberwachung                              |
| PersonnelMeasure | committee                                      | B-tree                    | Gremienweite Maßnahmen                          |
| DocumentLink     | document                                       | B-tree                    | Dokumentverknüpfungs-Abfragen                   |
| DocumentLink     | linked_object_type, linked_object_id           | B-tree (composite)        | Zielobjekt-Abfragen                             |
| DocumentLink     | document, linked_object_type, linked_object_id | B-tree (UNIQUE composite) | Eindeutige Verknüpfungen                        |

## 4.5 Datenmigrations-Strategie

- Django-Migrationen (`makemigrations` / `migrate`) für Schema-Änderungen.
- Datenmigrationen für initiale Daten (Standard-Rollen inkl. EXTERNAL_MEMBER, Standard-Berechtigungen mit Zuordnungen,
  Benachrichtigungstypen).
- Rollback-fähige Migrationen für sichere Deployments.
- Migrationstests in CI/CD-Pipeline.
