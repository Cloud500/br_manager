# 📋 DETAILLIERTER FUNKTIONSPLAN: MEETINGS APP (AKTUALISIERT)

## 🎯 KERNFUNKTIONEN

### 1. STATUS-WORKFLOW (AKTUALISIERT)

**Erlaubte Übergänge:**
```
DRAFT → SENT → IN_PROGRESS → COMPLETED
```

**Workflow-Regeln:**
```python
valid_transitions = {
    'DRAFT': ['SENT'],
    'SENT': ['IN_PROGRESS'],
    'IN_PROGRESS': ['COMPLETED'],
    'COMPLETED': []  # Final
}
```

**Business Rules:**
```python
is_editable = (status == 'DRAFT')
is_deletable = (status == 'DRAFT')
can_send_invitation = (status == 'DRAFT')
can_complete = (status == 'IN_PROGRESS')
```

---

### 2. BERECHTIGUNGSSYSTEM (AKTUALISIERT)

#### user_can_create(user, committee)

**Berechtigt sind:**
- ✅ Superuser (immer)
- ✅ User mit Permission `meeting.create_other` (Admin-Recht für ALLE Gremien)
- ✅ User mit Permission `meeting.create` **im EIGENEN Committee** (über Rolle)
- ✅ **SPEZIAL:** Für MAIN-Committee: User mit Permission `meeting.create` im Betriebsausschuss

**Wichtig:** `meeting.create` bezieht sich immer auf das **eigene Gremium**!

**Logik:**
```python
# 1. Superuser → TRUE
if user.is_superuser: return True

# 2. meeting.create_other (Admin) → TRUE für ALLE Gremien
if user.has_permission('meeting.create_other'): return True

# 3. meeting.create im EIGENEN Committee
for membership in user.memberships.filter(committee=committee):
    if membership.role.has_permission('meeting.create'):
        return True

# 4. SPEZIAL: MAIN-Committee + Betriebsausschuss
if committee.type == 'MAIN':
    betriebsausschuss = committee.get_betriebsausschuss()
    for membership in user.memberships.filter(committee=betriebsausschuss):
        if membership.role.has_permission('meeting.create'):
            return True

return False
```

**Beispiel 1: CHAIR erstellt Meeting im eigenen Gremium**
```
User: Max Mustermann
Committee: IT-Ausschuss
Membership: Max → IT-Ausschuss (Rolle: CHAIR)
CHAIR-Rolle hat: meeting.create ✅

Prüfung: user_can_create(Max, IT-Ausschuss)
  ✅ Max hat meeting.create in IT-Ausschuss
  → return True ✅

Ergebnis: Darf Meeting im IT-Ausschuss erstellen
```

**Beispiel 2: CHAIR versucht Meeting in ANDEREM Gremium**
```
User: Max Mustermann
Committee: Betriebsrat (anderes Gremium!)
Membership: Max → IT-Ausschuss (Rolle: CHAIR)
CHAIR-Rolle hat: meeting.create (aber nur für IT-Ausschuss!)

Prüfung: user_can_create(Max, Betriebsrat)
  ❌ Max hat KEINE Membership in Betriebsrat
  ❌ Max hat NICHT meeting.create_other
  → return False ❌

Ergebnis: Darf KEIN Meeting im Betriebsrat erstellen
```

**Beispiel 3: Betriebsausschuss-Mitglied für MAIN**
```
User: Anna Schmidt
Committee: Betriebsrat (MAIN)
Membership: Anna → Betriebsausschuss (Rolle: MEMBER)
MEMBER-Rolle im Betriebsausschuss hat: meeting.create ✅

Prüfung: user_can_create(Anna, Betriebsrat)
  ❌ Anna hat keine Membership in Betriebsrat
  ✅ Betriebsrat ist MAIN
  ✅ Anna ist Mitglied im Betriebsausschuss mit meeting.create
  → return True ✅ (Spezialregel)

Ergebnis: Darf Meeting im Betriebsrat erstellen
```

**Beispiel 4: Admin mit meeting.create_other**
```
User: System-Admin
Committee: Beliebiges Gremium
Membership: Admin hat meeting.create_other (globale Admin-Berechtigung)

Prüfung: user_can_create(Admin, JEDES_COMMITTEE)
  ✅ Admin hat meeting.create_other
  → return True ✅

Ergebnis: Darf Meetings in ALLEN Gremien erstellen
```

