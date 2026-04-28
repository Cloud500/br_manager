# 04 - Implementierungsplan: Tagesordnungen (Agendas)

**Version:** 1.2  
**Stand:** April 2026  
**Status:** Planung

---

## Übersicht

Dieses Dokument beschreibt die Implementierung eines **modulbasierten Tagesordnungs-Systems** für die BR-Manager Anwendung. Das System ermöglicht die Erstellung, Verwaltung und Strukturierung von Tagesordnungen für Sitzungen mit flexiblen, erweiterbaren Modulen für verschiedene Tagesordnungspunkt-Typen.

### Ziele

1. **Modulare Architektur**: Tagesordnungspunkte (TOPs) sind in Module unterteilt (Regular Items, Resolutions, Elections, etc.)
2. **Granulare Berechtigungen**: Jedes Modul hat eigene Permissions (z.B. darf normale TOPs erstellen, darf Beschlüsse erstellen)
3. **Basis-Funktionalität zuerst**: Phase 1 implementiert nur normale Tagesordnungspunkte
4. **Meeting-Integration**: Jedes Meeting hat genau eine Agenda
5. **Erweiterbarkeit**: Spätere Module (Beschlüsse, Wahlen) können einfach hinzugefügt werden

### Abgrenzung

- **NICHT** die alte `06_agendas.md` 1:1 umsetzen (veraltet)
- **Fokus auf Dokumentation**, minimale Code-Snippets
- Anpassung an bestehende Code-Struktur (committees, meetings, roles)

---

## 1. Systemarchitektur

### 1.1 Kern-Komponenten

```
apps/
  agendas/
    models.py           # Agenda, AgendaItem (Base), AgendaItemRegular
    managers.py         # Custom QuerySet/Manager
    forms.py            # AgendaItemForm, AgendaItemRegularForm
    views.py            # CRUD Views
    signals.py          # Auto-Agenda bei Meeting-Erstellung
    mixins.py           # AgendaPermissionMixin
    templates/
      agendas/
        item_form.html
    static/
      agendas/
        agenda_reorder.js  # Sortable.js Integration
```

### 1.2 Modulares Design

**Agenda-Item Typen (Module):**

| Modul | Phase | Beschreibung |
|-------|-------|--------------|
| `REGULAR` | Phase 1 | Normale Tagesordnungspunkte |
| `RESOLUTION` | Phase 2 | Beschlüsse |
| `ELECTION` | Phase 3 | Wahlen |
| `PROTOCOL_APPROVAL` | Phase 4 | Protokollgenehmigung |
| `PERSONNEL_MEASURE` | Phase 5 | Personalmaßnahmen |

**Implementierungsstrategie:**
- Phase 1: Basis-Modell `AgendaItem` (Abstract Base) + `AgendaItemRegular`
- Spätere Phasen: Neue Modelle erben von `AgendaItem` (z.B. `AgendaItemResolution`)

---

## 2. Datenmodell

### 2.1 Agenda-Modell

**Beschreibung:**
Das Agenda-Modell ist eine **OneToOne-Relation** zu einem Meeting. Jedes Meeting hat genau eine Agenda. Die Finalisierung erfolgt **automatisch** basierend auf dem Meeting-Status.

**Wichtige Felder:**
- `id`: UUID Primary Key
- `meeting`: OneToOne zu `meetings.Meeting` mit CASCADE Delete
- `created_at`, `updated_at`: Audit-Trail

**Felder die NICHT vorhanden sind:**
- ~~`is_finalized`~~: Wird als **Property** berechnet basierend auf `meeting.status == 'SENT'`
- ~~`finalized_at`~~: Nicht nötig (kommt aus Meeting)
- ~~`finalized_by`~~: Nicht nötig (kommt aus Meeting)

**Properties (computed):**

1. **`is_editable`**
   - Gibt `True` zurück wenn Meeting-Status `DRAFT` oder `IN_PROGRESS` ist
   - Gibt `False` zurück bei allen anderen Status
   - Rationale: Agenda kann in Vorbereitung (DRAFT) und während der Sitzung (IN_PROGRESS) bearbeitet werden

2. **`is_finalized`**
   - Gibt `True` zurück wenn Meeting-Status `SENT` ist
   - Gibt `False` zurück bei allen anderen Status
   - Rationale: Agenda ist finalisiert sobald Einladung versendet wurde

3. **`item_count`**
   - Zählt alle zugeordneten AgendaItems
   - Nützlich für Admin-Display und Templates

**Methoden:**

1. **`reorder_items(item_order: List[UUID])`**
   - Erhält Liste von Item-UUIDs in gewünschter Reihenfolge
   - Aktualisiert das `sort_order` Feld jedes Items basierend auf Position in der Liste
   - Verwendet Float-Werte für feinere Sortierung (0.0, 1.0, 2.0, etc.)
   - Nach Update: Ruft `recalculate_item_numbers()` auf

2. **`recalculate_item_numbers()`**
   - Berechnet alle `item_number` Felder aller Items neu
   - **Performance:** Nutzt `bulk_update()` für effiziente Datenbank-Updates (single SQL query statt N queries)
   - **Algorithmus:**
     - Query: `self.agendaitemregular_items.select_related('parent').order_by('sort_order')`
     - Counter-Dictionary: `{parent_id: next_number}` (Type: `Dict[Optional[UUID], int]`)
     - Iteration durch alle Items:
       - Items ohne `parent_id`: Counter für `None` erhöhen, `item_number = str(counter[None])`
       - Items mit `parent_id`: Counter für `parent_id` erhöhen, `item_number = f"{parent.item_number}.{counter[parent_id]}"`
     - Beispiel: TOP 1 hat Kinder → "1.1", "1.2", TOP 1.2 hat Kinder → "1.2.1", "1.2.2"
   - Speichert alle Items via `AgendaItemRegular.objects.bulk_update(items_to_update, fields=['item_number'], batch_size=100)`
   - Type Hints: `def recalculate_item_numbers(self) -> None:`

### 2.2 AgendaItem (Abstract Base Model)

**Beschreibung:**
Abstract Base Model für alle Tagesordnungspunkt-Typen. Definiert gemeinsame Felder und Methoden. Konkrete Modelle (z.B. `AgendaItemRegular`) erben davon.

**Wichtige Felder:**

1. **`id`**: UUID Primary Key
2. **`agenda`**: ForeignKey zu `Agenda` mit CASCADE Delete
   - Related name ist dynamisch: `%(class)s_items` (z.B. `agendaitemregular_items`)
3. **`parent`**: ForeignKey zu `self` (nullable)
   - Ermöglicht hierarchische Struktur (Unterpunkte)
   - CASCADE Delete: Wenn Parent gelöscht wird, werden Kinder auch gelöscht
4. **`item_number`**: CharField (max 20, **nicht editierbar**)
   - Wird automatisch berechnet
   - Beispiele: "1", "1.1", "1.2", "2", "2.1", "2.1.3"
5. **`title`**: CharField (max 500)
   - Kurztitel des TOPs
6. **`description`**: TextField (optional)
   - Ausführliche Beschreibung
7. **`sort_order`**: FloatField
   - Für Drag-and-Drop Sortierung
   - Float ermöglicht feinere Positionierung als Integer
8. **`item_type`**: CharField (max 50, **nicht editierbar**)
   - Diskriminator für Polymorphismus
   - Wird automatisch gesetzt in `save()` Methode

**Wichtige Implementierungs-Details:**

1. **Automatische Nummerierung:**
   - `item_number` wird NIEMALS manuell gesetzt
   - System berechnet basierend auf:
     - `sort_order`: Definiert Reihenfolge innerhalb einer Ebene
     - `parent`: Definiert Hierarchie-Ebene
   - Neuberechnung nach jedem Create/Update/Delete/Reorder

