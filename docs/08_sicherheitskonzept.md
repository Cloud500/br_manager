# 08 – Sicherheitskonzept

## 8.1 Übersicht

Das Sicherheitskonzept des BR Managers umfasst technische und organisatorische Maßnahmen zum Schutz der Vertraulichkeit, Integrität und Verfügbarkeit aller verarbeiteten Daten. Die Maßnahmen orientieren sich an den Anforderungen der DSGVO, des BetrVG sowie an bewährten Sicherheitsstandards (OWASP, BSI-Grundschutz).

## 8.2 Authentifizierung

### 8.2.1 Primäre Authentifizierung

| Methode | Beschreibung |
|---------|-------------|
| **Lokaler Login** | E-Mail + Passwort mit Django's Auth-System |
| **SSO (OAuth2)** | Single Sign-On über OAuth2-fähigen Identity Provider (z. B. Azure AD, Keycloak) |

### 8.2.2 Passwort-Richtlinien

| Regel | Wert |
|-------|------|
| Mindestlänge | 12 Zeichen |
| Komplexität | Groß-/Kleinbuchstaben, Ziffern, Sonderzeichen |
| Passwort-Historie | Letzte 5 Passwörter gesperrt |
| Maximales Alter | 90 Tage (konfigurierbar) |
| Brute-Force-Schutz | Account-Sperre nach 5 Fehlversuchen (15 Min. Lockout) |
| Hashing-Algorithmus | Argon2id (Django-Standard ab 5.x) |

### 8.2.3 Zwei-Faktor-Authentifizierung (2FA)

- **Pflicht für:** Anwesenheitsbestätigung (rechtssichere Dokumentation).
- **Optional für:** Regulären Login (empfohlen für Vorsitz und Admin).
- **Unterstützte Methoden:**
  - TOTP (Time-based One-Time Password) – Authenticator-Apps (Google Authenticator, Authy, Microsoft Authenticator)
  - E-Mail-OTP als Fallback
- **Recovery:** Einmal-Codes (Recovery Codes) bei 2FA-Einrichtung generiert.

### 8.2.4 Session-Management

| Parameter | Wert |
|-----------|------|
| Session-Timeout (Inaktivität) | 30 Minuten |
| Maximale Session-Dauer | 8 Stunden |
| Gleichzeitige Sessions | Maximal 3 pro Benutzer |
| Session-Speicher | Redis (serverseitig) |
| Cookie-Flags | Secure, HttpOnly, SameSite=Strict |

## 8.3 Zugriffskontrolle

### 8.3.1 Rollenbasierte Zugriffskontrolle (RBAC)

Detailliert beschrieben in [06_berechtigungskonzept.md](06_berechtigungskonzept.md).

Zusammenfassung der Sicherheitsaspekte:

- **Principle of Least Privilege:** Benutzer erhalten nur die minimal notwendigen Rechte.
- **Kontextbasierte Rechte:** Ersatzmitglieder erhalten Zugriff nur während aktiver Einsatzzeit.
- **Zeitbegrenzter Zugriff:** Gastzugänge laufen automatisch ab.
- **Separation of Duties:** Protokollführung und Genehmigung sind getrennt.

### 8.3.2 Request-Sicherheit

| Maßnahme | Umsetzung |
|----------|----------|
| Authentifizierung | Django Sessions (Cookie-basiert, serverseitig) |
| CSRF-Schutz | Django CSRF-Middleware für alle POST/PUT/DELETE-Requests |
| Rate Limiting | Nginx-basierte Begrenzung der Anfragen pro IP und URL |
| Input Validation | Server-seitige Validierung aller Eingaben (Django Forms) |
| Content Security Policy | Restriktive CSP-Header |
| Request Size Limit | Maximale Anfragegröße: 10 MB (Uploads: 50 MB) |

## 8.4 Datensicherheit

### 8.4.1 Verschlüsselung

**Transport:**
- TLS 1.3 für alle Verbindungen (HTTPS)
- HSTS mit min. 1 Jahr max-age und includeSubDomains
- Deaktivierung von TLS 1.0 und 1.1

**Speicherung:**
- PostgreSQL: Verschlüsseltes Filesystem (LUKS) oder TDE
- Dateispeicher: AES-256 Server-Side Encryption
- Backups: AES-256 verschlüsselt
- Passwörter: Argon2id Hashing
- Sensible Konfiguration: Verschlüsselte Umgebungsvariablen oder Vault

### 8.4.2 Datenbankabsicherung

| Maßnahme | Beschreibung |
|----------|-------------|
| Prepared Statements | Django ORM verwendet parametrisierte Queries (SQL-Injection-Schutz) |
| Connection Encryption | SSL-Verbindung zwischen Django und PostgreSQL |
| Minimale Rechte | Datenbank-User hat nur notwendige Rechte (kein SUPERUSER) |
| Connection Pooling | pgBouncer mit authentifiziertem Zugang |
| Backups | Automatisierte, verschlüsselte tägliche Backups |
| Point-in-Time Recovery | WAL-Archivierung für PostgreSQL PITR |

