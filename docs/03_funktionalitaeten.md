# 03 – Funktionalitäten

## 3.1 Modulübersicht

| Modul                      | App-Name        | Beschreibung                                                                                                                    |
|----------------------------|-----------------|---------------------------------------------------------------------------------------------------------------------------------|
| Sitzungsverwaltung         | `meetings`      | Verwaltung von Sitzungen (Online/Hybrid/Präsenz) mit Vorsitz, Protokollführung und Verknüpfung aller sitzungsbezogenen Elemente |
| Tagesordnungen             | `agendas`       | Erstellung, Verwaltung und Vorlagen für Tagesordnungen                                                                          |
| Protokolle                 | `minutes`       | Protokollerstellung, Freigabe-Workflow und Versionierung                                                                        |
| Anwesenheitsverwaltung     | `attendance`    | Digitale Anwesenheitsbestätigung und Ersatzmitglieder-Logik                                                                     |
| Dokumentenmanagement       | `documents`     | DMS mit Versionierung und Zugriffssteuerung                                                                                     |
| Beschlusssystem            | `resolutions`   | Abstimmungen, Wahlen und Beschlussdokumentation                                                                                 |
| Ausschussverwaltung        | `committees`    | Verwaltung von Gremien und Ausschüssen                                                                                          |
| Rollen- & Rechteverwaltung | `roles`         | Dynamische Rollen und Berechtigungen konfigurieren                                                                              |
| Kalender                   | `calendar_mgmt` | Terminverwaltung und Kalenderintegration                                                                                        |
| Benachrichtigungen         | `notifications` | E-Mail- und In-App-Benachrichtigungen                                                                                           |
| To-Do-Verwaltung           | `todos`         | Verwaltung von Aufgaben mit Zuordnung und Fälligkeitsdaten                                                                      |
| Personelle Einzelmaßnahmen | `personnel`     | Verwaltung personeller Maßnahmen mit Fristenüberwachung                                                                         |

---

## 3.2 Sitzungsverwaltung (Modul: `meetings`)

**Beschreibung:** Jede Sitzung verfügt über ein strukturiertes Sitzungsobjekt mit Metadaten und verknüpften Elementen.
Das Sitzungsmodell ist das zentrale Element der Anwendung – alle weiteren Module (Tagesordnungen, Protokolle,
Anwesenheiten, Beschlüsse) sind an das Sitzungsobjekt gebunden.

**Sitzungsmetadaten:**

- **Sitzungstyp:** Online, Hybrid oder Präsenz.
- **Datum und Uhrzeit:** Geplanter Beginn und Ende.
- **Ort/Adresse (abhängig vom Sitzungstyp):**
    - **Online:** Nur ein Online-Teilnahmelink (URL) wird erfasst.
    - **Hybrid:** Online-Teilnahmelink **und** vollständige Adressfelder (Ortsbezeichnung, Straße, PLZ, Stadt, Raum).
    - **Präsenz:** Vollständige Adressfelder (Ortsbezeichnung, Straße, PLZ, Stadt, Raum) ohne Online-Link.
- **Zugeordnetes Gremium/Ausschuss:** Jede Sitzung ist einem Gremium oder Ausschuss zugeordnet.

**Verknüpfte Elemente:**

- **Tagesordnung:** Die Tagesordnung ist direkt an das Sitzungsobjekt gebunden.
- **Protokoll:** Das Protokoll wird der Sitzung zugeordnet.
- **Anwesenheiten:** Alle Anwesenheitseinträge sind mit der Sitzung verknüpft.
- **Beschlüsse:** Beschlüsse werden über die Tagesordnungspunkte der Sitzung referenziert.

**Vorsitz und Protokollführung:**

- **Vorsitz der Sitzung:** Die Sitzung wird von einem Vorsitzenden oder dessen Vertretung eröffnet. Die eröffnende
  Person wird als Vorsitz für diese Sitzung eingetragen.
- **Protokollführung der Sitzung:** Analog wird die Protokollführung (oder deren Vertretung) für die Sitzung
  eingetragen.
- **Vertretungen:** Sowohl für den Vorsitz als auch für die Protokollführung können ein oder mehrere Vertretungen im
  Gremium oder Ausschuss definiert werden. Vertretungen haben dieselben Rechte wie ihre jeweiligen Gegenstücke.

---

## 3.3 Tagesordnungen (Modul: `agendas`)

### 3.3.1 Erstellen und Verwalten

**Beschreibung:** Vollständiger Lebenszyklus einer Tagesordnung – von der Erstellung bis zur Finalisierung.

**Funktionen:**