---

#### user_can_change_status(user, meeting)

**Berechtigt sind:**
- ✅ Superuser (immer)
- ✅ User mit Permission `meeting.change_status` **im Committee des Meetings** (über Rolle)

**Flexibilität:** Gremien können frei entscheiden, welche Rollen diese Berechtigung haben!
- Typisch: CHAIR, VICE_CHAIR
- Möglich auch: "2. Stellvertreter", "Protokollführung", etc.

**Logik:**
```python
# 1. Superuser → TRUE
if user.is_superuser: return True

# 2. meeting.change_status im Meeting's Committee
for membership in user.memberships.filter(committee=meeting.committee):
    if membership.role.has_permission('meeting.change_status'):
        return True

return False
```

**Beispiel 1: CHAIR ändert Status**
```
Meeting: BR-Sitzung Mai (Committee: Betriebsrat)
User: Max Mustermann
Membership: Max → Betriebsrat (Rolle: CHAIR)
CHAIR-Rolle hat: meeting.change_status ✅

Prüfung: user_can_change_status(Max, meeting)
  ✅ Max hat meeting.change_status in Betriebsrat
  → return True ✅

Ergebnis: Darf Status ändern
```

**Beispiel 2: Stellvertreter ändert Status**
```
Meeting: BR-Sitzung Mai (Committee: Betriebsrat)
User: Lisa Weber
Membership: Lisa → Betriebsrat (Rolle: VICE_CHAIR)
VICE_CHAIR-Rolle hat: meeting.change_status ✅

Prüfung: user_can_change_status(Lisa, meeting)
  ✅ Lisa hat meeting.change_status in Betriebsrat
  → return True ✅

Ergebnis: Darf Status ändern (über Rollenkonfiguration!)
```

**Beispiel 3: 2. Stellvertreter (flexibel konfiguriert)**
```
Meeting: BR-Sitzung Mai (Committee: Betriebsrat)
User: Thomas Müller
Membership: Thomas → Betriebsrat (Rolle: CUSTOM "2. Stellvertreter")
"2. Stellvertreter"-Rolle hat: meeting.change_status ✅ (vom Gremium so konfiguriert)

Prüfung: user_can_change_status(Thomas, meeting)
  ✅ Thomas hat meeting.change_status in Betriebsrat
  → return True ✅

Ergebnis: Darf Status ändern (flexibles Rollensystem!)
```

**Beispiel 4: Reguläres Mitglied ohne Permission**
```
Meeting: BR-Sitzung Mai (Committee: Betriebsrat)
User: Peter Schmidt
Membership: Peter → Betriebsrat (Rolle: MEMBER)
MEMBER-Rolle hat: meeting.change_status ❌ (nicht konfiguriert)

Prüfung: user_can_change_status(Peter, meeting)
  ❌ Peter hat NICHT meeting.change_status in Betriebsrat
  → return False ❌

Ergebnis: Darf Status NICHT ändern
```

---

### 3. KONFLIKT-ERKENNUNG (AKTUALISIERT)

**Funktion:** `check_meeting_conflicts(meeting)`

**Konflikt-Kriterien:**
- ✅ Gleiches Committee ODER übergeordnetes Committee (Parent)
- ✅ Gleiches Datum
- ✅ Überschneidende Zeiträume

**Algorithmus:**
```python
committees_to_check = [meeting.committee]

# Add parent committee
if meeting.committee.parent:
    committees_to_check.append(meeting.committee.parent)

conflicts = Meeting.objects.filter(
    committee__in=committees_to_check,
    date=meeting.date
).exclude(pk=meeting.pk)

# Time overlap check...
```

**Beispiel:**
```
Committee-Hierarchie:
  Betriebsrat (MAIN)
    ├─ Betriebsausschuss (COMMITTEE)
    └─ IT-Ausschuss (SUBCOMMITTEE)

Szenario:
  Meeting: IT-Ausschuss am 2026-05-15, 10:00-12:00
  
  Konflikt-Check:
    ✅ Prüft IT-Ausschuss
    ✅ Prüft Betriebsrat (Parent)
    ❌ Prüft NICHT Betriebsausschuss (Sibling)

Reason: Nur Parent-Conflicts sind relevant
```

---

### 4. VERANTWORTLICHKEIT