### 8.4.3 Dateispeicher-Absicherung

- Dokumente werden außerhalb des Web-Root gespeichert.
- Zugriff nur über authentifizierte Django Views (kein direkter URL-Zugriff).
- Virus-Scan bei Upload (ClamAV-Integration).
- Prüfsummen (SHA-256) zur Integritätsprüfung.
- Dateityp-Validierung (MIME-Type und Extension).

## 8.5 Anwendungssicherheit

### 8.5.1 OWASP Top 10 – Gegenmaßnahmen

| OWASP-Risiko | Maßnahme |
|-------------|----------|
| **A01 – Broken Access Control** | RBAC, Objekt-Level-Berechtigungen, Audit-Logging |
| **A02 – Cryptographic Failures** | TLS 1.3, Argon2id, AES-256, keine Klartext-Speicherung |
| **A03 – Injection** | Django ORM (parametrisierte Queries), Input-Validierung |
| **A04 – Insecure Design** | Threat Modeling, Security Reviews, Principle of Least Privilege |
| **A05 – Security Misconfiguration** | Gehärtete Konfiguration, kein DEBUG in Production, Security-Header |
| **A06 – Vulnerable Components** | Automatisierte Dependency-Scans (Dependabot/Snyk), regelmäßige Updates |
| **A07 – Auth Failures** | 2FA, Account-Lockout, Session-Management, Passwort-Richtlinien |
| **A08 – Data Integrity Failures** | Signierte Updates, Integritätsprüfung von Dokumenten (SHA-256) |
| **A09 – Logging Failures** | Umfassendes Audit-Logging, zentrale Log-Sammlung, Alerting |
| **A10 – SSRF** | URL-Validierung, Netzwerksegmentierung, kein direkter Server-to-Server-Zugriff |

### 8.5.2 Security-Header

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 8.5.3 Dependency Management

- **Automatisierte Scans:** GitHub Dependabot oder Snyk für bekannte Schwachstellen.
- **Regelmäßige Updates:** Monatlicher Review und Update von Dependencies.
- **Lock-Files:** `requirements.txt` mit gepinnten Versionen.
- **SBOM:** Software Bill of Materials wird generiert und gepflegt.

## 8.6 Audit-Logging

### 8.6.1 Protokollierte Ereignisse

| Kategorie | Ereignisse |
|-----------|-----------|
| **Authentifizierung** | Login, Logout, fehlgeschlagene Anmeldeversuche, 2FA-Verifizierung, Passwortänderung |
| **Autorisierung** | Zugriffsversuche (erfolgreich und fehlgeschlagen), Rechteänderungen |
| **Datenzugriff** | Lesen, Erstellen, Ändern, Löschen von Ressourcen |
| **Administration** | Benutzerverwaltung, Rollenzuweisung, Systemkonfiguration |
| **Dokumente** | Upload, Download, Freigabe, Versionierung |
| **Beschlüsse** | Abstimmungen, Wahlergebnisse |
| **System** | Fehler, Warnungen, Performance-Anomalien |

### 8.6.2 Log-Format

Jeder Audit-Log-Eintrag enthält:

