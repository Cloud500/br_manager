# 03 – Funktionalitäten

## 3.1 Modulübersicht

| Modul                      | App-Name        | Beschreibung                                                |
|----------------------------|-----------------|-------------------------------------------------------------|
| Tagesordnungen             | `agendas`       | Erstellung, Verwaltung und Vorlagen für Tagesordnungen      |
| Protokolle                 | `minutes`       | Protokollerstellung, Freigabe-Workflow und Versionierung    |
| Anwesenheitsverwaltung     | `attendance`    | Digitale Anwesenheitsbestätigung und Ersatzmitglieder-Logik |
| Dokumentenmanagement       | `documents`     | DMS mit Versionierung und Zugriffssteuerung                 |
| Beschlusssystem            | `resolutions`   | Abstimmungen, Wahlen und Beschlussdokumentation             |
| Ausschussverwaltung        | `committees`    | Verwaltung von Gremien und Ausschüssen                      |
| Rollen- & Rechteverwaltung | `roles`         | Dynamische Rollen und Berechtigungen konfigurieren          |
| Kalender                   | `calendar_mgmt` | Terminverwaltung und Kalenderintegration                    |
| Benachrichtigungen         | `notifications` | E-Mail- und In-App-Benachrichtigungen                       |

---

## 3.2 Tagesordnungen (Modul: `agendas`)

### 3.2.1 Erstellen und Verwalten

**Beschreibung:** Vollständiger Lebenszyklus einer Tagesordnung – von der Erstellung bis zur Finalisierung.

**Funktionen:**

- **Erstellen:** Neue Tagesordnung für eine Sitzung anlegen mit Datum, Uhrzeit, Ort und zugeordnetem Gremium/Ausschuss.
- **Tagesordnungspunkte (TOP):** Hinzufügen, Bearbeiten, Löschen und Umsortieren von TOPs per Drag-and-Drop.
- **TOP-Typen:**
    - Regulärer TOP (Bericht, Diskussion, Information)
    - Beschluss-TOP (verknüpft mit Abstimmung)
    - Wahl-TOP (verknüpft mit Wahlverfahren)
    - Protokollgenehmigung (automatisch generiert, siehe 3.3)
- **Anhänge:** Dokumente können an einzelne TOPs angehängt werden (Verknüpfung mit DMS).
- **Status-Workflow:**

```
Entwurf → In Bearbeitung → Freigegeben → Versandt → Abgeschlossen
```

- **Bearbeitung:** Tagesordnungen im Status „Entwurf" und „In Bearbeitung" sind editierbar.
- **Löschung:** Nur im Status „Entwurf" möglich. Abgeschlossene Tagesordnungen werden archiviert.

### 3.2.2 Vorlagen

**Beschreibung:** Wiederverwendbare Vorlagen für regelmäßige Sitzungen.

**Funktionen:**