2. **Hierarchie-Verschachtelung:**
   - Items können beliebig tief verschachtelt werden
   - Beispiel: TOP 1 → TOP 1.1 → TOP 1.1.1 → TOP 1.1.1.1
   - Keine technische Begrenzung der Tiefe (UI sollte aber max 3-4 Ebenen empfehlen)

3. **Polymorphismus:**
   - `item_type` Feld wird in `save()` automatisch auf `self.__class__.__name__` gesetzt
   - Ermöglicht spätere Unterscheidung zwischen verschiedenen Item-Typen (Regular, Resolution, Election)
   
   **Polymorphismus-Strategie: Multi-Table Inheritance**
   
   Django nutzt **Multi-Table Inheritance** für konkrete Modelle, die von Abstract Base erben:
   - `AgendaItem` ist Abstract (`abstract = True`) → Keine eigene Tabelle
   - `AgendaItemRegular` erbt von `AgendaItem` → Eigene Tabelle mit allen Feldern
   - Spätere Modelle (`AgendaItemResolution`, `AgendaItemElection`) → Jeweils eigene Tabellen
   
   **Querying:**
   ```python
   # Alle Regular Items einer Agenda
   regular_items = AgendaItemRegular.objects.filter(agenda=my_agenda)
   
   # Später: Alle Resolution Items
   resolution_items = AgendaItemResolution.objects.filter(agenda=my_agenda)
   
   # Alle Items gemischt (Phase 2+): Union oder itertools.chain
   from itertools import chain
   all_items = list(chain(regular_items, resolution_items))
   all_items.sort(key=lambda x: x.sort_order)
   ```
   
   **Alternative (optional für Phase 2+):**
   - Package `django-polymorphic` für automatisches Subclass-Querying
   - Ermöglicht `AgendaItem.objects.filter(agenda=my_agenda)` mit automatischer Typ-Erkennung
   - Entscheidung kann in Phase 2 getroffen werden

**Methoden:**

1. **`save(*args, **kwargs)`**
   - Setzt `item_type` wenn noch nicht vorhanden
   - Ruft parent `save()` auf
   - Triggert anschließend Neuberechnung der Nummern (über Agenda)

2. **`get_type_display()`**
   - Gibt menschenlesbaren Typ zurück
   - Beispiele: "Normaler TOP", "Beschluss", "Wahl"

3. **`calculate_item_number()`**
   - Hilfsmethode für Nummerierungs-Berechnung
   - Wird von `Agenda.recalculate_item_numbers()` aufgerufen

**Meta-Optionen:**
- `abstract = True` (darf nicht direkt instanziiert werden)
- `ordering = ['sort_order']` (Standard-Sortierung)

### 2.3 AgendaItemRegular (Phase 1)

**Beschreibung:**
Konkretes Modell für normale Tagesordnungspunkte. Erbt alle Felder von `AgendaItem`, fügt keine zusätzlichen Felder hinzu.

**Felder:**
- Keine zusätzlichen Felder (nutzt nur Basis-Felder von `AgendaItem`)

**Meta-Optionen:**
- `verbose_name = 'Normaler TOP'`
- `verbose_name_plural = 'Normale TOPs'`
- `ordering = ['sort_order', 'item_number']`

**Spätere Module (Beispiele für Phase 2+):**

- **`AgendaItemResolution`** (Phase 2):
  - Zusätzliche Felder: `resolution_text`, `requires_vote`, `voting_type`
  
- **`AgendaItemElection`** (Phase 3):
  - Zusätzliche Felder: `position`, `election_mode`, `candidates`

---

## 3. Berechtigungssystem

### 3.1 Permissions-Struktur

**Agenda-Basis-Permissions:**

| Codename | Name | Kategorie | Beschreibung |
|----------|------|-----------|--------------|
| `agenda.view` | Tagesordnung ansehen | Agenda | Darf Tagesordnungen ansehen |

**Modul-spezifische Permissions (Phase 1 - Regular Items):**

| Codename | Name | Kategorie | Beschreibung |
|----------|------|-----------|--------------|
| `agenda.add_item_regular` | Normalen TOP hinzufügen | Agenda Items | Darf normale TOPs erstellen |
| `agenda.edit_item_regular` | Normalen TOP bearbeiten | Agenda Items | Darf normale TOPs bearbeiten |
| `agenda.delete_item_regular` | Normalen TOP löschen | Agenda Items | Darf normale TOPs löschen |
| `agenda.reorder_items` | TOPs neu anordnen | Agenda Items | Darf Reihenfolge und Hierarchie ändern |

**Wichtig:** Die folgenden Permissions werden NICHT benötigt:
- ~~`agenda.create`~~: Agenda wird automatisch mit Meeting erstellt
- ~~`agenda.edit`~~: Keine direkten Agenda-Edits, nur Items
- ~~`agenda.delete`~~: Löschen nur über Meeting möglich (CASCADE)
- ~~`agenda.finalize`~~: Finalisierung erfolgt automatisch über Meeting-Status

**Spätere Module (Beispiele für Phase 2+):**

- Phase 2 (Beschlüsse): `agenda.add_item_resolution`, `agenda.edit_item_resolution`, `agenda.vote_on_resolution`
- Phase 3 (Wahlen): `agenda.add_item_election`, `agenda.conduct_election`

### 3.2 Rollen-Zuweisungen

**Standard-Zuweisungen nach Rolle:**

| Rolle | Permissions | Begründung |
|-------|-------------|------------|
| **CHAIR** (Vorsitz) | Alle 5 Permissions | Volle Kontrolle über Agenda |
| **VICE_CHAIR** (Stellv. Vorsitz) | Alle 5 Permissions | Wie CHAIR |
| **CLERK** (Schriftführung) | Alle 5 Permissions | Erstellt üblicherweise die Agenda |
| **MEMBER** (Mitglied) | Nur `agenda.view` | Leserechte, keine Bearbeitung |
| **MEMBER** (in BA) | Alle 5 Permissions | BA-Mitglieder haben erweiterte Rechte |
| **SUBSTITUTE** (Ersatzmitglied) | **KEINE** Permissions | Können Agenda nicht sehen |
| **EXTERNAL_MEMBER** | **KEINE** Permissions | Erst nach Einladung (später) |
| **GUEST** | **KEINE** Permissions | Erst nach Einladung (später) |

**Rationale:**

1. **Vorsitz/Stellv. Vorsitz:**
   - Leiten die Sitzung, müssen Agenda vorbereiten können
   - Können TOPs hinzufügen/ändern/löschen

2. **Schriftführung:**
   - Erstellt üblicherweise die Agenda
   - Gleiche Rechte wie Vorsitz

3. **Normale Mitglieder:**
   - Nur Leserechte
   - Vorschlagssystem für TOPs kommt später als separates Feature

4. **BA-Mitglieder (Betriebsausschuss-Mitglieder):**
   - Erweiterte Rechte wie Vorsitz
   - **Identifikation:** Mitglieder in einem Committee vom Typ `COMMITTEE` (Betriebsausschuss)
   - Permission-Check prüft zusätzlich BA-Membership (siehe Abschnitt 5.3)
   - Können bei der Vorbereitung helfen

5. **Ersatzmitglieder:**
   - Keine Rechte (können Meeting nicht sehen)
   - Einspringen-Logik kommt später (temporäre Rechte)

6. **Externe/Gäste:**
   - Keine Rechte
   - Einladungssystem kommt später (temporäre Rechte für eingeladene Gäste)

---

## 4. Implementierungsphasen

### Phase 1: Projekt-Setup & Basis-Modelle

**Ziel:** Grundgerüst erstellen, normale TOPs funktionsfähig

#### 4.1 Django-App erstellen

**Command:**
```bash
python manage.py startapp agendas apps/agendas
```

**Dateien erstellen:**
- `apps/agendas/__init__.py`
- `apps/agendas/models.py`
- `apps/agendas/managers.py`
- `apps/agendas/admin.py`
- `apps/agendas/forms.py`
- `apps/agendas/views.py`
- `apps/agendas/urls.py`
- `apps/agendas/signals.py`
- `apps/agendas/mixins.py`

