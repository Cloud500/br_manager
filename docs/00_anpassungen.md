# Änderungen/Anpassungen

## [03_funktionalitaeten.md](03_funktionalitaeten.md)

Mir fehlt ein "Sitzungsmodell"
Also Eine Sitzung hat ja gewisse Metadatan, Typ (Online, Hybrid, Präsenz) Datum, Ort/Adresse (Bei Hybrid/Präsenz), etc.

An das Sitzungsobjekt ist dann auch Tagesordnung, Protokoll, Awesenheiten etc. Verknüpft.

Vorsitzende und Protokollführung (Gremium oder Ausschuss) können auch einen oder mehrere Vertretungen haben, diese haben die selben rechte wie ihre passenden "gegenstücke"
Sitzung wird dann von einem Vorsitz/Ersatz "eröffnet" und entsprechend als Vorsitz  für diese Sitzung Eingetragen. Gleiches analog für Protokollführung

### Generelles

Externe Ausschuss Mitglieder
Es muss etwas angepasst werden, Ausschüsse können Externe, nicht Gremiumsmitgllieder haben (z.B. Wirtschaftsausschuss)
Diese haben, solange sie mitglied in dem Gremium sind, zugriff auf alle Daten/Dokumente ihres Auschschusses, aber niemals auf die anderer Ausschüsse oder des Gremiums.



### 3.3.2 Freigabeprozess

Das Einreichen der Prüfung ist quasi Unnötig, nachdem das Protokoll von der Protokollführung als "fertig" erachtet wird,
Untershreibt sie Digital das Protokoll und der/die Vorsitzende unterschreibt das Protokoll danach auch digital.
Das ist gleichzusetzen mit der Vorläufigen Genehmigung.
(Wie das mit der Digitalen Unterschrift umsetzbar ist, musst du dir noch überlegen, falls noch nicht geschehen)

### 3.4.1 Digitale Bestätigung

Natürlich nur bei Online/Hybriieden Sitzungen nötig, bei reinen Präsenz sitzunen, wird von der Protokollführung das selbstständig ausgewählt/eingetragen
und es muss ein Dokument (Gescannte Anwesenheitsliste) an das Protokoll gehangen werden
(Am besten lässt sich die Vorlage mit den zu erwartenden Mitgliedern erstellen und ausdrucken, denk an freie felder für Spontane änderungen)


### 3.4.2 Ersatzmitglieder-Vorschläge

Klarer definieren, dass die geladenen Ersatzmitglieder denselben Zugriff auf "alle" Informationen während ihres Einsatzes haben?
Also von Einladung, bis zum Abschluss der Sitzung (oder manuell auch verlängerbar).
Sie werden während der Zeit wie ein reguläres Gremiumsmitglied behandelt.

### 3.5.2 Zugriffssteuerung

Anpassung bezüglich "Externe Ausschuss Mitglieder" nötig

### 3.6 Beschlusssystem

Für beschlüsse soll die möglichkeit bestehen diese am ende einer Sitzung an den Arbeitgeber zu übermitteln.
Also eine aus dem Beschluss generierte PDF Per mal versenden (nur Beschlusstext, Begründung, Beschlussfähigkeit Ja/Nein und Antrag ist angenommen Ja/Nein)


### 33.6.2 Wahlen

Wahlen nur bei Präsenzsitzungen möglich (Entsprechende Warnung wenn man eine WAHL TOP in eine Online/Hybrid Sitzung verwenden will)
Kein Automatismuss, ergebnisse werden manuell eingetragen, keine "Wahlsoftware" innerhalb des Projektes

### 3.7.2 Rechtekonzept pro Gremium

In der Auflistung fehlt Protokollführung
Mitglieder sollten auch Vollzugriff haben, Ersatzmitglieder im einsatz ebenso
Gäste haben zugriff auf die Tagesordnung und das Protokoll nur wenn sie selbst Eingeladen sind


### 3.9 Kalenderintegration

Für Präsenzmeetings sollten Geladene die möglichkeit haben im Termin zusätzliche daten für sich (nicht für alle einsehbar) zu hinterlegen
Hotel Gebucht Ja/Nein, Adresse des Hotels, Notizen


### Neue Funktionen

#### To-Do Liste

Verwaltung von To-Do's zuordnung von mehreren Mitgliedern, Fälligkeitsdatum etc.

#### Personelle einzelmaßnahmen

Einem Gremium kann die Option gegeben werden, Personelle einzelmaßnahmen zu verarbeiten (Lesbar und einsehbar für alle Gremiumsmitglieder)
Dort müssen Einstellungen, Versetzungen, Vertragsänderungen und Kündigungen verwaltet werden können.

In den Daten müssen Dokumente angehangen werden und braucht relevante infomationen
- Art der Maßnahme (Eisntellung, Änderung, Kündigung)
- Dokumente
- Notizen/Beschreibung

Zusätzlich datzu analog zu den TOP auch eigene Notizen/Informationen während der Sitzung

Das system soll so aufgebaut werden, das der Ausschuss jede Maßnahme mit auf die TOP für seine Sitzung setzen kann und die entsprechend, Analog zu Beschlüssen Abstimmen können (auch mit notizen)
Wichtig hier ist, das es Eine 7 Tagesfrist nach eingang der Maßnahme gibt, diese muss auch am besten Sichtbar gemacht werden ggf. mit benachrichtigung.
DAs ergebnniss der Maßnahmen kann am ende der Sitzung per Mail versendet werden.

Hier braucht es vorbereitet eine API schnittstelle um von "extern" PErsonelle Maßnahmen erstellen zu können (Später von der PErsonalabteilung)