- **Erstellen:** Neue Tagesordnung für eine Sitzung anlegen mit Datum, Uhrzeit, Ort/Adresse (je nach Sitzungstyp) und zugeordnetem Gremium/Ausschuss.
- **Tagesordnungspunkte (TOP):** Hinzufügen, Bearbeiten, Löschen und Umsortieren von TOPs per Drag-and-Drop.
- **TOP-Typen:**
    - Regulärer TOP (Bericht, Diskussion, Information)
    - Beschluss-TOP (verknüpft mit Abstimmung)
    - Wahl-TOP (verknüpft mit Wahlverfahren)
    - Personelle-Einzelmaßnahme-TOP (verknüpft mit personeller Maßnahme, siehe 3.13)
    - Protokollgenehmigung (automatisch generiert, siehe 3.4)
- **Anhänge:** Dokumente können an einzelne TOPs angehängt werden (Verknüpfung mit DMS).
- **Status-Workflow:**

```
Entwurf → In Bearbeitung → Freigegeben → Versandt → Abgeschlossen
```

- **Bearbeitung:** Tagesordnungen im Status „Entwurf" und „In Bearbeitung" sind editierbar.
- **Löschung:** Nur im Status „Entwurf" möglich. Abgeschlossene Tagesordnungen werden archiviert.

### 3.3.2 Vorlagen

**Beschreibung:** Wiederverwendbare Vorlagen für regelmäßige Sitzungen.

**Funktionen:**

