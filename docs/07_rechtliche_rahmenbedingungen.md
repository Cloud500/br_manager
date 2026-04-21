# 07 – Rechtliche Rahmenbedingungen

## 7.1 Übersicht

Der BR Manager muss die Anforderungen zweier zentraler Rechtsrahmen erfüllen:

1. **Betriebsverfassungsgesetz (BetrVG)** – Vorschriften zur Betriebsratsarbeit
2. **Datenschutz-Grundverordnung (DSGVO)** – Schutz personenbezogener Daten

---

## 7.2 BetrVG-Konformität

### 7.2.1 Relevante Paragraphen

| Paragraph          | Inhalt                      | Umsetzung im BR Manager                                                                                                      |
|--------------------|-----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| § 29 BetrVG        | Einberufung der Sitzungen   | Tagesordnungsmodul: Erstellung, Versand der Einladung mit Tagesordnung                                                       |
| § 30 BetrVG        | Betriebsratssitzungen       | Meeting-Management: Dokumentation von Ort/Adresse, Zeit, Teilnehmer; Unterstützung von Online-, Hybrid- und Präsenzsitzungen |
| § 33 BetrVG        | Beschlüsse des Betriebsrats | Beschlussmodul: Erfassung der Mehrheitsverhältnisse, Quorum-Prüfung                                                          |
| § 34 BetrVG        | Sitzungsniederschrift       | Protokollmodul: Rechtssichere Protokollierung mit Freigabe-Workflow                                                          |
| § 25 BetrVG        | Ersatzmitglieder            | Anwesenheitsmodul: Nachrück-Reihenfolge gemäß Wahlergebnis                                                                   |
| § 15 Abs. 2 BetrVG | Geschlechterverteilung      | Ersatzmitglieder-Vorschläge: Berücksichtigung der Geschlechterquote                                                          |
| § 28 BetrVG        | Ausschüsse                  | Ausschussverwaltung: Separate Verwaltung mit delegierten Befugnissen, inkl. externer Ausschussmitglieder                     |
| § 37 Abs. 2 BetrVG | Arbeitsbefreiung            | Kalendermodul: Dokumentation von BR-Tätigkeiten und Reisedaten                                                               |
| §§ 99–101 BetrVG   | Personelle Einzelmaßnahmen  | Modul `personnel`: Erfassung, Fristenüberwachung und Beschlussfassung zu Einstellungen, Versetzungen, Kündigungen etc.       |

### 7.2.2 Anforderungen an die Sitzungsniederschrift (§ 34 BetrVG)

Das Protokoll muss enthalten:

- [x] **Wortlaut der Beschlüsse** → Beschlusstext im Resolution-Modell
- [x] **Abstimmungsergebnis** → votes_for, votes_against, abstentions
- [x] **Anwesenheitsliste** → AttendanceRecord mit Zeitstempeln
- [x] **Unterschrift des Vorsitzenden** → Digitale Unterschrift durch Vorsitz (signed_by_chair) mit kryptographischer
  Signatur
- [x] **Unterschrift eines weiteren Mitglieds** → Digitale Unterschrift durch Protokollführung (signed_by_clerk) mit
  kryptographischer Signatur
- [x] **Einsicht durch Mitglieder** → Lesezugriff für alle Gremiumsmitglieder
- [x] **Einspruchsmöglichkeit** → Genehmigung in nächster Sitzung (Finalisierungs-Workflow)

### 7.2.3 Anforderungen an die Beschlussfassung (§ 33 BetrVG)

- **Beschlussfähigkeit:** Mindestens die Hälfte der Betriebsratsmitglieder muss anwesend sein.
- **Automatische Prüfung:** System berechnet Beschlussfähigkeit vor Beginn der Sitzung und bei jeder Abstimmung.
- **Ersatzmitglieder:** Nachrückende Ersatzmitglieder werden als stimmberechtigte Mitglieder gezählt.
- **Dokumentation:** Beschlussfähigkeit wird im Protokoll dokumentiert.

### 7.2.4 Anforderungen an die Ersatzmitglieder-Nachrückung (§ 25 BetrVG)

- **Listenzugehörigkeit:** Bei Listenwahlen (Verhältniswahl) rückt ein Ersatzmitglied aus derselben Wahlliste
  (`election_list_name`) wie das verhinderte Mitglied nach.
- **Nachrück-Reihenfolge:** Innerhalb der Liste nach Listenplatz (`election_list_position`) und Stimmenzahl
  (`election_votes`) der Betriebsratswahl.
- **Geschlechterquote:** Das Minderheitengeschlecht darf nicht stärker unterrepräsentiert werden als im Wahlergebnis.
  Wird das Minderheitengeschlecht durch die Nachrückung unterschritten, rückt das nächste Ersatzmitglied derselben
  Liste mit dem entsprechenden Geschlecht nach.
- **Automatisierung:** System ermittelt korrekte Nachrückfolge unter Berücksichtigung von Listenzugehörigkeit,
  Listenplatz, Geschlechterregelung und Verfügbarkeit.

