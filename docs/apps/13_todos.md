# App: `todos` - Aufgabenverwaltung

## Übersicht

Verwaltung von Aufgaben aus der Betriebsratsarbeit mit Zuordnung, Fälligkeitsdaten und Verknüpfungen zu Sitzungen, TOPs, Beschlüssen.

## Hauptfunktionen

- Aufgaben erstellen, bearbeiten, löschen, zuweisen
- **Priorität:** HIGH, MEDIUM, LOW
- **Status:** OPEN, IN_PROGRESS, DONE
- **Verknüpfungen:** Sitzungen, TOPs, Beschlüsse, Dokumente
- **Zuordnung:** Einem oder mehreren Mitgliedern
- **Fristenüberwachung:** Automatische Erinnerungen
- **Wiederkehrende Aufgaben:** Konfigurierbar

## Datenmodell

### Todo
- `id`, `title`, `description`, `priority`, `status`, `due_date`
- `committee` (FK, optional), `meeting` (FK, optional)
- `agenda_item`, `resolution`, `document` (FKs, optional)
- `created_by`, `created_at`, `updated_at`
- `is_recurring`, `recurrence_rule` (iCal RRULE)

### TodoAssignment (M:N)
- `id`, `todo` (FK), `assigned_to` (FK → User), `assigned_at`
- **Constraint:** UNIQUE(todo, assigned_to)

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/todos/` | Aufgaben auflisten |
| `/todos/create/` | Erstellen |
| `/todos/<uuid:id>/` | Details |
| `/todos/<uuid:id>/edit/` | Bearbeiten |
| `/todos/<uuid:id>/delete/` | Löschen |
| `/todos/<uuid:id>/status/` | Status ändern |
| `/todos/<uuid:id>/assign/` | Mitglieder zuweisen |

### HTMX
- `/todos/<uuid:id>/status-toggle/` - Status inline ändern (Checkbox)
- `/todos/filter/` - To-Do-Liste live filtern

## Abhängigkeiten

- **accounts** (User)
- **committees** (Committee)
- **meetings** (Meeting)
- **agendas** (AgendaItem)
- **resolutions** (Resolution)
- **documents** (Document)

## Berechtigungen

- `todo.create` - Erstellen
- `todo.edit` - Bearbeiten (Ersteller + Zugewiesene)
- `todo.delete` - Löschen (nur Ersteller + Admin/Vorsitz)
- `todo.view` - Einsehen
- `todo.assign` - Zuweisen

## Templates

- `todos/todo_list.html` (mit Filter: Status, Priorität, Zugewiesen)
- `todos/todo_detail.html`
- `todos/todo_form.html`
- `todos/_todo_row.html` (HTMX)

## Implementierungshinweise

### Fristenüberwachung (Celery)
```python
@periodic_task(run_every=timedelta(hours=6))
def check_todo_deadlines():
    from apps.notifications.utils import notify
    
    upcoming = Todo.objects.filter(
        status__in=['OPEN', 'IN_PROGRESS'],
        due_date__lte=timezone.now() + timedelta(days=2),
        due_date__gte=timezone.now()
    )
    
    for todo in upcoming:
        for assignment in todo.assignments.all():
            notify(
                recipient=assignment.assigned_to,
                notification_type='TODO_REMINDER',
                title=f'Aufgabe fällig: {todo.title}',
                message=f'Die Aufgabe "{todo.title}" ist am {todo.due_date} fällig.',
                related_object=todo
            )
```

### Berechtigungsprüfung für Bearbeitung/Löschung
```python
def can_edit_todo(user, todo):
    # Ersteller darf immer bearbeiten
    if todo.created_by == user:
        return True
    
    # Zugewiesene dürfen bearbeiten
    if TodoAssignment.objects.filter(todo=todo, assigned_to=user).exists():
        return True
    
    # Admin/Vorsitz darf alles
    if user.has_perm('todo.edit') and user.is_admin:
        return True
    
    return False

def can_delete_todo(user, todo):
    # Nur Ersteller, Admin, Vorsitz
    if todo.created_by == user:
        return True
    if user.has_perm('todo.delete') and user.is_admin:
        return True
    return False
```

## Tests

- Unit-Tests für Berechtigungsprüfung
- Integration-Tests für Zuordnung
- Celery-Task-Tests für Fristenüberwachung
- HTMX-Tests für Status-Toggle