**Settings anpassen:**
In `config/settings/base.py` die App zu `INSTALLED_APPS` hinzufügen.

#### 4.2 Managers erstellen

**Datei:** `apps/agendas/managers.py`

**AgendaQuerySet:**
Custom QuerySet mit folgenden Filter-Methoden:

1. **`finalized()`**
   - Filters agendas where `meeting__status='SENT'`
   - Returns only finalized agendas

2. **`editable()`**
   - Filters agendas where `meeting__status__in=['DRAFT', 'IN_PROGRESS']`
   - Returns only editable agendas

3. **`for_committee(committee_id)`**
   - Filters agendas for a specific committee
   - Filter: `meeting__committee_id=committee_id`

**AgendaManager:**
Custom Manager that uses AgendaQuerySet and provides the same methods.

**Rationale:**
- Reusable filters for common queries
- Better readability in views/templates
- DRY Principle

#### 4.3 Basis-Modelle implementieren

**Datei:** `apps/agendas/models.py`

Implementierung der Modelle wie in Abschnitt 2 beschrieben:
- `Agenda` Modell mit Properties und Methoden
- `AgendaItem` Abstract Base Model
- `AgendaItemRegular` konkretes Modell

**Wichtige Implementierungs-Details:**

1. **Hierarchische Nummerierung (`recalculate_item_numbers`):**
   - Iterate through all items sorted by `sort_order`
   - Counter dictionary per parent: `{parent_id: next_number}`
   - Items without parent: "1", "2", "3", ...
   - Items with parent: "[Parent-Number].[Counter]"
   - Example: TOP 1 → Children: 1.1, 1.2; TOP 1.2 → Children: 1.2.1, 1.2.2
   - Save all items with new `item_number` (update only this field)

2. **Polymorphismus (`item_type`):**
   - In `save()` method: If `item_type` empty, set to `self.__class__.__name__`
   - Enables later distinction between Regular/Resolution/Election

3. **Validierung (nur wenn editierbar):**
   - In `clean()` method: Check if `agenda.is_editable`
   - If not editable: Raise ValidationError with meeting status

#### 4.4 Migrationen erstellen

**Commands:**
```bash
python manage.py makemigrations agendas
python manage.py migrate agendas
```

**Erwartete Migration:**
- `0001_initial.py`: Erstellt `Agenda` und `AgendaItemRegular` Tabellen

---

### Phase 2: Admin-Interface

**Ziel:** Django Admin für Agenda-Verwaltung

#### 2.1 Admin-Klassen erstellen

**Datei:** `apps/agendas/admin.py`

**AgendaItemInline:**
- TabularInline für AgendaItems im Agenda-Admin
- Zeigt Felder: `title`, `parent`, `sort_order`
- Readonly Felder: `item_number`
- Sortierung nach `sort_order`
- Erlaubt Inline-Editing direkt im Agenda-Admin

**AgendaAdmin:**
- List Display: `meeting`, `item_count`, `is_editable`, `is_finalized`
- List Filter: `meeting__status`, `created_at`
- Search Fields: `meeting__title`, `meeting__meeting_number`
- Readonly Fields: `id`, `created_at`, `updated_at`
- Inlines: `AgendaItemInline`

**Custom Admin-Methoden:**
- `item_count(obj)`: Zeigt Anzahl TOPs
- `is_editable(obj)`: Zeigt ✓/✗ ob editierbar
- `is_finalized(obj)`: Zeigt ✓/✗ ob finalisiert

**AgendaItemRegularAdmin:**
- List Display: `item_number`, `title`, `parent`, `agenda`, `sort_order`
- List Filter: `created_at`
- Search Fields: `title`, `description`, `agenda__meeting__title`
- Readonly Fields: `id`, `item_number`, `item_type`, `created_at`, `updated_at`
- Sortierung: `agenda`, `sort_order`

**Features:**
- Inline-Editing von TOPs direkt im Agenda-Admin
- Read-only Fields für Audit-Trail
- Suchfunktion über Meeting-Titel

---

### Phase 3: Berechtigungen via Migration

**Ziel:** Permissions via Migration erstellen (9999_* Pattern)

#### 3.1 Permissions-Migration erstellen

**Datei:** `apps/agendas/migrations/9999_seed_agenda_permissions.py`

**Struktur:**
- Data Migration mit `RunPython`
- Forward-Funktion: `seed_agenda_permissions(apps, schema_editor)`
- Reverse-Funktion: `reverse_seed_permissions(apps, schema_editor)`

**Permissions zu erstellen (5 Stück):**

| Codename | Name | Description | Category |
|----------|------|-------------|----------|
| `agenda.view` | Tagesordnung ansehen | Tagesordnungen ansehen | agenda |
| `agenda.add_item_regular` | Normalen TOP hinzufügen | Normale TOPs erstellen | agenda |
| `agenda.edit_item_regular` | Normalen TOP bearbeiten | Normale TOPs bearbeiten | agenda |
| `agenda.delete_item_regular` | Normalen TOP löschen | Normale TOPs löschen | agenda |
| `agenda.reorder_items` | TOPs neu anordnen | Reihenfolge und Hierarchie ändern | agenda |

**Rollen-Zuweisungen:**

1. **SYSTEM_ADMIN**: Alle 5 Permissions
2. **CHAIR**: Alle 5 Permissions
3. **VICE_CHAIR**: Alle 5 Permissions
4. **CLERK**: Alle 5 Permissions
5. **MEMBER**: Nur `agenda.view`
6. **SUBSTITUTE**: Keine Permissions
7. **EXTERNAL_MEMBER**: Keine Permissions
8. **GUEST**: Keine Permissions

**Migration Dependencies:**
- `('agendas', '0001_initial')`
- `('roles', '9999_seed_roles_and_permissions')` - Ensures roles exist first

**Implementierung:**
- Loop über Permissions-Liste: `Permission.objects.get_or_create(codename=..., defaults={...})`
- Für jede Rolle: `Role.objects.get(codename=...)` mit `try/except Role.DoesNotExist`
- Permissions zuweisen: `RolePermission.objects.get_or_create(role=..., permission=...)`
- Reverse: `Permission.objects.filter(category='agenda').delete()` (CASCADE löscht RolePermissions)

**Siehe:** Vollständiges Beispiel in `apps/meetings/migrations/9999_seed_meeting_permissions.py` (Zeilen 1-183)

#### 3.2 Migration ausführen

**Commands:**
```bash
python manage.py makemigrations agendas  # Falls noch nicht erstellt
python manage.py migrate agendas
```

**Validierung (Django Shell):**
- Check: `Permission.objects.filter(category='agenda').count()` → Sollte 5 sein
- Check: `Role.objects.get(codename='CHAIR').permissions.filter(category='agenda').count()` → Sollte 5 sein
- Check: `Role.objects.get(codename='MEMBER').permissions.filter(category='agenda').count()` → Sollte 1 sein

---

### Phase 4: Views & Templates

**Ziel:** CRUD-Funktionalität für Agendas/Items, Permission-Checks

#### 4.1 Permission-Mixin erstellen

**Datei:** `apps/agendas/mixins.py`

**AgendaPermissionMixin:**
Mixin für Permission-Checks in Agenda-Views. Prüft Berechtigungen basierend auf Committee-Membership.

**Attribute:**
- `required_permission`: String mit Permission-Codename (z.B. 'agenda.edit_item_regular')

**Methoden:**

1. **`dispatch(request, *args, **kwargs)`**
   - Überschreibt dispatch-Methode
   - Ruft `has_permission()` auf
   - Wirft PermissionDenied wenn keine Berechtigung