---

## 7.3 DSGVO-Konformität

### 7.3.1 Grundsätze der Datenverarbeitung (Art. 5 DSGVO)

| Grundsatz                        | Umsetzung                                                                                           |
|----------------------------------|-----------------------------------------------------------------------------------------------------|
| **Rechtmäßigkeit**               | Verarbeitung basiert auf Einwilligung (Art. 6 Abs. 1a) oder berechtigtem Interesse (Art. 6 Abs. 1f) |
| **Zweckbindung**                 | Daten werden ausschließlich für die Betriebsratsarbeit verwendet                                    |
| **Datenminimierung**             | Nur notwendige Daten werden erfasst (z. B. keine privaten Kontaktdaten ohne Einwilligung)           |
| **Richtigkeit**                  | Benutzer können eigene Daten jederzeit korrigieren                                                  |
| **Speicherbegrenzung**           | Aufbewahrungsfristen konfigurierbar, automatische Löschung nach Ablauf                              |
| **Integrität & Vertraulichkeit** | Verschlüsselung, Zugriffssteuerung, Audit-Logging                                                   |

### 7.3.2 Datenminimierung

**Pflichtfelder (minimal erforderlich):**

- Vorname, Nachname
- Geschlecht (erforderlich für § 15 Abs. 2 BetrVG)
- E-Mail-Adresse (für Systemzugang und Benachrichtigungen)

**Optionale Felder (nur mit Einwilligung):**

- Telefonnummer
- Profilbild
- Abteilung / Personalnummer

**Keine Erfassung von:**