- **Vorlagen erstellen:** Aus bestehender Tagesordnung oder manuell.
- **Standard-TOPs:** Vorlagen enthalten vordefinierte TOPs (z. B. „Genehmigung des letzten Protokolls",
  „Verschiedenes").
- **Vorlagen zuweisen:** Verknüpfung mit Gremium/Ausschuss als Standard-Vorlage.
- **Vorlagen anpassen:** Beim Erstellen einer neuen Tagesordnung aus Vorlage können TOPs individuell angepasst werden.

### 3.2.3 Benachrichtigungen

**Beschreibung:** Automatischer E-Mail-Versand bei relevanten Ereignissen rund um die Tagesordnung.

**Auslöser:**

| Ereignis              | Empfänger                    | Zeitpunkt                                |
|-----------------------|------------------------------|------------------------------------------|
| Tagesordnung versandt | Alle eingeladenen Teilnehmer | Sofort bei Statuswechsel auf „Versandt"  |
| Erinnerung an Sitzung | Alle eingeladenen Teilnehmer | Konfigurierbar (z. B. 24h vorher)        |

> **Hinweis:** Weitere modulübergreifende Benachrichtigungen (Protokoll zur Prüfung, Ersatzmitglied-Einladung etc.)
> sind in Abschnitt 3.10 (Benachrichtigungen) zentral dokumentiert.

---

## 3.3 Protokolle (Modul: `minutes`)

### 3.3.1 Erstellung

**Beschreibung:** Protokolle können während oder nach der Sitzung erstellt werden. Das Protokoll besteht aus
**Sitzungsmetadaten** (Kopfdaten der Sitzung) und **TOP-bezogenen Inhalten** (Notizen und Abstimmungsergebnisse pro
Tagesordnungspunkt).

#### Sitzungsmetadaten (Protokollkopf)

Das Protokoll erfasst folgende übergreifende Informationen zur Sitzung:

- **Startzeit der Sitzung:** Tatsächlicher Beginn (Zeitstempel).
- **Sitzungsart:** Online oder Präsenz.
- **Anwesenheitsliste:** Automatische Übernahme aus der Anwesenheitsbestätigung (siehe 3.4).
- **Abwesenheit:** Auflistung regulärer Mitglieder, die nicht anwesend sind (entschuldigt/unentschuldigt).
- **Nachgeladene Ersatzmitglieder:** Separat aufgeführte Ersatzmitglieder mit Angabe, wen sie vertreten.
- **Tagesordnung:** Automatische Übernahme der TOPs aus der Tagesordnung.
- **Ende der Sitzung:** Tatsächliches Ende (Zeitstempel).

#### TOP-bezogene Inhalte

Für jeden Tagesordnungspunkt werden folgende Inhalte erfasst:

- **Rich-Text-Editor:** WYSIWYG-Editor für strukturierte Notizen und Protokollierung pro TOP.
- **Vorstrukturierung:** Automatische Übernahme der TOPs aus der Tagesordnung als Protokollstruktur.
- **Verknüpfungen:** Automatische Verknüpfung mit:
    - Beschlüssen und Abstimmungsergebnissen (bei Beschluss-TOPs)
    - Angehängten Dokumenten (aus dem DMS)
- **Notizen:** Freitextfeld für Diskussionsergebnisse, Berichte und Informationen.

#### Ergebnis-Struktur des fertigen Protokolls

Das generierte Protokolldokument hat folgende Struktur:

1. Startzeit der Sitzung
2. Sitzungsart (Online/Präsenz)
3. Anwesenheitsliste der Sitzung
4. Abwesenheit regulärer nicht anwesender Mitglieder
5. Nachgeladene Ersatzmitglieder (separat aufgeführt)
6. Tagesordnung (Agenda)
7. Protokolleinträge pro Tagesordnungspunkt (Notizen, Beschlüsse, Abstimmungsergebnisse)
8. Ende der Sitzung

### 3.3.2 Freigabeprozess

**Beschreibung:** Mehrstufiger Genehmigungsprozess für Protokolle.

**Workflow:**

```
                    ┌──────────┐
                    │ Entwurf  │
                    └────┬─────┘
                         │ Protokollführung reicht ein
                         ▼
               ┌─────────────────┐
               │ Zur Prüfung     │
               │ eingereicht     │
               └────┬────────┬───┘
                    │        │
    ┌───────────────▼─┐  ┌──▼────────────────┐
    │ Genehmigung     │  │ Genehmigung       │
    │ Vorsitz         │  │ Protokollführung  │
    └───────┬─────────┘  └──────┬────────────┘
            │                   │
            └─────────┬─────────┘
                      │ Beide genehmigt
                      ▼
          ┌───────────────────────┐
          │ Vorläufig genehmigt   │
          └───────────┬───────────┘
                      │ Automatisch auf TO der
                      │ nächsten Sitzung gesetzt
                      ▼
          ┌───────────────────────┐
          │ Beschluss in nächster │
          │ Sitzung (Abstimmung)  │
          └───────────┬───────────┘
                      │
            ┌─────────┴──────────┐
            ▼                    ▼
   ┌──────────────┐    ┌──────────────┐
   │ Finalisiert  │    │ Überarbeitung│
   │ (Freigegeben)│    │ erforderlich │
   └──────────────┘    └──────────────┘
```

**Rollen im Freigabeprozess:**

| Rolle                       | Berechtigung                                      |
|-----------------------------|---------------------------------------------------|
| Protokollführung            | Erstellt Protokoll, reicht zur Prüfung ein        |
| Vorsitz (Gremium/Ausschuss) | Genehmigt oder weist zurück                       |
| Gremiumsmitglieder          | Stimmen in nächster Sitzung über Finalisierung ab |

**Automatische TOP-Erstellung:** Nach vorläufiger Genehmigung wird automatisch ein TOP „Genehmigung des Protokolls
vom [Datum]" auf die Tagesordnung der nächsten Sitzung gesetzt.

### 3.3.3 Versionierung

**Beschreibung:** Lückenlose Nachvollziehbarkeit aller Änderungen.

**Funktionen:**

- **Automatische Versionierung:** Jede Speicherung erzeugt eine neue Version.
- **Diff-Ansicht:** Vergleich zwischen zwei beliebigen Versionen.
- **Änderungsprotokoll:** Wer hat wann was geändert.
- **Wiederherstellung:** Ältere Versionen können wiederhergestellt werden (nur vor Finalisierung).
- **Unveränderbarkeit:** Nach Finalisierung ist das Protokoll schreibgeschützt.

---

## 3.4 Anwesenheitsverwaltung (Modul: `attendance`)

### 3.4.1 Digitale Bestätigung

**Beschreibung:** Rechtssichere digitale Anwesenheitsbestätigung.

**Ablauf:**

1. Mitglied meldet sich im System an.
2. Bei der Sitzung wird die Anwesenheit über einen **2FA-gesicherten Bestätigungsprozess** erfasst:
    - Schritt 1: Anmeldung im System (1. Faktor: Passwort/SSO)
    - Schritt 2: Bestätigung per TOTP-Code oder Push-Benachrichtigung (2. Faktor)
3. Zeitstempel und IP-Adresse werden für die Audit-Dokumentation erfasst.
4. Verspätetes Erscheinen und vorzeitiges Verlassen können mit Zeitstempel dokumentiert werden.

**Anwesenheitsstatus:**

| Status                    | Beschreibung                         |
|---------------------------|--------------------------------------|
| Anwesend                  | Vollständig anwesend                 |
| Verspätet                 | Ab Zeitpunkt X anwesend              |
| Vorzeitig gegangen        | Bis Zeitpunkt X anwesend             |
| Abwesend (entschuldigt)   | Vorab entschuldigt                   |
| Abwesend (unentschuldigt) | Nicht erschienen, nicht entschuldigt |
| Vertreten                 | Durch Ersatzmitglied vertreten       |

### 3.4.2 Ersatzmitglieder-Vorschläge

**Beschreibung:** Intelligente Vorschläge für Ersatzmitglieder bei Abwesenheit.

**Logik:**

1. **Wahlresultate:** Ersatzmitglieder werden nach Listenplatz/Stimmenzahl priorisiert.
2. **Geschlechterregelung:** Das System berücksichtigt die Geschlechterquote gemäß § 15 Abs. 2 BetrVG (
   Minderheitengeschlecht).
3. **Verfügbarkeit:** Abgleich mit dem Kalender des Ersatzmitglieds.
4. **Nachrück-Reihenfolge:** Automatische Ermittlung der korrekten Nachrück-Reihenfolge.

**Workflow bei Abwesenheitsmeldung:**

```
Mitglied meldet Abwesenheit
         │
         ▼
System ermittelt Ersatzmitglieder-Vorschläge
(basierend auf Wahlresultat + Geschlechterregelung + Verfügbarkeit)
         │
         ▼
Vorsitz wählt Ersatzmitglied aus oder bestätigt Vorschlag
         │
         ▼
Ersatzmitglied wird benachrichtigt und eingeladen
         │
         ▼
Ersatzmitglied erhält temporären Zugriff auf Sitzungsunterlagen
```

### 3.4.3 Kalenderintegration

**Beschreibung:** Zentrale Terminverwaltung mit Abwesenheitsmanagement.

**Funktionen:**

- **Sitzungstermine:** Alle Sitzungstermine im zentralen Kalender.
- **Abwesenheiten eintragen:** Mitglieder und Ersatzmitglieder können Abwesenheiten pflegen.
- **Nachladungsbedarf:** Automatische Erkennung, wenn die Beschlussfähigkeit gefährdet ist.
- **Kalender-Export:** iCal-Export für Synchronisation mit externen Kalendern (Outlook, Google Calendar).
- **Ersatzmitglieder-Zugriff:** Ersatzmitglieder haben **dauerhaften Zugriff** auf den Kalender, unabhängig von einem
  aktiven Einsatz. Auf alle anderen Daten erhalten sie nur während ihrer Einsatzzeit Zugriff.

### 3.4.4 Beschlussfähigkeitsprüfung

**Beschreibung:** Automatische Prüfung der Beschlussfähigkeit gemäß § 33 BetrVG.

**Funktionen:**

- Berechnung basierend auf der Anzahl der ordentlichen Mitglieder.
- Warnung bei drohender Beschlussunfähigkeit.
- Berücksichtigung von Ersatzmitgliedern als stimmberechtigte Teilnehmer.
- Dokumentation der Beschlussfähigkeit im Protokoll.

---

## 3.5 Dokumentenmanagementsystem (Modul: `documents`)

### 3.5.1 Dokumentenverwaltung

**Beschreibung:** Zentrale Speicherung und Verwaltung aller betriebsratsrelevanten Dokumente.

**Funktionen:**

- **Upload:** Unterstützung gängiger Formate (PDF, DOCX, XLSX, PPTX, Bilder).
- **Kategorisierung:** Ordnerstruktur und Tags zur Organisation.
- **Versionierung:** Automatische Versionierung bei Aktualisierungen.
- **Änderungsverfolgung:** Änderungsprotokoll mit Benutzer, Zeitstempel und Beschreibung.
- **Volltextsuche:** Suche über Dokumenteninhalte (PDF-Text-Extraktion).
- **Vorschau:** Dokumentenvorschau im Browser ohne Download.
- **Verknüpfungen:** Dokumente können mit TOPs, Protokollen und Beschlüssen verknüpft werden.

### 3.5.2 Zugriffssteuerung

**Beschreibung:** Granulare Rechteverwaltung für Dokumentenzugriff.

**Zugriffsebenen:**

| Ebene                | Beschreibung                               |
|----------------------|--------------------------------------------|
| Öffentlich (Gremium) | Alle Mitglieder des Gremiums haben Zugriff |
| Ausschuss            | Nur Mitglieder des jeweiligen Ausschusses  |
| Eingeschränkt        | Nur bestimmte Personen                     |
| Vertraulich          | Nur Vorsitz und definierte Personen        |

**Gastzugriff:**

- Gäste erhalten **zeitbegrenzten** Zugriff auf spezifische Dokumente.
- Zugriff wird über Einladungslinks mit Ablaufdatum realisiert.
- Nach Ablauf wird der Zugriff automatisch entzogen.
- Alle Zugriffe werden im Audit-Log protokolliert.

---

## 3.6 Beschlusssystem (Modul: `resolutions`)

### 3.6.1 Beschlüsse

**Beschreibung:** Erfassung und Dokumentation von Beschlüssen mit automatischer Berechnung der Beschlussfähigkeit und
des Abstimmungsergebnisses.

**Funktionen:**

- **Verknüpfung:** Jeder Beschluss ist mit einem Tagesordnungspunkt (TOP) verknüpft.
- **Beschlusstext:** Strukturierter Beschluss mit zwei separaten Feldern:
    - **Beschlusstext / Beschlussvorschlag:** Der eigentliche Wortlaut des Beschlusses bzw. Antrags.
    - **Begründung:** Separate Begründung zum Beschluss.
- **Abstimmung:** Erfassung der Abstimmungsergebnisse mit folgenden Feldern:

| Feld                              | Typ                | Beschreibung                                                                                                                |
|-----------------------------------|--------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Dafür                             | Anzahl             | Anzahl der Ja-Stimmen                                                                                                       |
| Dagegen                           | Anzahl             | Anzahl der Nein-Stimmen                                                                                                     |
| Enthaltungen                      | Anzahl             | Anzahl der Enthaltungen                                                                                                     |
| Anwesend                          | Anzahl             | Anzahl der wahlberechtigten Mitglieder zum Zeitpunkt der Abstimmung                                                        |
| Beschlussfähigkeit festgestellt   | Berechnet (Ja/Nein) | Automatische Berechnung, ob ausreichend Mitglieder anwesend sind. **Überschreibbar.** Konfigurierbar pro Gremium (Standard: ≥ 1/2 der Gesamtmitglieder) |
| Antrag ist angenommen             | Berechnet (Ja/Nein) | Automatische Berechnung basierend auf dem Abstimmungsergebnis und dem konfigurierten Mehrheitstyp. **Überschreibbar.**      |

- **Ergebnis:** Automatische Berechnung: Angenommen / Abgelehnt (basierend auf einfacher Mehrheit oder qualifizierter
  Mehrheit je nach Konfiguration). Manuelles Überschreiben ist möglich (z. B. bei Sonderfällen).
- **Beschlussnummer:** Automatische, fortlaufende Nummerierung (z. B. `BR-2026-042`).
- **Beschlussregister:** Zentrales Register aller Beschlüsse mit Such- und Filterfunktion.

### 3.6.2 Wahlen

**Beschreibung:** Durchführung von Wahlen innerhalb des Gremiums.

**Funktionen:**

- **Wahlverfahren:** Unterstützung verschiedener Wahlverfahren (Mehrheitswahl, Verhältniswahl).
- **Geheime Abstimmung:** Option für geheime Abstimmungen.
- **Kandidatenlisten:** Verwaltung von Kandidaten und Listen.
- **Ergebnisprotokollierung:** Automatische Dokumentation der Wahlergebnisse im Protokoll.

---

## 3.7 Ausschussverwaltung (Modul: `committees`)

### 3.7.1 Verwaltung

**Beschreibung:** Separate Verwaltung für verschiedene Gremien und Ausschüsse.

**Funktionen:**

- **Gremien-Typen:**
    - Betriebsrat (Hauptgremium)
    - Betriebsausschuss
    - Fachausschüsse (z. B. Wirtschaftsausschuss, Personalausschuss)
    - Ad-hoc-Ausschüsse
- **Mitgliederverwaltung:** Zuordnung von Mitgliedern zu Gremien mit Rolle (Vorsitz, stellv. Vorsitz, Mitglied).
- **Eigenständige Bereiche:** Jedes Gremium hat eigene Tagesordnungen, Protokolle, Dokumente und Beschlüsse.
- **Hierarchie:** Ausschüsse sind dem Betriebsrat untergeordnet; Beschlüsse können zur Bestätigung an das Hauptgremium
  weitergeleitet werden.

### 3.7.2 Rechtekonzept pro Gremium

Die Berechtigungen pro Gremium werden über das **dynamische Rollensystem** gesteuert (siehe Modul 3.8). Die folgende
Tabelle zeigt die **Standard-Konfiguration**, die über die Rollenverwaltung anpassbar ist:

| Rolle (Standard)                  | Tagesordnung     | Protokoll        | Dokumente              | Beschlüsse       |
|-----------------------------------|------------------|------------------|------------------------|------------------|
| Vorsitz                           | Vollzugriff      | Vollzugriff      | Vollzugriff            | Vollzugriff      |
| Mitglied                          | Lesen            | Lesen            | Lesen                  | Abstimmen        |
| Ersatzmitglied (im Einsatz)       | Lesen            | Lesen            | Lesen                  | Abstimmen        |
| Ersatzmitglied (nicht im Einsatz) | Kein Zugriff     | Kein Zugriff     | Kein Zugriff           | Kein Zugriff     |
| Gast                              | Kein Zugriff     | Kein Zugriff     | Freigegebene Dokumente | Kein Zugriff     |
| *Benutzerdefinierte Rollen*       | *Konfigurierbar* | *Konfigurierbar* | *Konfigurierbar*       | *Konfigurierbar* |

> **Hinweis:** Ersatzmitglieder haben unabhängig vom Einsatzstatus immer Zugriff auf den Kalender. Über
> benutzerdefinierte Rollen können weitere Zugriffsprofile erstellt werden (z. B. „Leseberechtigter", „Assistenz
> Vorsitz").

---

## 3.8 Rollen- und Rechteverwaltung (Modul: `roles`)

### 3.8.1 Dynamisches Rollensystem

**Beschreibung:** Vollständig konfigurierbares Rollen- und Berechtigungssystem, das es Administratoren und Vorsitzenden
ermöglicht, Rollen zu erstellen, zu bearbeiten und ihnen granulare Berechtigungen zuzuweisen.

**Kernkonzepte:**

- **Berechtigungen (Permissions):** Jede Aktion im System (z. B. „Sitzung erstellen", „Protokoll genehmigen") ist als
  eigenständige Berechtigung definiert. Berechtigungen sind vordefiniert und können nicht durch Benutzer erstellt, aber
  Rollen zugewiesen werden.
- **Rollen:** Bündeln mehrere Berechtigungen zu einem Profil. Das System liefert Standard-Rollen (Vorsitz, Mitglied,
  Protokollführung etc.) aus, die anpassbar sind.
- **Zuordnung:** Rollen werden Mitgliedern innerhalb eines Gremiums zugewiesen. Ein Benutzer kann in verschiedenen
  Gremien unterschiedliche Rollen haben.

### 3.8.2 Rollen verwalten

**Funktionen:**

- **Rollen-Übersicht:** Tabellarische Ansicht aller Rollen mit Name, Typ, Anzahl zugewiesener Mitglieder und Status (
  Standard/Benutzerdefiniert).
- **Rolle erstellen:** Neue Rolle mit frei wählbarem Namen und Beschreibung erstellen. Optional: bestehende Rolle als
  Vorlage duplizieren.
- **Rolle bearbeiten:** Name, Beschreibung und zugewiesene Berechtigungen einer Rolle anpassen.
- **Rolle löschen:** Benutzerdefinierte Rollen löschen (Voraussetzung: keine aktiven Zuweisungen). Standard-Rollen sind
  nicht löschbar.
- **Rollen-Migration:** Beim Löschen einer Rolle können zugewiesene Mitglieder automatisch einer anderen Rolle
  zugeordnet werden.

### 3.8.3 Berechtigungen zuweisen

**Funktionen:**

- **Berechtigungs-Editor:** Visuelle Oberfläche zum Zuweisen/Entziehen von Berechtigungen.
    - Berechtigungen nach Modulen/Kategorien gruppiert (Sitzungen, Protokolle, Dokumente etc.).
    - Checkboxen zum Aktivieren/Deaktivieren einzelner Berechtigungen.
    - „Alle auswählen" / „Alle abwählen" pro Kategorie.
    - Suchfunktion zum schnellen Finden von Berechtigungen.
- **Berechtigungsmatrix:** Übersichtliche Matrix-Ansicht: Rollen (Spalten) × Berechtigungen (Zeilen).
- **Vorschau:** Vor dem Speichern wird eine Vorschau der resultierenden Zugriffsrechte angezeigt.

### 3.8.4 Rollen zuweisen

**Funktionen:**

- **Mitgliederverwaltung:** Bei der Zuordnung eines Mitglieds zu einem Gremium wird eine Rolle ausgewählt.
- **Rollenwechsel:** Die Rolle eines Mitglieds kann jederzeit geändert werden. Die Berechtigungen werden sofort
  aktualisiert.
- **Systemrollen:** Systemweite Rollen (z. B. System-Admin) werden in der globalen Benutzerverwaltung zugewiesen.

### 3.8.5 Sicherheit und Audit

**Funktionen:**

- **Audit-Trail:** Jede Änderung an Rollen, Berechtigungszuordnungen und Rollenzuweisungen wird protokolliert.
- **Privilege Escalation Prevention:** Benutzer können keine Rollen erstellen, die mehr Rechte enthalten als ihre eigene
  Rolle.
- **Compliance-Export:** Export der vollständigen Berechtigungsmatrix pro Gremium für Prüfungszwecke.

---

## 3.9 Kalenderintegration (Modul: `calendar_mgmt`)

**Beschreibung:** Zentrale Kalender- und Terminverwaltung.

**Funktionen:**

- **Sitzungskalender:** Übersicht aller geplanten Sitzungen aller Gremien.
- **Persönlicher Kalender:** Individuelle Ansicht mit eigenen Sitzungen.
- **Abwesenheitskalender:** Verwaltung von Urlaub, Krankheit, Dienstreisen.
- **Terminkollisionsprüfung:** Warnung bei Überschneidungen.
- **Raumverwaltung:** Optional: Verwaltung von Sitzungsräumen.
- **iCal-Export/Import:** Synchronisation mit externen Kalenderprogrammen.
- **Erinnerungen:** Konfigurierbare Erinnerungen vor Sitzungen.

---

## 3.10 Benachrichtigungen (Modul: `notifications`)

### Benachrichtigungskanäle

| Kanal  | Beschreibung                             |
|--------|------------------------------------------|
| E-Mail | Primärer Benachrichtigungskanal          |
| In-App | Benachrichtigungscenter in der Anwendung |

### Benachrichtigungstypen

| Typ                          | Auslöser                             | Empfänger              |
|------------------------------|--------------------------------------|------------------------|
| Sitzungseinladung            | Tagesordnung versandt                | Alle Mitglieder        |
| Sitzungserinnerung           | Konfigurierter Zeitpunkt vor Sitzung | Eingeladene Teilnehmer |
| Protokoll zur Prüfung        | Protokoll eingereicht                | Vorsitz                |
| Protokoll genehmigt          | Vorläufige Genehmigung               | Alle Mitglieder        |
| Dokument geteilt             | Dokument mit Gremium geteilt         | Betroffene Mitglieder  |
| Ersatzmitglied-Einladung     | Nachrückung erforderlich             | Ersatzmitglied         |
| Beschlussfähigkeit gefährdet | Zu viele Abwesenheiten               | Vorsitz                |
| Abwesenheitsmeldung          | Mitglied meldet Abwesenheit          | Vorsitz                |

### Benachrichtigungseinstellungen

- Benutzer können Benachrichtigungspräferenzen individuell konfigurieren.
- Pflichtbenachrichtigungen (z. B. Sitzungseinladungen) können nicht deaktiviert werden.
- Zusammenfassungs-E-Mails (Digest) als Option für nicht-kritische Benachrichtigungen.