2. **`has_permission(request) -> bool`**
   - Prüft ob `required_permission` gesetzt ist
   - Admin/Superuser haben immer Zugriff (Early Return)
   - Holt Agenda/Meeting aus View-Kontext
   - Holt Committee aus Meeting
   - Sucht aktive Membership für User in diesem Committee
   - Prüft ob Role des Membership die erforderliche Permission hat
   - Gibt True/False zurück

**Rationale:**
- Wiederverwendbares Mixin für alle Agenda-Views
- Integriert mit bestehendem Roles/Permissions-System
- Berücksichtigt Committee-Kontext (nicht global)

#### 4.2 Forms erstellen

**Datei:** `apps/agendas/forms.py`

**AgendaItemRegularForm:**
Form für normale TOPs. Basiert auf ModelForm.

**Meta:**
- Model: `AgendaItemRegular`
- Fields: `title`, `description`, `parent`
- Widgets: Bootstrap-Styles für alle Felder
- Labels: Deutsche Beschriftungen

**Hinweise:**
- `item_number` ist NICHT im Form (wird automatisch berechnet)
- `sort_order` ist NICHT im Form (wird bei Create automatisch gesetzt)

**`__init__` Methode:**
- Akzeptiert `agenda` Parameter
- Filtert `parent` Dropdown: Nur TOPs der gleichen Agenda
- Verhindert Cross-Agenda Parent-Zuweisungen

#### 4.3 Views implementieren

**Datei:** `apps/agendas/views.py`

Alle Views verwenden:
- `LoginRequiredMixin`: Nur eingeloggte User
- `AgendaPermissionMixin`: Permission-Checks
- Class-Based Views (Django Standard)

**AgendaItemCreateView:**
- Erbt von CreateView
- Required Permission: `agenda.add_item_regular`
- Template: `agendas/item_form.html`

**Besonderheiten:**
1. `get_form_kwargs()`: Übergibt Agenda an Form (für Parent-Filter)
2. `get_context_data()`: Fügt Agenda zu Context hinzu
3. `form_valid()`:
   - Setzt `agenda` Foreign Key
   - Berechnet automatisch `sort_order` (letzte Position + 1.0)
   - Speichert Item
   - Ruft `agenda.recalculate_item_numbers()` auf
4. `get_success_url()`: Redirect zu Meeting-Detail (wo Agenda eingebettet ist)

**AgendaItemUpdateView:**
- Erbt von UpdateView
- Required Permission: `agenda.edit_item_regular`
- Template: `agendas/item_form.html`
- Nach Save: Redirect zu Meeting-Detail

**AgendaItemDeleteView:**
- Erbt von DeleteView
- Required Permission: `agenda.delete_item_regular`
- Nach Delete: Trigger Neuberechnung der Nummern, Redirect zu Meeting-Detail

**reorder_items (AJAX-Endpoint):**
Function-Based View für Drag-and-Drop Sortierung.

**Request:**
- Method: POST
- Data: JSON mit `item_order` Array
  - Jedes Element: `{id: UUID, parent_id: UUID|null}`

**Logik:**
1. Permission-Check: `agenda.reorder_items`
2. Hole Agenda
3. Prüfe `agenda.is_editable` (Fehler wenn nicht editierbar)
4. Iteriere durch `item_order` Array
5. Update `sort_order` (Index) und `parent_id` für jedes Item
6. Rufe `agenda.recalculate_item_numbers()` auf
7. Hole aktualisierte `item_numbers` aller Items
8. Gib JSON zurück: `{status: 'success', item_numbers: {uuid: number, ...}}`

**Response:**
JavaScript nutzt `item_numbers` Map um DOM dynamisch zu aktualisieren (KEIN Reload!).

#### 4.4 URLs definieren

**Datei:** `apps/agendas/urls.py`

URL-Patterns:
- `items/add/`: AgendaItemCreateView (needs agenda_id param)
- `items/<uuid:pk>/edit/`: AgendaItemUpdateView
- `items/<uuid:pk>/delete/`: AgendaItemDeleteView
- `<uuid:agenda_id>/reorder/`: reorder_items (AJAX)

**In config/urls.py einbinden:**
Include unter `/agendas/` Pfad.

#### 4.5 Templates erstellen

**Datei:** `apps/agendas/templates/agendas/item_form.html`

**Aufbau:**
- Extends `base.html`
- Title: "TOP bearbeiten" oder "Neuen TOP erstellen"
- Formular mit CSRF-Token
- Bootstrap-Styles
- Info-Box: Erklärt automatische Nummerierung und Parent-Auswahl
- Buttons: "Speichern", "Abbrechen" (zu Meeting-Detail)

**Hinweis:**
Die Agenda-Liste wird NICHT in einem separaten Template gerendert, sondern **direkt in der Meeting-Detail-View eingebettet** (siehe Abschnitt 5.2).

#### 4.6 JavaScript (Drag-and-Drop mit dynamischer Nummerierung)

**Datei:** `apps/agendas/static/agendas/agenda_reorder.js`

**Funktionalität:**

1. **CSRF-Token Helper:**
   - Funktion `getCookie(name)` liest CSRF-Token aus Cookie
   - Standard Django-Pattern: Iteriert durch `document.cookie.split(';')`
   - Sucht Cookie mit Name `csrftoken`
   - Dekodiert mit `decodeURIComponent()`
   - Speichert in Variable: `const csrftoken = getCookie('csrftoken');`

2. **Sortable.js Integration:**
   - Initialisiere Sortable auf `#agenda-items-list` Container
   - Options:
     - `handle: '.handle'` - Nur am ☰-Symbol greifen
     - `ghostClass: 'sortable-ghost'` - CSS-Klasse für visuelles Feedback
     - `animation: 150` - Smooth Animation (150ms)
     - `onEnd: function(evt) { ... }` - Event-Handler

3. **onEnd Event-Handler:**
   - Wird aufgerufen wenn User Item loslässt
   - Sammelt neue Reihenfolge aller Items aus DOM
   - Erstellt Array: `[{id: uuid, parent_id: uuid|null, sort_order: index}, ...]`
   - Sendet AJAX-Request an `/agendas/<agenda_id>/reorder/` Endpoint

4. **AJAX-Request (Fetch API):**
   - Method: `POST`
   - Headers:
     - `'Content-Type': 'application/json'`
     - `'X-CSRFToken': csrftoken` (aus Cookie)
   - Body: `JSON.stringify({ item_order: itemOrder })`
   - Response-Handling:
     - Success: `data.status === 'success'` → Ruft `updateItemNumbers(data.item_numbers)` auf
     - Error: Zeigt Toast-Nachricht (z.B. `showToast('Fehler beim Sortieren', 'error')`)
   - Catch: Netzwerkfehler → Console-Log + Toast

5. **updateItemNumbers(itemNumbers) Funktion:**
   - Parameter: Map `{item_uuid: "neue_nummer", ...}`
   - Iteriert durch alle `<li>` Elemente mit `data-item-id` Attribut
   - Findet `<strong>` Element (enthält Nummer)
   - Updated `textContent` auf neue Nummer aus Map
   - **KEIN Reload** → Smooth UX ohne Seitenflackern

**Phase 2 Erweiterung - Nested Sortable:**
- Aktuell: Flaches Drag-and-Drop (nur Reihenfolge ändern, Parent manuell im Form)
- Phase 2: Nested Sortable mit Sortable.js
  - Option `group: 'nested'` - Ermöglicht Verschachtelung
  - Option `fallbackOnBody: true` - Besseres Drag-Verhalten
  - Items können in andere Items **hinein** gezogen werden (visuell verschachtelt)
  - Beispiel: TOP 2 in TOP 1 ziehen → wird automatisch zu TOP 1.3
  - Komplexere Event-Handler für Parent-Änderungen
  - Siehe: Sortable.js Dokumentation - Nested Sortables Example

---

### Phase 5: Helper-Funktionen & Integration

**Ziel:** Auto-Agenda-Erstellung bei Meeting, Helper-Methoden, Meeting-Integration