**Property:** `get_responsible_user`

**Logik:**
```python
@property
def get_responsible_user(self):
    """
    Returns chair or chair_substitute.
    TODO: Later check attendance when attendance app exists.
    """
    return self.chair if self.chair else self.chair_substitute
```

**Später mit attendance-App:**
```python
# Wenn chair anwesend → chair
# Wenn chair nicht anwesend → chair_substitute
```

---

## 🔄 BEISPIELABLAUF

### Vollständiger Meeting-Lebenszyklus

```
TAG 1 (2026-04-01): ERSTELLUNG
───────────────────────────────
User: Max Mustermann (CHAIR des Betriebsrats)
Action: Meeting erstellen

Prüfung: user_can_create(Max, Betriebsrat)
  ✅ Max ist CHAIR → TRUE

Meeting erstellt:
  status: DRAFT
  is_editable: TRUE
  is_deletable: TRUE
  can_send_invitation: TRUE
  can_complete: FALSE

TAG 8 (2026-04-08): EINLADUNG VERSENDEN
────────────────────────────────────────
User: Max Mustermann (chair)
Action: Einladung versenden

Prüfung:
  ✅ status == 'DRAFT'
  ✅ can_send_invitation == TRUE
  ✅ user_can_change_status(Max, meeting) == TRUE

Status-Übergang: DRAFT → SENT
  sent_at: 2026-04-08 09:30:00
  📧 E-Mail an alle Committee-Mitglieder

Neuer Zustand:
  status: SENT
  is_editable: FALSE
  is_deletable: FALSE
  can_send_invitation: FALSE
  can_complete: FALSE

TAG 15 (2026-04-15): SITZUNG BEGINNEN
──────────────────────────────────────
User: Max Mustermann (chair)
Action: Status ändern SENT → IN_PROGRESS

Prüfung:
  ✅ SENT → IN_PROGRESS erlaubt
  ✅ user_can_change_status(Max, meeting) == TRUE

Status-Übergang: SENT → IN_PROGRESS

Neuer Zustand:
  status: IN_PROGRESS
  can_complete: TRUE ← JETZT MÖGLICH

TAG 15 (2026-04-15, 12:15): SITZUNG ABSCHLIESSEN
─────────────────────────────────────────────────
User: Max Mustermann (chair)
Action: Meeting abschließen

Prüfung:
  ✅ status == 'IN_PROGRESS'
  ✅ can_complete == TRUE
  ✅ user_can_change_status(Max, meeting) == TRUE

Status-Übergang: IN_PROGRESS → COMPLETED
  actual_start_time: 10:05
  actual_end_time: 12:15

Endzustand:
  status: COMPLETED
  is_editable: FALSE
  is_deletable: FALSE
  can_send_invitation: FALSE
  can_complete: FALSE
```

---

## ❌ FEHLERSZENARIEN

### FEHLER 1: Ungültiger Status-Übergang

```
Meeting: status=DRAFT
User: Max (chair)
Versuch: DRAFT → IN_PROGRESS (direkt überspringen)

Validierung:
  ❌ 'IN_PROGRESS' not in valid_transitions['DRAFT']
  ❌ Erlaubt ist nur: ['SENT']

Response:
  JsonResponse(400): {
    'error': 'Ungültiger Status-Übergang von DRAFT zu IN_PROGRESS'
  }

Korrekt: DRAFT → SENT → IN_PROGRESS
```

### FEHLER 2: Keine Berechtigung

```
Meeting: status=SENT
  chair: Max
  chair_substitute: Lisa

User: Peter (reguläres Mitglied)
Versuch: SENT → IN_PROGRESS

Prüfung:
  ❌ Peter ≠ chair
  ❌ Peter ≠ chair_substitute

Response:
  JsonResponse(403): {
    'error': 'Keine Berechtigung zum Ändern des Status'
  }
```

### FEHLER 3: Falscher Status für Aktion

```
Meeting: status=SENT
User: Max (chair)
Versuch: Meeting abschließen

Prüfung:
  ❌ can_complete == FALSE (status ≠ IN_PROGRESS)

Response:
  Redirect mit Error:
  "Meeting kann nur im Status IN_PROGRESS abgeschlossen werden"
```

---

## 📊 ZUSAMMENFASSUNG DER ÄNDERUNGEN

