# Rollen & Permissions Matrix

Diese Datei definiert welche Permissions jede Rolle standardmäßig hat.
Verwendet als Basis für die Anpassung der Migrations-Dateien in `apps/*/migrations/9999_*.py`.

**Legende:**

- ✓ = Permission ist zugewiesen
- ✗ = Permission ist NICHT zugewiesen

---

## System-Rollen

### SYSTEM_ADMIN

- Beschreibung: Vollständige System-Administration
- Typ: SYSTEM
- **Erhält ALLE Permissions automatisch**

### USER

- Beschreibung: Standard-Benutzer ohne besondere Rechte
- Typ: SYSTEM
- **Erhält KEINE Permissions**

---

## Gremiums-Rollen (COMMITTEE)

### CHAIR (Vorsitz)

- Beschreibung: Vorsitzender des Gremiums
- auto_include_in_ba: Ja

### VICE_CHAIR (Stellv. Vorsitz)

- Beschreibung: Stellvertretender Vorsitzender
- auto_include_in_ba: Ja

### CLERK (Schriftführung)

- Beschreibung: Schriftführer des Gremiums
- auto_include_in_ba: Nein

### MEMBER (Mitglied)

- Beschreibung: Reguläres Gremiumsmitglied
- auto_include_in_ba: Nein

### SUBSTITUTE (Ersatzmitglied)

- Beschreibung: Ersatzmitglied für reguläre Mitglieder
- auto_include_in_ba: Nein

### EXTERNAL_MEMBER (Externes Mitglied)

- Beschreibung: Externes Mitglied ohne Stimmrecht
- auto_include_in_ba: Nein

### GUEST (Gast)

- Beschreibung: Gast ohne Stimmrecht
- auto_include_in_ba: Nein

---

## APP: ROLES (System & Rollen-Verwaltung)

| Permission                 | Codename                | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|----------------------------|-------------------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Systemweiter Admin-Zugriff | system.admin            | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Benutzer verwalten         | system.manage_users     | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Rolle erstellen            | role.create             | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Rolle bearbeiten           | role.edit               | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Rolle löschen              | role.delete             | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Berechtigungen zuweisen    | role.assign_permissions | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Rollen einsehen            | role.view               | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Rolle zuweisen             | role.assign_to_member   | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |

---

## APP: COMMITTEES (Gremien-Verwaltung)

| Permission               | Codename                 | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|--------------------------|--------------------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Gremium erstellen        | committee.create         | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Gremium bearbeiten       | committee.edit           | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Gremiumsdetails einsehen | committee.view           | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✓          | ✓               | ✓     |
| Alle Gremien einsehen    | committee.view_all       | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Gremium löschen          | committee.delete         | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Mitglieder verwalten     | committee.manage_members | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Mitgliederliste einsehen | committee.view_members   | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✓          | ✓               | ✓     |

---

## APP: MEETINGS (Sitzungs-Verwaltung)

| Permission                           | Codename                    | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|--------------------------------------|-----------------------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Sitzung erstellen (eigenes Gremium)  | meeting.create              | ✓            | ✗    | ✓     | ✓          | ✓     | ✓¹     | ✗          | ✗               | ✗     |
| Sitzung in anderen Gremien erstellen | meeting.create_other        | ✓            | ✗    | ✗     | ✗          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Sitzung anzeigen                     | meeting.view                | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✓               | ✓     |
| Sitzung bearbeiten                   | meeting.edit                | ✓            | ✗    | ✓     | ✓          | ✗     | ✓¹     | ✗          | ✗               | ✗     |
| Entwurf löschen                      | meeting.delete_draft        | ✓            | ✗    | ✓     | ✓          | ✓     | ✓¹     | ✗          | ✗               | ✗     |
| Einladung versenden                  | meeting.send_invitation     | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Sitzung beginnen                     | meeting.start_meeting       | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Sitzung abschließen                  | meeting.complete_meeting    | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Als Sitzungsleitung wählbar          | meeting.is_chair            | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |
| Als Schriftführung wählbar           | meeting.is_clerk            | ✓            | ✗    | ✗     | ✗          | ✓     | ✗      | ✗          | ✗               | ✗     |

¹: Wenn in dem Gremium Betriebsausschuss

---

## APP: AGENDAS (Tagesordnungs-Verwaltung)

| Permission                 | Codename                     | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|----------------------------|------------------------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Tagesordnung ansehen       | agenda.view                  | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Normalen TOP hinzufügen    | agenda.add_item_regular      | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| Normalen TOP bearbeiten    | agenda.edit_item_regular     | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| Normalen TOP löschen       | agenda.delete_item_regular   | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| TOPs neu anordnen          | agenda.reorder_items         | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |

---

## APP: ELECTIONS (Wahl-Verwaltung)

| Permission         | Codename        | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|--------------------|-----------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Wahl erstellen     | election.create | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| Wahl anzeigen      | election.view   | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Wahl bearbeiten    | election.edit   | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| Wahl löschen       | election.delete | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |

---

## APP: RESOLUTIONS (Beschluss-Verwaltung)

| Permission                           | Codename                         | SYSTEM_ADMIN | USER | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL_MEMBER | GUEST |
|--------------------------------------|----------------------------------|--------------|------|-------|------------|-------|--------|------------|-----------------|-------|
| Beschluss erstellen                  | resolution.create                | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Beschluss bearbeiten                 | resolution.edit                  | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Beschluss während Sitzung bearbeiten | resolution.edit_during_meeting   | ✓            | ✗    | ✓     | ✓          | ✓     | ✗      | ✗          | ✗               | ✗     |
| Beschluss löschen                    | resolution.delete                | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Beschluss anzeigen                   | resolution.view                  | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Beschluss vorschlagen                | resolution.propose               | ✓            | ✗    | ✓     | ✓          | ✓     | ✓      | ✗          | ✗               | ✗     |
| Beschluss beschließen/ablehnen       | resolution.decide                | ✓            | ✗    | ✓     | ✓          | ✗     | ✗      | ✗          | ✗               | ✗     |

---

## Hinweise zur Nutzung

1. **SYSTEM_ADMIN** erhält automatisch ALLE Permissions (siehe Code in den Migrations)
2. **USER** erhält standardmäßig KEINE Permissions
3. Die Tabellen zeigen den **aktuellen Stand** aus den Migrations-Dateien
4. Zum Anpassen der Permissions:
    - Diese Datei bearbeiten (✓/✗ setzen wie gewünscht)
    - Dann die entsprechenden `9999_*.py` Migrations-Dateien anpassen

5. **auto_include_in_ba**: Definiert ob Rolle automatisch in Betriebsausschuss-Gremien verfügbar ist
    - CHAIR: Ja
    - VICE_CHAIR: Ja
    - Alle anderen: Nein

---