#### 5.1 Signal: Auto-Agenda bei Meeting-Erstellung

**Datei:** `apps/agendas/signals.py`

**Struktur:**
- Import: `from django.db.models.signals import post_save`
- Import: `from django.dispatch import receiver`
- Import: `from apps.meetings.models import Meeting`
- Import: `from .models import Agenda`

**Signal-Handler:**
- Decorator: `@receiver(post_save, sender=Meeting)`
- Funktion: `def create_agenda_for_meeting(sender, instance, created, **kwargs):`
- Docstring: Google-Style mit Args-Beschreibung
- Logik: `if created:` (NICHT `if created == True:`)
  - `Agenda.objects.create(meeting=instance)`

**Datei:** `apps/agendas/apps.py`

**AppConfig:**
- Class: `AgendasConfig(AppConfig)`
- Attribute:
  - `default_auto_field = 'django.db.models.BigAutoField'`
  - `name = 'apps.agendas'`
  - `verbose_name = 'Tagesordnungen'`
- Methode: `def ready(self):`
  - Docstring: Erklärt Signal-Registrierung
  - Import: `import apps.agendas.signals  # noqa: F401`
  - Kommentar: "This ensures signals are registered before any models are used."

**Rationale:**
- Automatische Agenda-Erstellung → User muss nicht daran denken
- Garantiert dass jedes Meeting eine Agenda hat
- Signal wird in `ready()` registriert (Django Best Practice)
- `noqa: F401` verhindert Linter-Warnung für "unused import"

#### 5.2 Meeting-Integration

**Meeting-Model erweitern:**

**Datei:** `apps/meetings/models.py`

**Neue Properties:**

1. **`has_agenda`**
   - Prüft ob `hasattr(self, 'agenda')`
   - Gibt True/False zurück

2. **`agenda_finalized`**
   - Gibt `self.has_agenda and self.agenda.is_finalized` zurück

**Meeting-Detail-Template erweitern:**

**Datei:** `apps/meetings/templates/meetings/detail.html`

**WICHTIG:** Agenda wird **direkt eingebettet**, KEIN separater "Tagesordnung anzeigen" Button!

**Position:** Nach dem Meeting-Header (ca. Zeile 45-50)

**Struktur:**

1. **Outer Container:**
   - Bootstrap: `<div class="row mt-4">` → `<div class="col-12">` → `<div class="card">`

2. **Card-Header:**
   - Title: `<h5>Tagesordnung</h5>`
   - Status-Badge (conditional):
     - `{% if meeting.agenda.is_finalized %}` → Badge `bg-success`: "Finalisiert"
     - `{% elif meeting.status == 'IN_PROGRESS' %}` → Badge `bg-warning text-dark`: "Sitzung läuft - Editierbar"
     - `{% else %}` → Badge `bg-secondary`: "Entwurf"

3. **Card-Body - Items vorhanden:**
   - Check: `{% if meeting.agenda.agendaitemregular_items.exists %}`
   - Liste: `<ul id="agenda-items-list" class="list-group">`
   - Loop: `{% for item in meeting.agenda.agendaitemregular_items.all %}`
   - List-Item: `<li class="list-group-item d-flex justify-content-between align-items-start" data-item-id="{{ item.id }}">`
   - **Hierarchische Einrückung:**
     - `{% if item.parent %}style="padding-left: {{ item.item_number|count_dots|add:2 }}rem;"{% endif %}`
     - Filter `count_dots` zählt Punkte in `item_number` (z.B. "1.2.3" → 2 Punkte)
   - **Item-Content:**
     - Drag-Handle (conditional): `{% if can_reorder_agenda and meeting.agenda.is_editable %}` → `<span class="handle">☰</span>`
     - Nummer + Titel: `<strong>{{ item.item_number }}</strong> {{ item.title }}`
     - Beschreibung (optional): `{% if item.description %}` → `<p class="text-muted">{{ item.description|truncatewords:20 }}</p>`
   - **Action-Buttons (conditional):**
     - `{% if can_edit_agenda and meeting.agenda.is_editable %}`
     - Button-Group: "Bearbeiten" (URL: `agendas:item_edit`), "Löschen" (URL: `agendas:item_delete`, onclick confirm)

4. **Card-Body - Keine Items:**
   - Check: `{% else %}`
   - Alert: `<div class="alert alert-info">` mit Icon + Text "Noch keine Tagesordnungspunkte vorhanden."
   - Link (conditional): `{% if can_add_agenda_item and meeting.agenda.is_editable %}` → "Jetzt erstellen"

5. **Add-Button (am Ende):**
   - Check: `{% if can_add_agenda_item and meeting.agenda.is_editable %}`
   - Button: `<a href="{% url 'agendas:item_create' %}?agenda={{ meeting.agenda.id }}" class="btn btn-success">`
   - Text: "+ Neuen TOP hinzufügen"

6. **Sortable.js Script (conditional):**
   - Check: `{% if can_reorder_agenda and meeting.agenda.is_editable %}`
   - CDN: `<script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>`
   - Custom Script: `<script src="{% static 'agendas/agenda_reorder.js' %}"></script>`
   - Init: `<script>const agendaId = '{{ meeting.agenda.id }}'; initAgendaReorder(agendaId);</script>`

**Template-Filter für Einrückung:**

**Datei:** `apps/agendas/templatetags/agenda_tags.py`

**Struktur:**
- Ordner erstellen: `apps/agendas/templatetags/` mit `__init__.py`
- Import: `from django import template`
- Register: `register = template.Library()`
- Filter: `@register.filter` → `def count_dots(value):` → `return str(value).count('.')`
- Docstring: "Count dots in item_number for indentation (e.g., '1.2.3' → 2 dots)."

**Django findet Filter automatisch wenn:**
- Ordner `templatetags/` existiert mit `__init__.py`
- App in `INSTALLED_APPS`
- Template lädt Filter: `{% load agenda_tags %}` (am Anfang des Templates)

**Meeting-Detail-View erweitern:**

**Datei:** `apps/meetings/views.py`

**MeetingDetailView - `get_context_data()` Methode:**

**Context-Variablen hinzufügen:**
- `can_add_agenda_item`: Ruft `user_has_permission('agenda.add_item_regular', committee)` auf
- `can_edit_agenda`: Ruft `user_has_permission('agenda.edit_item_regular', committee)` auf
- `can_reorder_agenda`: Ruft `user_has_permission('agenda.reorder_items', committee)` auf

**Rationale:**
- Template kann Buttons conditional rendern
- Permission-Logik zentral in View (nicht im Template)

**Hinweis:** Die separate `AgendaDetailView` kann optional bleiben für Stand-Alone Agenda-Ansicht, aber primär wird Agenda direkt im Meeting angezeigt.

#### 5.3 Permission-Helper erweitern

**Datei:** `apps/agendas/mixins.py`

**AgendaPermissionMixin - Erweiterte `has_permission()` Methode:**

Die Permission-Check Logik muss BA-Mitglieder berücksichtigen. Analog zur Meetings-App wird geprüft, ob der User im zugehörigen Betriebsausschuss Mitglied ist.

**Methoden-Signatur:**
- `def has_permission(self, request) -> bool:`

**Docstring:**
- Google-Style
- Erklärt BA-Sonderregel: "Regular MEMBER role has only 'agenda.view' permission, BUT: If user is member of the Betriebsausschuss (committee_type='COMMITTEE'), they get extended permissions"

**Logik (Schritt für Schritt):**

1. **Guard Clause - Superuser/Staff:**
   - `if request.user.is_superuser or request.user.is_staff:` → `return True`

2. **Context holen:**
   - `agenda = self.get_agenda()` (Methode muss in View implementiert werden)
   - `committee = agenda.meeting.committee`