- **Zeitstempel** (UTC, ISO 8601)
- **Benutzer-ID** (oder „SYSTEM" für automatische Aktionen)
- **Aktion** (CREATE, READ, UPDATE, DELETE, LOGIN, etc.)
- **Ressourcentyp und -ID**
- **IP-Adresse**
- **User-Agent**
- **Vorherige und neue Werte** (bei Änderungen)
- **Ergebnis** (Erfolg/Fehlschlag)

### 8.6.3 Log-Sicherheit

- Audit-Logs sind **unveränderlich** (Append-Only-Tabelle, kein UPDATE/DELETE).
- Separate Datenbankverbindung mit eingeschränkten Rechten (nur INSERT und SELECT).
- Zentrale Aggregation über ELK Stack.
- Aufbewahrungsfrist: 2 Jahre (konfigurierbar).
- Automatische Alerts bei verdächtigen Mustern (z. B. Brute-Force, ungewöhnliche Zugriffsmuster).

## 8.7 Netzwerksicherheit

### 8.7.1 Netzwerkarchitektur

```
                    Internet
                       │
                  ┌────┴────┐
                  │Firewall │
                  └────┬────┘
                       │
              ┌────────┴────────┐
              │   DMZ (Nginx)   │
              │  Reverse Proxy  │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │ Anwendungsnetz  │
              │  Django + Celery│
              └───┬─────────┬───┘
                  │         │
           ┌──────┴──┐ ┌───┴──────┐
           │Datenbank│ │  Redis   │
           │  Netz   │ │  Netz    │
           │(Postgr.)│ │          │
           └─────────┘ └──────────┘
```

### 8.7.2 Netzwerk-Maßnahmen

| Maßnahme | Beschreibung |
|----------|-------------|
| Netzwerksegmentierung | Datenbank und Redis nicht direkt aus dem Internet erreichbar |
| Firewall-Regeln | Nur notwendige Ports geöffnet (443 für HTTPS) |
| Reverse Proxy | Nginx als einziger Einstiegspunkt |
| Rate Limiting | Auf Nginx- und Anwendungsebene |
| DDoS-Schutz | Cloudflare oder äquivalenter Dienst (optional) |
| VPN | Administrativer Zugriff nur über VPN |

## 8.8 Penetrationstests und Sicherheitsüberprüfungen

### 8.8.1 Regelmäßige Prüfungen

| Prüfung | Frequenz | Durchführung |
|---------|----------|-------------|
| Automatisierte Schwachstellen-Scans | Wöchentlich | CI/CD-Pipeline (OWASP ZAP, Trivy) |
| Dependency-Audit | Bei jedem Build | Dependabot / Snyk |
| Code-Review (Security) | Bei jedem Pull Request | Entwicklungsteam + SAST-Tools |
| Penetrationstest | Jährlich | Externer Dienstleister |
| Security-Audit | Jährlich | Externer Dienstleister |
| DSGVO-Audit | Jährlich | Datenschutzbeauftragter |

### 8.8.2 Schwachstellen-Management

1. **Erkennung:** Automatisierte Scans und manuelle Prüfungen.
2. **Bewertung:** Klassifizierung nach CVSS-Score (Critical, High, Medium, Low).
3. **Behebung:** SLA basierend auf Schweregrad:
   - Critical: 24 Stunden
   - High: 7 Tage
   - Medium: 30 Tage
   - Low: Nächster Release-Zyklus
4. **Verifizierung:** Erneuter Test nach Behebung.
5. **Dokumentation:** Alle Schwachstellen und deren Behebung werden dokumentiert.

### 8.8.3 Statische Code-Analyse (SAST)

- **Tools:** Bandit (Python), ESLint Security Plugin (JavaScript/TypeScript)
- **Integration:** Pre-Commit-Hooks und CI/CD-Pipeline
- **Regeln:** OWASP-konforme Regelsets

## 8.9 Incident Response

### 8.9.1 Incident-Response-Plan

| Phase | Beschreibung |
|-------|-------------|
| **1. Erkennung** | Automatische Alerts, Benutzer-Meldungen, Audit-Log-Analyse |
| **2. Analyse** | Bestimmung des Umfangs, betroffene Daten und Benutzer |
| **3. Eindämmung** | Sofortmaßnahmen (Account-Sperrung, Netzwerkisolierung) |
| **4. Beseitigung** | Behebung der Schwachstelle, Bereinigung |
| **5. Wiederherstellung** | Rückkehr zum Normalbetrieb, Verifizierung |
| **6. Nachbereitung** | Lessons Learned, Anpassung der Maßnahmen |

### 8.9.2 Meldepflichten (DSGVO Art. 33/34)

- **Aufsichtsbehörde:** Meldung innerhalb von 72 Stunden bei Datenschutzverletzungen.
- **Betroffene:** Unverzügliche Benachrichtigung bei hohem Risiko für die Rechte der Betroffenen.
- **Dokumentation:** Alle Vorfälle werden im Incident-Register dokumentiert.

## 8.10 Backup und Disaster Recovery

### 8.10.1 Backup-Strategie

| Typ | Frequenz | Aufbewahrung | Speicherort |
|-----|----------|-------------|-------------|
| Vollbackup (Datenbank) | Täglich, 02:00 UTC | 30 Tage | S3-kompatibler Speicher (verschlüsselt) |
| Inkrementelles Backup (WAL) | Kontinuierlich | 7 Tage | S3-kompatibler Speicher |
| Dokumenten-Backup | Täglich | 30 Tage | Separater S3-Bucket |
| Konfigurations-Backup | Bei Änderung | 90 Tage | Git-Repository |

### 8.10.2 Recovery-Ziele

| Metrik | Zielwert |
|--------|---------|
| Recovery Point Objective (RPO) | ≤ 1 Stunde |
| Recovery Time Objective (RTO) | ≤ 4 Stunden |

### 8.10.3 Disaster-Recovery-Tests

- **Frequenz:** Quartalsweise
- **Umfang:** Vollständige Wiederherstellung aus Backup in Testumgebung
- **Dokumentation:** Ergebnisse und Verbesserungsmaßnahmen werden dokumentiert