- **Vorlagen erstellen:** Aus bestehender Tagesordnung oder manuell.
- **Standard-TOPs:** Vorlagen enthalten vordefinierte TOPs (z. B. „Genehmigung des letzten Protokolls",
  „Verschiedenes").
- **Vorlagen zuweisen:** Verknüpfung mit Gremium/Ausschuss als Standard-Vorlage.
- **Vorlagen anpassen:** Beim Erstellen einer neuen Tagesordnung aus Vorlage können TOPs individuell angepasst werden.

### 3.3.3 Benachrichtigungen

**Beschreibung:** Automatischer E-Mail-Versand bei relevanten Ereignissen rund um die Tagesordnung.

**Auslöser:**

| Ereignis              | Empfänger                    | Zeitpunkt                               |
|-----------------------|------------------------------|-----------------------------------------|
| Tagesordnung versandt | Alle eingeladenen Teilnehmer | Sofort bei Statuswechsel auf „Versandt" |
| Erinnerung an Sitzung | Alle eingeladenen Teilnehmer | Konfigurierbar (z. B. 24h vorher)       |

> **Hinweis:** Weitere modulübergreifende Benachrichtigungen (Protokoll zur Prüfung, Ersatzmitglied-Einladung etc.)
> sind in Abschnitt 3.10 (Benachrichtigungen) zentral dokumentiert.

---

## 3.4 Protokolle (Modul: `minutes`)

### 3.4.1 Erstellung

**Beschreibung:** Protokolle können während oder nach der Sitzung erstellt werden. Das Protokoll besteht aus
**Sitzungsmetadaten** (Kopfdaten der Sitzung) und **TOP-bezogenen Inhalten** (Notizen und Abstimmungsergebnisse pro
Tagesordnungspunkt).

#### Sitzungsmetadaten (Protokollkopf)

Das Protokoll erfasst folgende übergreifende Informationen zur Sitzung:

- **Startzeit der Sitzung:** Tatsächlicher Beginn (Zeitstempel).
- **Sitzungsart:** Online, Hybrid oder Präsenz.
- **Anwesenheitsliste:** Automatische Übernahme aus der Anwesenheitsbestätigung (siehe 3.5).
- **Abwesenheit:** Auflistung regulärer Mitglieder, die nicht anwesend sind (nachladbar/nicht nachladbar).
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
2. Sitzungsart (Online/Hybrid/Präsenz)
3. Anwesenheitsliste der Sitzung
4. Abwesenheit regulärer nicht anwesender Mitglieder
5. Nachgeladene Ersatzmitglieder (separat aufgeführt)
6. Tagesordnung (Agenda)
7. Protokolleinträge pro Tagesordnungspunkt (Notizen, Beschlüsse, Abstimmungsergebnisse)
8. Ende der Sitzung

### 3.4.2 Freigabeprozess

**Beschreibung:** Vereinfachter Genehmigungsprozess für Protokolle mittels digitaler Unterschriften.

**Workflow:**

Nachdem die Protokollführung das Protokoll als fertig erachtet, unterschreibt sie es digital. Anschließend unterschreibt
der/die Vorsitzende das Protokoll ebenfalls digital. Diese beiden digitalen Unterschriften entsprechen der vorläufigen
Genehmigung – ein separater Einreichungsschritt ist nicht erforderlich.

```
                    ┌──────────┐
                    │ Entwurf  │
                    └────┬─────┘
                         │ Protokollführung erachtet
                         │ Protokoll als fertig
                         ▼
               ┌─────────────────────┐
               │ Digitale Unterschrift│
               │ Protokollführung     │
               └────────┬────────────┘
                        │
                        ▼
               ┌─────────────────────┐
               │ Digitale Unterschrift│
               │ Vorsitz              │
               └────────┬────────────┘
                        │ Beide haben unterschrieben
                        │ = Vorläufige Genehmigung
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

**Digitale Unterschrift:**

Die digitale Unterschrift wird über einen gesicherten Bestätigungsprozess im System umgesetzt. Beim Unterschreiben wird
der Benutzer, Zeitstempel und eine kryptographische Signatur (Hash des Protokollinhalts + Benutzer-ID + Zeitstempel)
erfasst, um die Integrität und Authentizität der Genehmigung sicherzustellen.

**Rollen im Freigabeprozess:**

| Rolle                                | Berechtigung                                                 |
|--------------------------------------|--------------------------------------------------------------|
| Protokollführung (Gremium/Ausschuss) | Erstellt Protokoll, unterschreibt digital als Fertigstellung |
| Vorsitz (Gremium/Ausschuss)          | Unterschreibt digital (= vorläufige Genehmigung)             |
| Gremiumsmitglieder                   | Stimmen in nächster Sitzung über Finalisierung ab            |

**Automatische TOP-Erstellung:** Nach vorläufiger Genehmigung wird automatisch ein TOP „Genehmigung des Protokolls
vom [Datum]" auf die Tagesordnung der nächsten Sitzung gesetzt.

### 3.4.3 Versionierung

**Beschreibung:** Lückenlose Nachvollziehbarkeit aller Änderungen.

**Funktionen:**

- **Automatische Versionierung:** Jede Speicherung erzeugt eine neue Version.
- **Diff-Ansicht:** Vergleich zwischen zwei beliebigen Versionen.
- **Änderungsprotokoll:** Wer hat wann was geändert.
- **Wiederherstellung:** Ältere Versionen können wiederhergestellt werden (nur vor Finalisierung).
- **Unveränderbarkeit:** Nach Finalisierung ist das Protokoll schreibgeschützt.

---

## 3.5 Anwesenheitsverwaltung (Modul: `attendance`)

### 3.5.1 Digitale Bestätigung

**Beschreibung:** Rechtssichere Anwesenheitsbestätigung – je nach Sitzungstyp digital oder papierbasiert.

#### Online- und Hybridsitzungen

**Ablauf:**

1. Mitglied meldet sich im System an.
2. Bei der Sitzung wird die Anwesenheit über einen **2FA-gesicherten Bestätigungsprozess** erfasst:
    - Schritt 1: Anmeldung im System (1. Faktor: Passwort/SSO)
    - Schritt 2: Bestätigung per TOTP-Code oder Push-Benachrichtigung (2. Faktor)
3. Zeitstempel und IP-Adresse werden für die Audit-Dokumentation erfasst.
4. Verspätetes Erscheinen und vorzeitiges Verlassen können mit Zeitstempel dokumentiert werden.

#### Präsenzsitzungen

Bei reinen Präsenzsitzungen erfolgt die Anwesenheitserfassung durch die Protokollführung:

1. **Vorlage erstellen:** Das System erstellt eine druckbare Anwesenheitsliste mit allen erwarteten Mitgliedern (inkl.
   eingeladener Ersatzmitglieder) und freien Feldern für spontane Änderungen.
2. **Vor Ort ausfüllen:** Die Anwesenheitsliste wird von den Teilnehmern vor Ort unterschrieben.
3. **Digitalisierung:** Die unterschriebene Anwesenheitsliste wird gescannt und als Dokument an das Protokoll angehängt.
4. **Eintragung:** Die Protokollführung trägt die Anwesenheiten im System manuell ein.

**Anwesenheitsstatus:**

| Status                    | Beschreibung                         |
|---------------------------|--------------------------------------|
| Anwesend                  | Vollständig anwesend                 |
| Verspätet                 | Ab Zeitpunkt X anwesend              |
| Vorzeitig gegangen        | Bis Zeitpunkt X anwesend             |
| Abwesend (nachladbar)       | Abwesend, Ersatzmitglied kann nachrücken     |
| Abwesend (nicht nachladbar) | Abwesend, kein Nachladen möglich/nötig       |
| Vertreten                 | Durch Ersatzmitglied vertreten       |

### 3.5.2 Ersatzmitglieder-Vorschläge

**Beschreibung:** Intelligente Vorschläge für Ersatzmitglieder bei Abwesenheit.

**Logik:**

1. **Listenzugehörigkeit:** Bei Listenwahlen (Verhältniswahl) wird das Ersatzmitglied aus derselben Wahlliste
   (`election_list_name`) wie das verhinderte Mitglied ermittelt.
2. **Wahlresultate:** Innerhalb der Liste werden Ersatzmitglieder nach Listenplatz (`election_list_position`) und
   Stimmenzahl (`election_votes`) priorisiert.
3. **Geschlechterregelung:** Das System berücksichtigt die Geschlechterquote gemäß § 15 Abs. 2 BetrVG
   (Minderheitengeschlecht). Wird das Minderheitengeschlecht durch die Nachrückung unterschritten, rückt stattdessen
   das nächste Ersatzmitglied der gleichen Liste mit dem entsprechenden Geschlecht nach.
4. **Verfügbarkeit:** Abgleich mit dem Kalender des Ersatzmitglieds.
5. **Nachrück-Reihenfolge:** Automatische Ermittlung der korrekten Nachrück-Reihenfolge unter Berücksichtigung von
   Listenzugehörigkeit, Listenplatz, Geschlechterregelung und Verfügbarkeit.

**Workflow bei Abwesenheitsmeldung:**

```
Mitglied meldet Abwesenheit
         │
         ▼
System ermittelt Ersatzmitglieder-Vorschläge
(basierend auf Listenzugehörigkeit + Listenplatz + Geschlechterregelung + Verfügbarkeit)
         │
         ▼
Vorsitz wählt Ersatzmitglied aus oder bestätigt Vorschlag
         │
         ▼
Ersatzmitglied wird benachrichtigt und eingeladen
         │
         ▼
Ersatzmitglied erhält temporären Zugriff auf Sitzungsunterlagen
(Zugriff gilt von der Einladung bis zum Abschluss der Sitzung,
manuell verlängerbar; Ersatzmitglieder werden während dieser Zeit
wie reguläre Gremiumsmitglieder behandelt)
```

> **Hinweis:** Eingeladene Ersatzmitglieder erhalten ab dem Zeitpunkt der Einladung bis zum Abschluss der Sitzung (oder
> manuell verlängert) denselben Zugriff auf alle Informationen wie reguläre Gremiumsmitglieder. Während ihres Einsatzes
> werden sie in jeder Hinsicht wie ein reguläres Gremiumsmitglied behandelt.

### 3.5.3 Kalenderintegration

**Beschreibung:** Zentrale Terminverwaltung mit Abwesenheitsmanagement.

**Funktionen:**

- **Sitzungstermine:** Alle Sitzungstermine im zentralen Kalender.
- **Abwesenheiten eintragen:** Mitglieder und Ersatzmitglieder können Abwesenheiten pflegen (nachladbar/nicht nachladbar – aus Datenschutzgründen wird kein konkreter Abwesenheitsgrund gespeichert).
- **Nachladungsbedarf:** Automatische Erkennung, wenn die Beschlussfähigkeit gefährdet ist.
- **Kalender-Export:** iCal-Export für Synchronisation mit externen Kalendern (Outlook, Google Calendar).
- **Ersatzmitglieder-Zugriff:** Ersatzmitglieder haben **dauerhaften Zugriff** auf den Kalender, unabhängig von einem
  aktiven Einsatz. Auf alle anderen Daten erhalten sie nur während ihrer Einsatzzeit Zugriff.

### 3.5.4 Beschlussfähigkeitsprüfung

**Beschreibung:** Automatische Prüfung der Beschlussfähigkeit gemäß § 33 BetrVG.

**Funktionen:**

- Berechnung basierend auf der Anzahl der ordentlichen Mitglieder.
- Warnung bei drohender Beschlussunfähigkeit.
- Berücksichtigung von Ersatzmitgliedern als stimmberechtigte Teilnehmer.
- Dokumentation der Beschlussfähigkeit im Protokoll.

---

## 3.6 Dokumentenmanagementsystem (Modul: `documents`)

### 3.6.1 Dokumentenverwaltung

**Beschreibung:** Zentrale Speicherung und Verwaltung aller betriebsratsrelevanten Dokumente.

**Funktionen:**

- **Upload:** Unterstützung gängiger Formate (PDF, DOCX, XLSX, PPTX, Bilder).
- **Kategorisierung:** Ordnerstruktur und Tags zur Organisation.
- **Versionierung:** Automatische Versionierung bei Aktualisierungen.
- **Änderungsverfolgung:** Änderungsprotokoll mit Benutzer, Zeitstempel und Beschreibung.
- **Volltextsuche:** Suche über Dokumenteninhalte (PDF-Text-Extraktion).
- **Vorschau:** Dokumentenvorschau im Browser ohne Download.
- **Verknüpfungen:** Dokumente können mit TOPs, Protokollen und Beschlüssen verknüpft werden.

### 3.6.2 Zugriffssteuerung

**Beschreibung:** Granulare Rechteverwaltung für Dokumentenzugriff.

**Zugriffsebenen:**

| Ebene                | Beschreibung                                                                               |
|----------------------|--------------------------------------------------------------------------------------------|
| Öffentlich (Gremium) | Alle Mitglieder des Gremiums haben Zugriff                                                 |
| Ausschuss            | Nur Mitglieder des jeweiligen Ausschusses (inkl. externe Ausschussmitglieder, siehe 3.8.1) |
| Eingeschränkt        | Nur bestimmte Personen                                                                     |
| Vertraulich          | Nur Vorsitz und definierte Personen                                                        |

**Externe Ausschussmitglieder:**

Externe Ausschussmitglieder (die nicht Mitglied des übergeordneten Gremiums sind) haben ausschließlich Zugriff auf die
Dokumente ihres Ausschusses. Sie haben **keinen** Zugriff auf Dokumente anderer Ausschüsse oder des Gremiums. Dieser
Zugriff besteht, solange ihre Mitgliedschaft im Ausschuss aktiv ist.

**Gastzugriff:**

- Gäste erhalten **zeitbegrenzten** Zugriff auf spezifische Dokumente.
- Zugriff wird über Einladungslinks mit Ablaufdatum realisiert.
- Nach Ablauf wird der Zugriff automatisch entzogen.
- Alle Zugriffe werden im Audit-Log protokolliert.

---

## 3.7 Beschlusssystem (Modul: `resolutions`)

### 3.7.1 Beschlüsse

**Beschreibung:** Erfassung und Dokumentation von Beschlüssen mit automatischer Berechnung der Beschlussfähigkeit und
des Abstimmungsergebnisses.

**Funktionen:**

- **Verknüpfung:** Jeder Beschluss ist mit einem Tagesordnungspunkt (TOP) verknüpft.
- **Beschlusstext:** Strukturierter Beschluss mit zwei separaten Feldern:
    - **Beschlusstext / Beschlussvorschlag:** Der eigentliche Wortlaut des Beschlusses bzw. Antrags.
    - **Begründung:** Separate Begründung zum Beschluss.
- **Abstimmung:** Erfassung der Abstimmungsergebnisse mit folgenden Feldern:

| Feld                            | Typ                 | Beschreibung                                                                                                                                            |
|---------------------------------|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| Dafür                           | Anzahl              | Anzahl der Ja-Stimmen                                                                                                                                   |
| Dagegen                         | Anzahl              | Anzahl der Nein-Stimmen                                                                                                                                 |
| Enthaltungen                    | Anzahl              | Anzahl der Enthaltungen                                                                                                                                 |
| Anwesend                        | Anzahl              | Anzahl der wahlberechtigten Mitglieder zum Zeitpunkt der Abstimmung                                                                                     |
| Beschlussfähigkeit festgestellt | Berechnet (Ja/Nein) | Automatische Berechnung, ob ausreichend Mitglieder anwesend sind. **Überschreibbar.** Konfigurierbar pro Gremium (Standard: ≥ 1/2 der Gesamtmitglieder) |
| Antrag ist angenommen           | Berechnet (Ja/Nein) | Automatische Berechnung basierend auf dem Abstimmungsergebnis und dem konfigurierten Mehrheitstyp. **Überschreibbar.**                                  |

- **Ergebnis:** Automatische Berechnung: Angenommen / Abgelehnt (basierend auf einfacher Mehrheit oder qualifizierter
  Mehrheit je nach Konfiguration). Manuelles Überschreiben ist möglich (z. B. bei Sonderfällen).
- **Beschlussnummer:** Automatische, fortlaufende Nummerierung (z. B. `BR-2026-042`).
- **Beschlussregister:** Zentrales Register aller Beschlüsse mit Such- und Filterfunktion.
- **Beschluss-Übermittlung an Arbeitgeber:** Am Ende einer Sitzung besteht die Möglichkeit, Beschlüsse per E-Mail an den
  Arbeitgeber zu übermitteln. Dabei wird eine aus dem Beschluss generierte PDF versendet, die ausschließlich den
  Beschlusstext, die Begründung, die Beschlussfähigkeit (Ja/Nein) und das Ergebnis (Antrag angenommen Ja/Nein) enthält.

### 3.7.2 Wahlen

**Beschreibung:** Durchführung von Wahlen innerhalb des Gremiums. Wahlen sind ausschließlich bei **Präsenzsitzungen**
möglich.

> **Wichtig:** Wird ein Wahl-TOP in eine Online- oder Hybridsitzung eingefügt, zeigt das System eine entsprechende
> Warnung an, dass Wahlen nur bei Präsenzsitzungen durchgeführt werden können.

**Funktionen:**

- **Nur Präsenzsitzungen:** Wahlen können ausschließlich in Präsenzsitzungen durchgeführt werden.
- **Manuelle Ergebniserfassung:** Wahlergebnisse werden manuell eingetragen – es gibt keine integrierte Wahlsoftware.
  Das System dient der Dokumentation, nicht der Durchführung der Wahl.
- **Wahlverfahren:** Unterstützung verschiedener Wahlverfahren (Mehrheitswahl, Verhältniswahl).
- **Geheime Abstimmung:** Option für geheime Abstimmungen.
- **Kandidatenlisten:** Verwaltung von Kandidaten und Listen. Kandidatinnen und Kandidaten werden als **Freitext**
  erfasst (`candidate_name`) – es ist keine Verknüpfung mit einem bestehenden Benutzer-Konto erforderlich.
  Bei Listenwahlen (Verhältniswahl) wird der Listenname (`election_list_name`) pro Mitglied/Ersatzmitglied
  gespeichert und bildet die Grundlage für die Nachrückregeln.
- **Listenplatz & Stimmenzahl:** Erfassung von Listenplatz (`election_list_position`) und Stimmenzahl
  (`election_votes`) zur Bestimmung der Nachrück-Reihenfolge innerhalb einer Liste.
- **Ergebnisprotokollierung:** Dokumentation der Wahlergebnisse im Protokoll.

---

## 3.8 Ausschussverwaltung (Modul: `committees`)

### 3.8.1 Verwaltung

**Beschreibung:** Separate Verwaltung für verschiedene Gremien und Ausschüsse.

**Funktionen:**

- **Gremien-Typen:**
    - Betriebsrat (Hauptgremium)
    - Betriebsausschuss
    - Fachausschüsse (z. B. Wirtschaftsausschuss, Personalausschuss)
    - Ad-hoc-Ausschüsse
- **Mitgliederverwaltung:** Zuordnung von Mitgliedern zu Gremien mit Rolle (Vorsitz, stellv. Vorsitz, Mitglied,
  Protokollführung).
- **Externe Ausschussmitglieder:** Ausschüsse können externe Mitglieder haben, die nicht dem übergeordneten Gremium
  angehören (z. B. Wirtschaftsausschuss). Diese externen Mitglieder haben, solange ihre Mitgliedschaft im Ausschuss
  aktiv ist, Zugriff auf alle Daten und Dokumente ihres Ausschusses, jedoch **niemals** auf Daten anderer Ausschüsse
  oder des übergeordneten Gremiums.
- **Eigenständige Bereiche:** Jedes Gremium hat eigene Tagesordnungen, Protokolle, Dokumente und Beschlüsse.
- **Hierarchie:** Ausschüsse sind dem Betriebsrat untergeordnet; Beschlüsse können zur Bestätigung an das Hauptgremium
  weitergeleitet werden.

### 3.8.2 Rechtekonzept pro Gremium

Die Berechtigungen pro Gremium werden über das **dynamische Rollensystem** gesteuert (siehe Modul 3.9). Die folgende
Tabelle zeigt die **Standard-Konfiguration**, die über die Rollenverwaltung anpassbar ist:

| Rolle (Standard)                  | Tagesordnung        | Protokoll           | Dokumente              | Beschlüsse       |
|-----------------------------------|---------------------|---------------------|------------------------|------------------|
| Vorsitz                           | Vollzugriff         | Vollzugriff         | Vollzugriff            | Vollzugriff      |
| Protokollführung                  | Vollzugriff         | Vollzugriff         | Vollzugriff            | Vollzugriff      |
| Mitglied                          | Vollzugriff         | Vollzugriff         | Vollzugriff            | Vollzugriff      |
| Ersatzmitglied (im Einsatz)       | Vollzugriff         | Vollzugriff         | Vollzugriff            | Vollzugriff      |
| Ersatzmitglied (nicht im Einsatz) | Kein Zugriff        | Kein Zugriff        | Kein Zugriff           | Kein Zugriff     |
| Externes Ausschussmitglied        | Vollzugriff*        | Vollzugriff*        | Vollzugriff*           | Vollzugriff*     |
| Gast                              | Eingeladene Sitzung | Eingeladene Sitzung | Freigegebene Dokumente | Kein Zugriff     |
| *Benutzerdefinierte Rollen*       | *Konfigurierbar*    | *Konfigurierbar*    | *Konfigurierbar*       | *Konfigurierbar* |

\* Externe Ausschussmitglieder haben ausschließlich Zugriff auf die Daten ihres Ausschusses, niemals auf andere
Ausschüsse oder das Gremium.

> **Hinweis:** Ersatzmitglieder haben unabhängig vom Einsatzstatus immer Zugriff auf den Kalender. Gäste haben Zugriff
> auf die Tagesordnung und das Protokoll nur für Sitzungen, zu denen sie eingeladen sind. Über benutzerdefinierte Rollen
> können weitere Zugriffsprofile erstellt werden (z. B. „Leseberechtigter", „Assistenz Vorsitz").

---

## 3.9 Rollen- und Rechteverwaltung (Modul: `roles`)

### 3.9.1 Dynamisches Rollensystem

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

### 3.9.2 Rollen verwalten

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

### 3.9.3 Berechtigungen zuweisen

**Funktionen:**

- **Berechtigungs-Editor:** Visuelle Oberfläche zum Zuweisen/Entziehen von Berechtigungen.
    - Berechtigungen nach Modulen/Kategorien gruppiert (Sitzungen, Protokolle, Dokumente etc.).
    - Checkboxen zum Aktivieren/Deaktivieren einzelner Berechtigungen.
    - „Alle auswählen" / „Alle abwählen" pro Kategorie.
    - Suchfunktion zum schnellen Finden von Berechtigungen.
- **Berechtigungsmatrix:** Übersichtliche Matrix-Ansicht: Rollen (Spalten) × Berechtigungen (Zeilen).
- **Vorschau:** Vor dem Speichern wird eine Vorschau der resultierenden Zugriffsrechte angezeigt.

### 3.9.4 Rollen zuweisen

**Funktionen:**

- **Mitgliederverwaltung:** Bei der Zuordnung eines Mitglieds zu einem Gremium wird eine Rolle ausgewählt.
- **Rollenwechsel:** Die Rolle eines Mitglieds kann jederzeit geändert werden. Die Berechtigungen werden sofort
  aktualisiert.
- **Systemrollen:** Systemweite Rollen (z. B. System-Admin) werden in der globalen Benutzerverwaltung zugewiesen.

### 3.9.5 Sicherheit und Audit

**Funktionen:**

- **Audit-Trail:** Jede Änderung an Rollen, Berechtigungszuordnungen und Rollenzuweisungen wird protokolliert.
- **Privilege Escalation Prevention:** Benutzer können keine Rollen erstellen, die mehr Rechte enthalten als ihre eigene
  Rolle.
- **Compliance-Export:** Export der vollständigen Berechtigungsmatrix pro Gremium für Prüfungszwecke.

---

## 3.10 Kalenderintegration (Modul: `calendar_mgmt`)

**Beschreibung:** Zentrale Kalender- und Terminverwaltung.

**Funktionen:**

- **Sitzungskalender:** Übersicht aller geplanten Sitzungen aller Gremien.
- **Persönlicher Kalender:** Individuelle Ansicht mit eigenen Sitzungen.
- **Abwesenheitskalender:** Verwaltung von Abwesenheiten (nachladbar/nicht nachladbar – aus Datenschutzgründen ohne konkreten Abwesenheitsgrund).
- **Reisedaten:** Mitglieder können Reisedaten (z. B. An- und Abreise bei mehrtägigen Veranstaltungen, Schulungen oder
  auswärtigen Sitzungen) im Kalender eintragen. Reisedaten werden in der Übersicht und bei der Verfügbarkeitsprüfung
  berücksichtigt.
- **Terminkollisionsprüfung:** Warnung bei Überschneidungen (inkl. Reisedaten).
- **Raumverwaltung:** Optional: Verwaltung von Sitzungsräumen.
- **iCal-Export/Import:** Synchronisation mit externen Kalenderprogrammen.
- **Erinnerungen:** Konfigurierbare Erinnerungen vor Sitzungen.

---

## 3.11 Benachrichtigungen (Modul: `notifications`)

### Benachrichtigungskanäle

| Kanal  | Beschreibung                             |
|--------|------------------------------------------|
| E-Mail | Primärer Benachrichtigungskanal          |
| In-App | Benachrichtigungscenter in der Anwendung |

### Benachrichtigungstypen

| Typ                               | Auslöser                               | Empfänger                      |
|-----------------------------------|----------------------------------------|--------------------------------|
| Sitzungseinladung                 | Tagesordnung versandt                  | Alle Mitglieder                |
| Sitzungserinnerung                | Konfigurierter Zeitpunkt vor Sitzung   | Eingeladene Teilnehmer         |
| Protokoll zur Unterschrift        | Protokollführung hat unterschrieben    | Vorsitz                        |
| Protokoll genehmigt               | Vorläufige Genehmigung                 | Alle Mitglieder                |
| Dokument geteilt                  | Dokument mit Gremium geteilt           | Betroffene Mitglieder          |
| Ersatzmitglied-Einladung          | Nachrückung erforderlich               | Ersatzmitglied                 |
| Beschluss-PDF an Arbeitgeber      | Beschluss-Versand ausgelöst            | Arbeitgeber (E-Mail)           |
| Personelle Maßnahme: Fristwarnung | Fristablauf in ≤ 2 Tagen               | Vorsitz, zuständige Mitglieder |
| Personelle Maßnahme: Ergebnis     | Ergebnisversand nach Sitzung ausgelöst | Arbeitgeber (E-Mail)           |
| Beschlussfähigkeit gefährdet      | Zu viele Abwesenheiten                 | Vorsitz                        |
| Abwesenheitsmeldung               | Mitglied meldet Abwesenheit            | Vorsitz                        |

### Benachrichtigungseinstellungen

- Benutzer können Benachrichtigungspräferenzen individuell konfigurieren.
- Pflichtbenachrichtigungen (z. B. Sitzungseinladungen) können nicht deaktiviert werden.
- Zusammenfassungs-E-Mails (Digest) als Option für nicht-kritische Benachrichtigungen.

---

## 3.12 To-Do-Verwaltung (Modul: `todos`)

**Beschreibung:** Verwaltung von Aufgaben, die sich aus der Betriebsratsarbeit ergeben.

**Funktionen:**

- **Aufgabe erstellen:** Titel, Beschreibung, Fälligkeitsdatum, Priorität (Hoch/Mittel/Niedrig).
- **Aufgabe bearbeiten:** Der Ersteller und alle zugewiesenen Mitglieder können die Aufgabe bearbeiten.
- **Aufgabe löschen:** Nur der Ersteller der Aufgabe kann diese löschen. Admin, Vorsitz und Stellv. Vorsitz können alle Aufgaben löschen.
- **Zuordnung:** Aufgaben können einem oder mehreren Mitgliedern zugewiesen werden.
- **Verknüpfung:** Aufgaben können mit Sitzungen, TOPs, Beschlüssen oder Dokumenten verknüpft werden.
- **Status-Workflow:**

```
Offen → In Bearbeitung → Erledigt
```

- **Fristenüberwachung:** Automatische Erinnerungen bei bevorstehenden Fälligkeitsdaten.
- **Übersicht:** Persönliche und gremienweite To-Do-Listen mit Filter- und Sortiermöglichkeiten.
- **Wiederkehrende Aufgaben:** Möglichkeit, regelmäßig wiederkehrende Aufgaben zu definieren.

---

## 3.13 Personelle Einzelmaßnahmen (Modul: `personnel`)

**Beschreibung:** Verwaltung und Nachverfolgung personeller Einzelmaßnahmen gemäß §§ 99–101 BetrVG (Einstellungen,
Versetzungen, Umgruppierungen, Kündigungen etc.). Das Modul kann pro Ausschuss aktiviert oder deaktiviert werden (
`personnel_enabled`). Alle regulären Gremiumsmitglieder sowie aktive Ersatzmitglieder haben Lesezugriff auf die
Maßnahmen. Die Verwaltung (Erstellen, Bearbeiten, Löschen etc.) ist nur in Ausschüssen möglich, bei denen das Modul
aktiviert ist.

**Funktionen:**

- **Maßnahme erfassen:** Typ der Maßnahme (Einstellung, Versetzung, Umgruppierung, Kündigung etc.), Name der betroffenen
  Person (Klartext, da zur Nachfrage beim Arbeitgeber erforderlich), Beschreibung, eingegangene Unterlagen.
- **Fristenüberwachung:** Automatische Berechnung und Überwachung der gesetzlichen Fristen (z. B. Zustimmungsfrist von
  einer Woche nach § 99 Abs. 3 BetrVG).
- **Status-Workflow:**

```
Eingegangen → Vollständig → In Prüfung → Stellungnahme erstellt → Beschluss gefasst → Abgeschlossen
```

- **Verknüpfung mit Tagesordnung:** Jede Maßnahme kann als eigener TOP (Typ: Personelle-Einzelmaßnahme-TOP) auf die
  Tagesordnung einer Sitzung gesetzt werden. Während der Sitzung können analog zu regulären TOPs Notizen und
  Informationen erfasst werden.
- **Verknüpfung mit Beschlüssen:** Stellungnahmen und Beschlüsse (Zustimmung/Verweigerung) können direkt mit der
  Maßnahme verknüpft und analog zu Beschlüssen abgestimmt werden.
- **Fristwarnung:** Automatische Benachrichtigung an den Vorsitz und betroffene Mitglieder bei bevorstehenden
  Fristabläufen (7-Tages-Frist nach Eingang gemäß § 99 Abs. 3 BetrVG). Die verbleibende Frist wird in der Übersicht
  prominent angezeigt.
- **Ergebnisversand:** Das Ergebnis der Maßnahme (Zustimmung/Verweigerung mit Begründung) kann am Ende einer Sitzung per
  E-Mail an den Arbeitgeber versendet werden.
- **Dokumentenanhänge:** Unterlagen des Arbeitgebers und eigene Stellungnahmen können angehängt werden.
- **Externe API-Schnittstelle:** Eine vorbereitete API ermöglicht die externe Erstellung personeller Maßnahmen (z. B.
  durch die Personalabteilung).
- **Register:** Zentrales Register aller personellen Einzelmaßnahmen mit Such- und Filterfunktion.
- **Datenschutz:** Besondere Zugangsbeschränkungen gemäß DSGVO – Zugriff nur für berechtigte Mitglieder.