3. **Standard Permission-Check:**
   - Query: `Membership.objects.filter(user=request.user, committee=committee, is_active=True).select_related('role')`
   - Loop durch Memberships:
     - `if membership.role:`
       - Check: `membership.role.permissions.filter(codename=self.required_permission).exists()`
       - `if has_perm:` → `return True`

4. **BA-Sonderregel (nur für MAIN Committee):**
   - `if committee.committee_type == 'MAIN':`
   - Query Betriebsausschuss: `committee.subcommittees.filter(committee_type='COMMITTEE', is_active=True).first()`
   - `if betriebsausschuss:`
     - Query BA-Memberships: `Membership.objects.filter(user=request.user, committee=betriebsausschuss, is_active=True).select_related('role')`
     - Loop durch BA-Memberships (analog zu Schritt 3)
     - Check Permission, `if has_perm:` → `return True`

5. **Fallback:**
   - `return False`

**Rationale:**
- Wiederverwendbares Mixin für alle Agenda-Views
- Integriert mit bestehendem Roles/Permissions-System
- Berücksichtigt Committee-Kontext (nicht global)
- **BA-Logik:** Analog zu Meetings-App (siehe `apps/meetings/models.py` Zeilen 416-438 - `user_can_create()`)
- Keine zusätzlichen Felder/Flags nötig - nutzt bestehende Committee-Hierarchie

---

## 5. Testing-Strategie

### 5.1 Unit-Tests

**Datei:** `apps/agendas/tests/test_models.py`

**Test-Klassen:**

1. **AgendaModelTest:**
   - Test Agenda-Erstellung
   - Test Properties (`is_editable`, `is_finalized` basierend auf Meeting-Status)
   - Test `item_count` Property
   - Test `recalculate_item_numbers` Methode

2. **AgendaItemRegularTest:**
   - Test Item-Erstellung
   - Test automatische Nummerierung (1, 2, 3)
   - Test hierarchische Nummerierung (1, 1.1, 1.2, 2, 2.1, 2.1.1)
   - Test Parent-Child Beziehung
   - Test CASCADE Delete (Parent löschen → Kinder gelöscht)

**Datei:** `apps/agendas/tests/test_views.py`

**Test-Klassen:**

1. **AgendaItemCreateViewTest:**
   - Test Permission-Check (User ohne Permission → 403)
   - Test Item-Erstellung (mit Permission → Success)
   - Test automatische `sort_order` Berechnung
   - Test Neuberechnung der Nummern nach Create

2. **AgendaItemUpdateViewTest:**
   - Test Permission-Check
   - Test Item-Update
   - Test Parent ändern (Nummerierung muss neu berechnet werden)

3. **AgendaItemDeleteViewTest:**
   - Test Permission-Check
   - Test Item-Delete
   - Test Neuberechnung der Nummern nach Delete

4. **ReorderItemsViewTest:**
   - Test Permission-Check
   - Test Reorder-Request (AJAX)
   - Test Response enthält korrekte `item_numbers`
   - Test editierbar-Check (finalisierte Agenda → Fehler)

### 5.2 Test-Commands

**Commands:**
```bash
# Alle Tests
python manage.py test apps.agendas

# Mit Coverage
coverage run --source='apps/agendas' manage.py test apps.agendas
coverage report
```

---

## 6. Zukünftige Erweiterungen

### Phase 2: Beschlüsse (Resolutions)

**Neue Modelle:**
- `AgendaItemResolution(AgendaItem)`: Beschluss-TOP mit Abstimmungslogik
- `ResolutionVote`: Abstimmungs-Ergebnisse

**Neue Permissions:**
- `agenda.add_item_resolution`
- `agenda.edit_item_resolution`
- `agenda.vote_on_resolution`

**Features:**
- Beschlusstext-Editor
- Abstimmungs-Modus (offen/geheim)
- Live-Voting Interface

### Phase 3: Wahlen (Elections)

**Neue Modelle:**
- `AgendaItemElection(AgendaItem)`: Wahl-TOP
- `ElectionCandidate`: Kandidaten
- `ElectionVote`: Stimmen

**Neue Permissions:**
- `agenda.add_item_election`
- `agenda.conduct_election`

**Features:**
- Kandidaten-Verwaltung
- Wahlmodus (offene Liste, geheime Wahl)
- Stimmzettel-Generator

### Phase 4: Vorlagen (Templates)

**Neue Modelle:**
- `AgendaTemplate`: Vorlage für wiederkehrende Agendas
- `AgendaTemplateItem`: Vorlage-TOPs

**Features:**
- Vorlagen-Bibliothek
- One-Click Agenda-Erstellung aus Vorlage
- Template-Sharing zwischen Committees

---

## 7. Zusammenfassung

### 7.1 Implementierte Funktionen (Phase 1)

| Feature | Beschreibung |
|---------|--------------|
| **Agenda-Modell** | OneToOne zu Meeting, Finalisierung automatisch via Meeting-Status |
| **AgendaItemRegular** | Normale TOPs mit Titel, Beschreibung, hierarchischer Struktur |
| **Hierarchische Nummerierung** | Automatisch: 1, 1.1, 1.2, 2, 2.1, 2.1.1, etc. |
| **Drag-and-Drop Sortierung** | Sortable.js für Reihenfolge und Hierarchie, dynamisches Update ohne Reload |
| **CRUD-Views** | Erstellen, Bearbeiten, Löschen von TOPs |
| **Permission-System** | Granulare Berechtigungen pro Modul |
| **Admin-Interface** | Django Admin für Agenda/Items |
| **Auto-Agenda-Erstellung** | Signal erstellt Agenda bei neuem Meeting |
| **Auto-Finalisierung** | Agenda wird finalisiert wenn Meeting-Status = SENT |
| **Auto-Öffnung** | Agenda wird wieder editierbar wenn Meeting-Status = IN_PROGRESS |
| **Meeting-Integration** | Agenda direkt in Meeting-Detail-View eingebettet (kein separater Button) |

### 7.2 Permissions & Rollen

**Permissions (Phase 1):**

| Permission | CHAIR | VICE_CHAIR | CLERK | MEMBER | MEMBER (BA) | SUBSTITUTE | EXTERNAL | GUEST |
|------------|-------|------------|-------|--------|-------------|-----------|----------|-------|
| `agenda.view` | ✓ | ✓ | ✓ | ✓ | ✓ | - | - | - |
| `agenda.add_item_regular` | ✓ | ✓ | ✓ | - | ✓ | - | - | - |
| `agenda.edit_item_regular` | ✓ | ✓ | ✓ | - | ✓ | - | - | - |
| `agenda.delete_item_regular` | ✓ | ✓ | ✓ | - | ✓ | - | - | - |
| `agenda.reorder_items` | ✓ | ✓ | ✓ | - | ✓ | - | - | - |

**Zugriffsrechte-Details:**
- **Vorsitz/Stellv. Vorsitz/Schriftführung**: Volle Kontrolle über Agenda
- **Mitglieder (normal)**: Nur Leserechte
- **Mitglieder (Betriebsausschuss)**: Erweiterte Rechte wie Vorsitz (via Committee-Type Check)
  - BA-Mitglieder = Mitglieder in einem Committee vom Typ `COMMITTEE`
  - Permission-Check prüft zusätzlich Membership im zugehörigen BA
- **Ersatzmitglieder**: KEINE Rechte (Einspringen-Logik kommt später)
- **Externe/Gäste**: KEINE Rechte (Einladungssystem kommt später)

### 7.3 Prozessablauf

**Szenario: Vorbereitung und Durchführung einer Sitzung**

#### **Phase 1: Meeting erstellen**
- **Wer:** Vorsitz oder Schriftführung
- **Aktion:** Meeting wird in `apps/meetings` erstellt (Status: DRAFT)
- **System:** Signal `create_agenda_for_meeting` erstellt automatisch leere Agenda