- Privaten Adressen
- Gesundheitsdaten (das System speichert bewusst keinen konkreten Abwesenheitsgrund – nur „nachladbar"/„nicht
  nachladbar")
- Politische Zugehörigkeit oder Gewerkschaftsmitgliedschaft

### 7.3.3 Einwilligung

- **Aktive Einwilligung:** Benutzer müssen bei der Registrierung aktiv der Datenverarbeitung zustimmen.
- **Granulare Einwilligung:** Separate Einwilligung für optionale Datenfelder und Benachrichtigungskanäle.
- **Widerruf:** Einwilligung kann jederzeit widerrufen werden.
- **Dokumentation:** Alle Einwilligungen werden mit Zeitstempel protokolliert.

### 7.3.4 Rechte der Betroffenen

| Recht                              | Artikel | Umsetzung                                              |
|------------------------------------|---------|--------------------------------------------------------|
| **Auskunftsrecht**                 | Art. 15 | Export aller personenbezogenen Daten als JSON/PDF      |
| **Recht auf Berichtigung**         | Art. 16 | Benutzer können eigene Daten im Profil korrigieren     |
| **Recht auf Löschung**             | Art. 17 | Account-Löschung mit Anonymisierung historischer Daten |
| **Recht auf Einschränkung**        | Art. 18 | Deaktivierung des Accounts ohne Datenlöschung          |
| **Recht auf Datenübertragbarkeit** | Art. 20 | Export in maschinenlesbarem Format (JSON, CSV)         |
| **Widerspruchsrecht**              | Art. 21 | Opt-out für optionale Verarbeitung                     |

### 7.3.5 Löschkonzept

**Automatische Löschung nach konfigurierbaren Fristen:**

| Datentyp                   | Standard-Aufbewahrung       | Begründung                           |
|----------------------------|-----------------------------|--------------------------------------|
| Sitzungsprotokolle         | Amtszeit + 4 Jahre          | Gesetzliche Aufbewahrungspflicht     |
| Beschlüsse                 | Amtszeit + 4 Jahre          | Rechtssicherheit                     |
| Anwesenheitslisten         | Amtszeit + 1 Jahr           | Dokumentation der Beschlussfähigkeit |
| Audit-Logs                 | 2 Jahre                     | Nachvollziehbarkeit                  |
| Personelle Einzelmaßnahmen | Amtszeit + 4 Jahre          | Rechtssicherheit, Fristennachweis    |
| To-Do-Einträge             | 1 Jahr nach Erledigung      | Nachvollziehbarkeit                  |
| Benutzerkonten (inaktiv)   | 6 Monate nach letztem Login | Datenminimierung                     |
| Gastzugänge                | 30 Tage nach Ablauf         | Zeitbegrenzter Zugriff               |
| Benachrichtigungen         | 6 Monate                    | Datenminimierung                     |

**Anonymisierung statt Löschung:**

Für historische Protokolle und Beschlüsse werden personenbezogene Daten anonymisiert (z. B. „Mitglied A hat zugestimmt")
anstatt vollständig gelöscht, um die Rechtssicherheit der Dokumentation zu wahren.

### 7.3.6 Verzeichnis der Verarbeitungstätigkeiten (Art. 30 DSGVO)

Das System unterstützt die Erstellung eines Verarbeitungsverzeichnisses durch:

- Automatische Dokumentation aller Verarbeitungstätigkeiten
- Export-Funktion für das Verarbeitungsverzeichnis
- Angabe von Zweck, Rechtsgrundlage und Kategorien für jede Verarbeitungstätigkeit

### 7.3.7 Datenschutz-Folgenabschätzung (Art. 35 DSGVO)

Eine DSFA ist durchzuführen, da:

- Besondere Kategorien personenbezogener Daten verarbeitet werden können (Gewerkschaftszugehörigkeit implizit durch
  Betriebsratsmitgliedschaft).
- Umfangreiche und systematische Verarbeitung stattfindet.

**Empfehlung:** Vor Produktivbetrieb ist eine DSFA in Zusammenarbeit mit dem Datenschutzbeauftragten durchzuführen.

---

## 7.4 Verschlüsselung

### 7.4.1 Daten während der Übertragung (Data in Transit)

| Maßnahme            | Umsetzung                             |
|---------------------|---------------------------------------|
| TLS 1.3             | Alle HTTP-Verbindungen über HTTPS     |
| HSTS                | HTTP Strict Transport Security Header |
| Certificate Pinning | Optional für erhöhte Sicherheit       |

### 7.4.2 Daten im Ruhezustand (Data at Rest)

| Maßnahme                 | Umsetzung                                                                    |
|--------------------------|------------------------------------------------------------------------------|
| Datenbankverschlüsselung | PostgreSQL Transparent Data Encryption (TDE) oder verschlüsseltes Filesystem |
| Dateiverschlüsselung     | S3-Server-Side Encryption (SSE-S3 / SSE-KMS)                                 |
| Passwörter               | bcrypt/Argon2 Hashing (Django Standard)                                      |
| Backup-Verschlüsselung   | AES-256 verschlüsselte Backups                                               |

---

## 7.5 Aufbewahrungspflichten

### Betriebsverfassungsrechtliche Aufbewahrung

- **Sitzungsniederschriften:** Müssen für die Dauer der Amtszeit des Betriebsrats und darüber hinaus aufbewahrt werden.
- **Beschlüsse:** Müssen dauerhaft nachvollziehbar sein, solange sie Rechtswirkung entfalten.
- **Wahlunterlagen:** Separate Aufbewahrung gemäß Wahlordnung.

### Empfohlene Aufbewahrungsfristen

| Dokument               | Frist                    | Rechtsgrundlage              |
|------------------------|--------------------------|------------------------------|
| Protokolle             | Amtszeit + 4 Jahre       | BetrVG / Verjährungsfristen  |
| Beschlüsse             | Amtszeit + 4 Jahre       | BetrVG                       |
| Betriebsvereinbarungen | Solange gültig + 3 Jahre | BetrVG                       |
| Wahlunterlagen         | 4 Jahre                  | § 19 BetrVG (Wahlanfechtung) |
| Audit-Logs             | 2 Jahre                  | DSGVO-Nachweispflicht        |

---

## 7.6 Compliance-Checkliste

| Nr. | Anforderung                                                    | Status | Umsetzung                                           |
|-----|----------------------------------------------------------------|--------|-----------------------------------------------------|
| 1   | Protokolle enthalten Beschlusswortlaut und Abstimmungsergebnis | ✅      | Minutes + Resolution Modelle                        |
| 2   | Anwesenheitsliste wird geführt                                 | ✅      | AttendanceRecord                                    |
| 3   | Protokoll wird vom Vorsitz und weiterem Mitglied unterzeichnet | ✅      | Digitale Unterschriften (kryptographisch gesichert) |
| 4   | Beschlussfähigkeit wird geprüft                                | ✅      | Quorum-Check                                        |
| 5   | Ersatzmitglieder rücken nach korrekter Reihenfolge nach        | ✅      | Substitute-Suggestions                              |
| 6   | Geschlechterquote wird berücksichtigt                          | ✅      | Gender-Logic in Suggestions                         |
| 7   | Nur notwendige Daten werden erfasst                            | ✅      | Minimale Pflichtfelder                              |
| 8   | Einwilligung wird eingeholt und dokumentiert                   | ✅      | Consent-Management                                  |
| 9   | Betroffenenrechte können ausgeübt werden                       | ✅      | Export, Löschung, Berichtigung                      |
| 10  | Daten werden verschlüsselt gespeichert und übertragen          | ✅      | TLS 1.3, Encryption at Rest                         |
| 11  | Zugriffskontrolle ist implementiert                            | ✅      | RBAC + Audit-Logging                                |
| 12  | Aufbewahrungsfristen sind konfiguriert                         | ✅      | Retention Policy                                    |
| 13  | DSFA ist durchgeführt                                          | ⏳      | Vor Produktivbetrieb erforderlich                   |
| 14  | Verarbeitungsverzeichnis ist erstellt                          | ⏳      | Export-Funktion vorhanden                           |
| 15  | Personelle Einzelmaßnahmen: Fristen werden überwacht           | ✅      | Automatische Fristberechnung und Warnungen          |
| 16  | Digitale Unterschriften sind kryptographisch gesichert         | ✅      | Hash des Inhalts + Benutzer-ID + Zeitstempel        |
