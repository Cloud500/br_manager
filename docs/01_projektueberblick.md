# 01 – Projektüberblick

## 1.1 Projektname

**BR Manager** – Digitales Betriebsrats-Management-System

## 1.2 Zielsetzung

Der BR Manager hat zum Ziel, die Arbeit von Betriebsräten vollständig digital abzubilden und zu unterstützen. Die Anwendung soll:

- Die Verwaltung von Sitzungen, Tagesordnungen und Protokollen vereinfachen und automatisieren.
- Beschlüsse und Abstimmungen rechtssicher dokumentieren.
- Die Anwesenheitsverwaltung inkl. Ersatzmitglieder-Logik digitalisieren.
- Ein integriertes Dokumentenmanagementsystem (DMS) bereitstellen.
- Die Einhaltung gesetzlicher Vorgaben (BetrVG, DSGVO) sicherstellen.
- Die Zusammenarbeit zwischen Gremien, Ausschüssen und deren Mitgliedern verbessern.

## 1.3 Problemstellung

Die Betriebsratsarbeit ist in vielen Unternehmen noch stark papierbasiert oder durch fragmentierte Tools geprägt. Dies führt zu:

- Mangelnder Nachvollziehbarkeit von Beschlüssen und Protokollen.
- Aufwändiger manueller Verwaltung von Anwesenheiten und Ersatzmitgliedern.
- Risiken bei der Einhaltung rechtlicher Vorgaben (BetrVG, DSGVO).
- Fehlender Versionierung und Zugriffskontrolle bei Dokumenten.
- Ineffizienter Kommunikation zwischen Gremiumsmitgliedern.

## 1.4 Stakeholder

| Rolle | Beschreibung | Interessen |
|-------|-------------|------------|
| **Betriebsratsvorsitzende/r** | Leitung des Betriebsrats | Effiziente Sitzungsführung, rechtssichere Dokumentation |
| **Betriebsratsmitglieder** | Ordentliche Mitglieder des Gremiums | Einfacher Zugriff auf Dokumente, Abstimmungen, Termine |
| **Ersatzmitglieder** | Stellvertretende Mitglieder | Zugriff auf relevante Daten während Einsatzzeit, Kalender |
| **Protokollführung** | Verantwortlich für Sitzungsprotokolle | Einfache Protokollerstellung und Freigabe-Workflow |
| **Ausschussmitglieder** | Mitglieder von Fachausschüssen | Separate Verwaltung, eigene Dokumente und Beschlüsse |
| **Gäste** | Zeitweise eingeladene Personen | Zeitbegrenzter Zugriff auf relevante Dokumente |
| **IT-Administration** | Technische Betreuung | Wartbarkeit, Sicherheit, Deployment |
| **Datenschutzbeauftragte/r** | DSGVO-Compliance | Datenschutzkonformität, Audit-Fähigkeit |

## 1.5 Projektumfang (Scope)

### In Scope

- Django-Monolith (Server-Side Rendering mit HTMX/Alpine.js, Responsive Webdesign)
- Tagesordnungsverwaltung mit Vorlagen
- Protokollverwaltung mit Freigabe-Workflow und Versionierung
- Anwesenheitsverwaltung mit 2FA-Bestätigung und Ersatzmitglieder-Logik
- Dokumentenmanagementsystem (DMS) mit Versionierung und Zugriffssteuerung
- Beschluss- und Abstimmungssystem
- Ausschussverwaltung mit separaten Rechten
- Kalenderintegration
- E-Mail-Benachrichtigungen
- Dynamische, konfigurierbare Rollen- und Rechteverwaltung
- Audit-Logging
- BetrVG- und DSGVO-konforme Umsetzung

### Out of Scope (Mitgedacht ohne Umsetzung)
- Integration in HR-Systeme (SAP, Workday etc.)
- Videokonferenz-Integration
- Öffentliche Betriebsversammlungs-Funktionalität

## 1.6 Erfolgskriterien

| Kriterium | Messung |
|-----------|---------|
| Vollständige Digitalisierung der Sitzungsverwaltung | Alle Sitzungen werden über das System abgewickelt |
| Rechtssichere Dokumentation | Audit bestätigt BetrVG- und DSGVO-Konformität |
| Benutzerakzeptanz | ≥ 80 % der Mitglieder nutzen das System aktiv |
| Verfügbarkeit | ≥ 99,5 % Uptime während Geschäftszeiten |
| Reaktionszeit | Seitenladezeit < 2 Sekunden |

## 1.7 Annahmen und Abhängigkeiten

### Annahmen

- Die Nutzer verfügen über einen modernen Webbrowser (Chrome, Firefox, Edge, Safari).
- Ein zentraler Mailserver ist für E-Mail-Benachrichtigungen verfügbar.
- Die IT-Infrastruktur unterstützt Docker-basiertes Deployment.
- OAuth2-fähiger Identity Provider ist vorhanden (z. B. Azure AD, Keycloak).

### Abhängigkeiten

- Verfügbarkeit eines PostgreSQL-Datenbankservers.
- Zugang zu einem SMTP-Server für E-Mail-Versand.
- Bereitstellung von SSL/TLS-Zertifikaten für verschlüsselte Kommunikation.
- Klärung der organisationsspezifischen Geschlechterregelungen für Ersatzmitglieder-Vorschläge.