#### **Phase 2: Agenda befüllen**
- **Wer:** Schriftführung (oder Vorsitz/Stellv. Vorsitz/BA-Mitglied)
- **Ablauf:**
  1. Navigiere zu Meeting → Tagesordnung ist direkt sichtbar (eingebettet)
  2. Klick auf "+ Neuen TOP hinzufügen"
  3. Formular ausfüllen: Titel, Beschreibung (optional), Übergeordneter TOP (optional)
  4. Speichern → TOP erscheint in Liste mit automatischer Nummer (z.B. "1")

#### **Phase 3: Weitere TOPs hinzufügen**
- Schriftführung fügt weitere TOPs hinzu
- System nummeriert automatisch: 1, 2, 3, ...
- Für Unterpunkte: Parent-Dropdown auswählen → System nummeriert z.B. 1.1, 1.2, 1.2.1, etc.

#### **Phase 4: Reihenfolge ändern (Drag-and-Drop)**
- **Aktion:** Greift TOP am ☰-Handle, zieht nach oben/unten, loslassen
- **System:**
  - AJAX-Request an Server
  - Aktualisiert `sort_order` aller Items
  - Berechnet `item_number` neu
  - Sendet neue `item_numbers` zurück
  - JavaScript aktualisiert Nummern **dynamisch** (KEIN Reload!)

#### **Phase 5: TOPs bearbeiten/löschen**
- **Bearbeiten:** Klick "Bearbeiten" → Titel/Beschreibung ändern → Speichern
- **Löschen:** Klick "Löschen" → Bestätigung → Weg
- **System:** Neuberechnung der `item_number` nach jeder Änderung

#### **Phase 6: Einladung versenden (Auto-Finalisierung)**
- **Wer:** Vorsitz
- **Aktion:**
  - Klick "Einladung versenden" (Meeting-Funktion)
  - **Meeting-Status wechselt zu SENT**
- **System:**
  - `agenda.is_finalized` wird automatisch `True` (Property basierend auf Meeting-Status)
  - `agenda.is_editable` wird `False`
  - Alle Bearbeiten/Löschen-Buttons verschwinden
  - Drag-and-Drop wird deaktiviert
  - Badge: "Finalisiert"

#### **Phase 7: Sitzung durchführen (Agenda wieder editierbar)**
- **Wer:** Vorsitz startet Sitzung
- **Aktion:** Meeting-Status wechselt zu IN_PROGRESS
- **System:**
  - `agenda.is_editable` wird wieder `True`
  - Bearbeiten/Löschen-Buttons erscheinen wieder
  - Badge: "Sitzung läuft - Editierbar"
  - **Rationale:** Während der Sitzung können spontan TOPs hinzugefügt/geändert werden

#### **Phase 8: Nach der Sitzung**
- **Wer:** Vorsitz beendet Sitzung
- **Aktion:** Meeting-Status wechselt zu COMPLETED
- **System:**
  - Agenda bleibt als Archiv erhalten
  - Keine Bearbeitung mehr möglich (is_editable = False)
  - Protokoll-Generierung basierend auf finaler Agenda (spätere Phase)

---

### 7.4 User-Szenarien (Detailliert)

#### **Szenario 1: Schriftführung bereitet Sitzung vor**

**Kontext:** Anna ist Schriftführerin im Betriebsrat.

1. **Meeting öffnen:**
   - Anna öffnet das Meeting "BR-Sitzung Mai 2026"
   - **Sieht direkt die Tagesordnung** im unteren Bereich der Seite (eingebettet)
   - Status-Badge: "Entwurf"

2. **Leere Agenda:**
   - Karte "Tagesordnung" zeigt: "Noch keine Tagesordnungspunkte vorhanden."
   - Button sichtbar: "+ Neuen TOP hinzufügen"

3. **TOP 1 erstellen:**
   - Klick "+ Neuen TOP hinzufügen"
   - Formular ausfüllen:
     - Titel: "Begrüßung und Feststellung der Beschlussfähigkeit"
     - Beschreibung: (leer)
     - Übergeordneter TOP: (leer)
   - Speichern
   - Zurück zur Meeting-Detail-Seite → Tagesordnung zeigt "**1.** Begrüßung und..."

4. **TOP 2 erstellen:**
   - Wieder "+ Neuen TOP hinzufügen"
   - Titel: "Genehmigung der Tagesordnung"
   - Speichern → "**2.** Genehmigung..."

5. **TOP 3 mit Unterpunkten:**
   - TOP 3 erstellen: "Berichte" → "**3.** Berichte"
   - TOP 3.1 erstellen:
     - Titel: "Bericht des Vorsitzenden"
     - **Übergeordneter TOP:** (Dropdown) → "3. Berichte" auswählen
     - Speichern → "**3.1** Bericht des Vorsitzenden"
   - TOP 3.2 erstellen:
     - Titel: "Bericht der Schwerbehindertenvertretung"
     - Übergeordneter TOP: "3. Berichte"
     - Speichern → "**3.2** Bericht der SBV"

6. **Reihenfolge ändern:**
   - Anna merkt: TOP 3.2 sollte vor 3.1
   - Greift TOP 3.2 am ☰-Handle
   - Zieht nach oben (über 3.1)
   - Loslassen
   - **System:** AJAX-Request → Nummern werden **dynamisch aktualisiert** (KEIN Reload!)
   - **Neue Nummerierung sofort sichtbar:** 3.1 = SBV-Bericht, 3.2 = Vorsitzenden-Bericht

7. **TOP löschen:**
   - TOP 3.2 ist doch unnötig
   - Klick "Löschen" → Bestätigung → Weg
   - System berechnet neu → Nur noch 3.1 vorhanden

#### **Szenario 2: Vorsitzender sendet Einladung (Auto-Finalisierung)**

**Kontext:** Max ist Vorsitzender, Anna hat Agenda vorbereitet.

1. **Meeting öffnen und Agenda prüfen:**
   - Max öffnet Meeting
   - **Sieht Tagesordnung direkt** im unteren Bereich (eingebettet)
   - Prüft alle TOPs - Alles OK

2. **Änderung vornehmen:**
   - TOP 1 umbenennen
   - Klick "Bearbeiten" bei TOP 1 → Titel ändern → Speichern

3. **Einladung versenden:**
   - Zurück zum Meeting (oder scrollt nach oben)
   - Klick "Einladung versenden"
   - **System:** Meeting-Status → SENT

4. **Agenda ist automatisch finalisiert:**
   - Max scrollt zur Tagesordnung
   - Badge: "Finalisiert"
   - KEINE Buttons mehr für Bearbeiten/Löschen/Hinzufügen
   - KEIN Drag-and-Drop Handle
   - Agenda ist "eingefroren"

#### **Szenario 3: Normales Mitglied schaut Agenda an**

**Kontext:** Lisa ist normales Mitglied (kein BA-Mitglied).

1. **Meeting öffnen:**
   - Lisa öffnet Meeting
   - **Sieht Tagesordnung direkt** (eingebettet)

2. **Nur Leserechte:**
   - Sieht alle TOPs (nur lesen)
   - KEINE Buttons zum Hinzufügen/Bearbeiten/Löschen
   - KEIN Drag-and-Drop Handle

3. **Warum keine Rechte?**
   - Lisa hat nur Permission `agenda.view`
   - Nur Vorsitz/Stellv./Schriftführung/BA-Mitglieder dürfen bearbeiten

#### **Szenario 4: BA-Mitglied bearbeitet Agenda**

**Kontext:** Tom ist normales Mitglied UND im Betriebsausschuss.

1. **Meeting öffnen:**
   - Tom öffnet Meeting
   - **Sieht Tagesordnung direkt** (eingebettet)
   - **System prüft:** Tom ist im BA → Erweiterte Rechte

2. **Vollzugriff:**
   - Sieht alle Buttons: "Bearbeiten", "Löschen", "+ Neuen TOP"
   - Kann Drag-and-Drop nutzen (☰-Handle sichtbar)
   - **Rationale:** BA-Mitglieder (Mitglieder in Committee vom Typ 'COMMITTEE') haben erweiterte Rechte
   - Permission-Check prüft zusätzlich Membership im Betriebsausschuss