| Aspekt | ALT | NEU |
|--------|-----|-----|
| **Status-Workflow** | DRAFT → IN_PROGRESS → APPROVED → SENT → COMPLETED | DRAFT → SENT → IN_PROGRESS → COMPLETED |
| **is_editable** | Verschiedene Stati | Nur DRAFT |
| **is_deletable** | Nur DRAFT | Nur DRAFT (gleich) |
| **can_send_invitation** | DRAFT/IN_PROGRESS/APPROVED | Nur DRAFT |
| **can_complete** | SENT + Datum in Vergangenheit | Nur IN_PROGRESS |
| **Berechtigungen** | Hardcoded CHAIR/VICE_CHAIR | **Flexibel über Rollensystem** |
| **meeting.create** | - | **Nur im eigenen Committee** (+ Betriebsausschuss für MAIN) |
| **meeting.create_other** | - | **Admin-Recht für alle Gremien** |
| **meeting.change_status** | Hardcoded chair/chair_substitute | **Flexibel konfigurierbar** (z.B. auch "2. Stellvertreter") |
| **Verantwortlichkeit** | - | get_responsible_user (chair/chair_substitute) |
| **Konflikt-Erkennung** | Nur gleiches Committee | Gleiches oder Parent-Committee |

---

## ✅ VALIDIERUNG

**1. Status-Workflow logisch?**
- DRAFT → bearbeitbar, Einladung versendbar ✅
- SENT → nicht mehr bearbeitbar, Sitzung kann beginnen ✅
- IN_PROGRESS → kann abgeschlossen werden ✅
- COMPLETED → final ✅

**2. Berechtigungen flexibel?**
- meeting.create nur im eigenen Committee ✅
- meeting.create_other für Admins ✅
- meeting.change_status über Rollensystem konfigurierbar ✅
- Gremien können frei entscheiden (z.B. "2. Stellvertreter") ✅

**3. Konflikt-Erkennung korrekt?**
- Prüft gleiches Committee ✅
- Prüft Parent-Committee ✅
- Ignoriert Sibling-Committees ✅

**4. Keine Hardcoded Rollen?**
- Alle Berechtigungen über Permission-System ✅
- Flexibel konfigurierbar pro Gremium ✅
- Keine Abhängigkeit von CHAIR/VICE_CHAIR codenames ✅

**ALLE ÄNDERUNGEN KORREKT IMPLEMENTIERT!** ✅

---

## 🎯 WICHTIGE DESIGN-ENTSCHEIDUNGEN

### 1. Permission-Scope

**meeting.create:**
- ✅ Bezieht sich auf das **eigene Committee**
- ✅ Verhindert ungewollte Committee-übergreifende Erstellung
- ✅ Betriebsausschuss-Spezialregel für MAIN-Committee

**meeting.create_other:**
- ✅ Globale Admin-Berechtigung
- ✅ Erlaubt Erstellung in **beliebigen** Gremien
- ✅ Nur für System-Admins/Superuser gedacht

### 2. Flexibles Rollensystem

**Keine Hardcoded Rollen:**
- ❌ KEINE Abhängigkeit von `role.codename == 'CHAIR'`
- ✅ Nur Permission-Check: `role.permissions.filter(codename='meeting.change_status')`
- ✅ Gremien können beliebige Rollen erstellen und Permissions zuweisen

**Beispiele für flexible Konfiguration:**
```
Gremium A:
  CHAIR → meeting.create, meeting.change_status
  VICE_CHAIR → meeting.create, meeting.change_status
  MEMBER → keine

Gremium B (mit 2. Stellvertreter):
  CHAIR → meeting.create, meeting.change_status
  VICE_CHAIR → meeting.create, meeting.change_status
  "2. STELLVERTRETER" → meeting.change_status
  MEMBER → keine

Gremium C (alle dürfen erstellen):
  CHAIR → meeting.create, meeting.change_status
  MEMBER → meeting.create
```

### 3. Verantwortlichkeit über Permissions

**get_responsible_user:**
- Aktuell: `chair if chair else chair_substitute`
- TODO: Später mit attendance-App automatisch basierend auf Anwesenheit
- **Wichtig:** Verantwortlichkeit ≠ Berechtigung!
  - `chair` ist **verantwortlich** (für Anzeige/Benachrichtigungen)
  - Berechtigung kommt aus `meeting.change_status` Permission