#### **Szenario 5: Während der Sitzung - spontane Änderung**

**Kontext:** Sitzung läuft, Meeting-Status = IN_PROGRESS.

1. **Spontaner Antrag:**
   - Während TOP 4 stellt Mitglied spontanen Antrag
   - Vorsitzender beschließt: Als neuer TOP 5 aufnehmen

2. **Agenda ändern:**
   - Schriftführung hat Meeting offen (parallel zur Sitzung)
   - Scrollt zur Tagesordnung
   - Badge: "Sitzung läuft - Editierbar"
   - Klick "+ Neuen TOP hinzufügen"
   - Titel: "Spontanantrag: Neue Pausenraumausstattung"
   - Speichern → TOP 5 erscheint in der Liste

3. **Warum editierbar?**
   - Meeting-Status = IN_PROGRESS
   - System erlaubt Änderungen während laufender Sitzung
   - **Rationale:** Flexibilität für spontane TOPs

#### **Szenario 6: Ersatzmitglied hat keinen Zugriff**

**Kontext:** Sarah ist Ersatzmitglied.

1. **Meeting öffnen:**
   - Sarah versucht Meeting zu öffnen
   - **System:** Permission denied
   - **Grund:** Ersatzmitglieder haben keine `meeting.view` Permission

2. **Agenda:**
   - Kann Tagesordnung nicht sehen (da Meeting nicht sichtbar)
   - **Später:** Einspringen-Logik gibt temporäre Rechte

#### **Szenario 7: Gast ohne Einladung**

**Kontext:** Michael ist Gast, aber NICHT eingeladen.

1. **Meeting öffnen:**
   - Michael versucht Meeting zu öffnen
   - **System:** Permission denied
   - **Grund:** Gäste haben keine `meeting.view` Permission

2. **Mit Einladung (später):**
   - Einladungssystem kommt später
   - Dann temporäre Rechte für eingeladene Gäste

---

### 7.5 Wichtige Abweichungen von alter 06_agendas.md

| Aspekt | Alte Spec (06_agendas.md) | Neue Spec (04_agendas.md) |
|--------|---------------------------|---------------------------|
| **Finalisierung** | Manueller Button | Automatisch via Meeting-Status |
| **Agenda-Erstellung** | Manuell | Automatisch via Signal |
| **TOP-Nummerierung** | Manuell eingeben | Automatisch berechnet |
| **Hierarchie** | Einfach (1, 2, 3) | Hierarchisch (1, 1.1, 2.1.3) |
| **Mitglieder-Rechte** | Können TOPs vorschlagen | Nur Leserechte (Vorschlagssystem separat) |
| **Öffentlich-Flag** | `is_public` Feld | Entfernt (kommt später für Protokolle) |
| **Ersatzmitglieder** | Leserechte | Keine Rechte |
| **Gäste** | Öffentliche TOPs sehen | Keine Rechte (nur mit Einladung) |
| **UI-Integration** | Separater "Tagesordnung anzeigen" Button | Direkt in Meeting-Detail eingebettet |
| **Drag-and-Drop** | Mit Reload | Ohne Reload (dynamisches Update) |

---

## 8. Code-Style & Best Practices

**Aus `CODE_STYLE_GUIDE.md`:**

1. **Sprache:**
   - Code (Variablen, Funktionen, Klassen): **Englisch**
   - User-facing (Labels, Fehlermeldungen, Templates): **Deutsch**

2. **Type Hints:**
   - Pflicht für alle Funktionen/Methoden
   - Beispiel: `def finalize(self, user: User) -> None:`

3. **Docstrings:**
   - Google-Style für alle Klassen/Methoden
   - Minimum: One-Liner für einfache Funktionen

4. **DRY (Don't Repeat Yourself):**
   - Permission-Checks in Mixins auslagern
   - Queryset-Filter in Custom Managers
   - Gemeinsame Logik extrahieren

5. **Guard Clauses:**
   - Frühe Returns statt tief verschachtelte if-Bedingungen
   - Verbessert Lesbarkeit

---

## 9. Deployment-Checkliste

**Vor Produktiv-Einsatz:**

- [ ] Migrations getestet (`python manage.py migrate --plan`)
- [ ] Permissions-Migration ausgeführt (`9999_seed_agenda_permissions.py`)
- [ ] Unit-Tests laufen durch (`python manage.py test apps.agendas`)
- [ ] Admin-Interface getestet (CRUD Agendas/Items)
- [ ] Permission-Checks validiert (verschiedene Rollen testen)
- [ ] BA-Mitglieder Permission-Check getestet (Committee-Type Logic)
- [ ] Frontend-Tests (Drag-and-Drop, Forms)
- [ ] Signal-Handler getestet (Auto-Agenda bei Meeting)
- [ ] Performance-Check (Queryset Optimierung, `select_related`, `bulk_update`)
- [ ] JavaScript CSRF-Token funktioniert

---

## 10. Offene Fragen / Entscheidungen

1. **Hierarchie-UI für Drag-and-Drop:**
   - Aktuell: Einfaches Drag-and-Drop mit manueller Parent-Auswahl im Form
   - Phase 2: Nested Sortable für visuelles Verschieben in Hierarchie-Ebenen?
   - **Empfehlung:** Phase 1 einfach halten, Nested Sortable in Phase 2

2. **Nummerierungs-Update bei Drag-and-Drop:**
   - **Bereits gelöst:** AJAX-Update ohne Reload
   - JavaScript aktualisiert Nummern dynamisch
   - Smooth UX ohne Seitenflackern

3. **Vorschlagssystem für Mitglieder:**
   - Wann implementieren?
   - Als Flag `is_proposed` am AgendaItem?
   - **Empfehlung:** Separates Feature in Phase 2 (nicht Teil der Basis-Agenda)

4. **Vorlagen-System:**
   - Wann implementieren? (Phase 4)
   - Committee-spezifisch oder global?
   - **Empfehlung:** Committee-spezifisch mit Share-Option

---

## Anhang

### A.1 Datenbankschema (Phase 1)

```
Agenda
  - id (UUID, PK)
  - meeting_id (UUID, FK → meetings.Meeting, UNIQUE)
  - created_at (DateTime)
  - updated_at (DateTime)
  
  # KEINE Felder für is_finalized, finalized_at, finalized_by
  # Diese Info kommt aus Meeting.status via Properties

AgendaItemRegular
  - id (UUID, PK)
  - agenda_id (UUID, FK → agendas.Agenda, CASCADE)
  - parent_id (UUID, FK → self, CASCADE, nullable)
  - item_number (String, max 20) [editable=False, auto-berechnet]
  - title (String, max 500)
  - description (Text)
  - sort_order (Float) [für Drag-and-Drop]
  - item_type (String, max 50) [auto: "AgendaItemRegular"]
  - created_at (DateTime)
  - updated_at (DateTime)
```

### A.2 API-Endpoints (zukünftig)

**REST API (optional in Phase 6):**

```
GET    /api/agendas/<uuid>/              # Agenda abrufen
POST   /api/agendas/<uuid>/items/        # Item erstellen
PATCH  /api/agendas/items/<uuid>/        # Item bearbeiten
DELETE /api/agendas/items/<uuid>/        # Item löschen
POST   /api/agendas/<uuid>/reorder/      # Items neu sortieren
```

### A.3 Referenzen

- **02_committees.md**: Implementierungsplan Gremien
- **03_meetings.md**: Implementierungsplan Sitzungen
- **06_agendas.md**: Alte Agenda-Spezifikation (veraltet, nur Referenz)
- **CODE_STYLE_GUIDE.md**: Code-Konventionen
- **ROLES_PERMISSIONS_MATRIX.md**: Rollen-Berechtigungen

---

**Ende des Implementierungsplans**
