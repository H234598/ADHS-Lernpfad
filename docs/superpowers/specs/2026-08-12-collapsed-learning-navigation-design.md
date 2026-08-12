---
title: Eingeklappte Lernkategorien in der linken Navigation
aliases:
  - Collapsed Learning Navigation
  - Variante A der ADHS-kompatiblen Seitennavigation
tags:
  - adhs-lernpfad
  - ux
  - navigation
  - mkdocs-material
  - adhs-kompatibel
  - accessibility
type: design
status: approved
date: 2026-08-12
created: 2026-08-12T10:53:40+02:00
updates:
  - 2026-08-12: Variante A nach Repositoryanalyse ausgewählt und als verbindliches Design festgelegt.
---

# Eingeklappte Lernkategorien in der linken Navigation

## Ziel

Die Lernkategorien **Grundlagen** und **Vertiefung** sollen beim Einstieg auf eine Seite außerhalb dieser Kategorien zunächst geschlossen sein. Dadurch werden nicht sofort alle Lernkarten gleichzeitig sichtbar und die linke Navigation bleibt reizärmer und leichter erfassbar.

Sobald eine Person eine Kategorie bewusst öffnet oder eine Lernkarte innerhalb einer Kategorie direkt aufruft, muss die betroffene Kategorie geöffnet sein. Die jeweils andere Lernkategorie bleibt geschlossen.

## Verbindliche Entscheidung

Umgesetzt wird **Variante A: routenbezogener, nicht persistierter Zustand**.

Der Öffnungszustand wird nicht in `localStorage`, `sessionStorage`, Cookies oder einer eigenen JavaScript-Zustandsverwaltung gespeichert. Er ergibt sich ausschließlich aus der aktuellen Seite und aus einer manuellen Interaktion im aktuell gerenderten Navigationszustand.

## Verhaltensvertrag

### Einstieg außerhalb einer Lernkategorie

Auf folgenden Seitentypen sind **Grundlagen** und **Vertiefung** zunächst geschlossen:

- Startseite;
- Einführung;
- Downloads;
- Seiten des Wissenssystems;
- Roadmap;
- weitere Seiten, die keiner der beiden Lernkategorien angehören.

Die Kategorienamen bleiben sichtbar und können gezielt geöffnet werden.

### Manuelles Öffnen

Ein Klick oder eine äquivalente native Bedienung des MkDocs-Material-Toggles öffnet genau die ausgewählte Kategorie. Dafür wird die vorhandene Theme-Interaktion verwendet; es wird kein eigener Toggle nachgebaut.

### Direktaufruf einer Lernkarte

Beim direkten Aufruf einer Karte unter `01-Grundlagen/` wird **Grundlagen** automatisch geöffnet. Beim direkten Aufruf einer Karte unter `02-Vertiefung/` wird **Vertiefung** automatisch geöffnet.

Die aktive Karte bleibt in der Navigation sichtbar und als aktive Seite gekennzeichnet. Die jeweils andere Lernkategorie bleibt geschlossen.

### Seitenwechsel und erneuter Einstieg

Es gibt keine dauerhafte Erinnerung an zuvor manuell geöffnete Kategorien. Nach einem vollständigen Seitenaufruf entscheidet wieder allein die aktuelle Route:

- Lernkarte innerhalb einer Kategorie: zugehörige Kategorie geöffnet;
- Seite außerhalb der Kategorien: beide Kategorien geschlossen.

## Architektur

Das Repository verwendet MkDocs Material `9.7.7`. In `mkdocs.yml` ist derzeit das Feature `navigation.sections` aktiviert. Dieses Feature behandelt die verschachtelten Navigationseinträge der ersten Ebene als dauerhaft dargestellte Abschnitte.

Die Umsetzung entfernt ausschließlich `navigation.sections` aus `theme.features`. Die übrigen Features bleiben erhalten:

- `navigation.instant`;
- `navigation.top`;
- `search.highlight`;
- `content.code.copy`.

Ohne `navigation.sections` rendert MkDocs Material die verschachtelten Kategorien über seine nativen Checkbox- und Label-Toggles. Das Theme öffnet den aktiven Navigationspfad bereits selbst, sodass Direktlinks auf Lernkarten keine zusätzliche Logik benötigen.

## Bewusst ausgeschlossene Lösungen

Nicht umgesetzt werden:

- eigenes Sidebar-JavaScript;
- Speicherung in `localStorage` oder `sessionStorage`;
- globale Aktivierung von `navigation.expand`;
- CSS, das Theme-Zustände nur optisch versteckt;
- DOM-Manipulation nach dem Laden;
- automatische Öffnung beider Lernkategorien;
- Änderungen an der fachlichen Navigation oder Reihenfolge der Karten.

## ADHS-Kompatibilität

Die Lösung reduziert die gleichzeitig sichtbare Auswahl beim Einstieg, ohne Orientierung zu verlieren:

- Kategorien bleiben als klare Einstiegspunkte sichtbar;
- Inhalte erscheinen erst nach bewusster Auswahl;
- ein Direktlink verliert den Kontext nicht, weil der aktive Pfad automatisch geöffnet wird;
- es entsteht kein überraschender, über Sitzungen hinweg gespeicherter Zustand;
- die native Theme-Implementierung vermeidet zusätzliche Animationen, Fokusfallen und Sonderbedienung.

## Barrierefreiheit und Bedienbarkeit

Die vorhandenen MkDocs-Material-Toggles werden beibehalten. Damit verbleiben Beschriftung, Fokusverhalten, Zustandsdarstellung und Theme-seitige Tastaturbehandlung in einer einheitlichen Komponente.

Die Änderung darf keine eigene interaktive Schicht einführen. Browserprüfungen müssen mindestens bestätigen:

1. Beide Lernkategorien sind auf der Startseite geschlossen.
2. Eine Kategorie lässt sich gezielt öffnen.
3. Ein Direktaufruf einer Grundlagenkarte öffnet nur **Grundlagen**.
4. Ein Direktaufruf einer Vertiefungskarte öffnet nur **Vertiefung**.
5. Die jeweilige aktive Karte ist sichtbar.

## Fehler- und Regressionsschutz

Ein schneller Konfigurationstest schützt den Vertrag gegen spätere Aktivierung von:

- `navigation.sections`, weil dies die Kategorien wieder als dauerhaft sichtbare Abschnitte darstellt;
- `navigation.expand`, weil dies alle verschachtelten Navigationsbereiche global aufklappen würde.

Ein Playwright-Test prüft zusätzlich das tatsächlich gebaute HTML und die sichtbare Bedienung. Damit wird verhindert, dass eine formal passende Konfiguration durch Theme-, Template- oder CSS-Änderungen trotzdem das falsche Verhalten zeigt.

## Änderungsscope

### Produktionskonfiguration

- `mkdocs.yml`: `navigation.sections` aus `theme.features` entfernen.

### Automatisierte Tests

- `tests/test_navigation_configuration.py`: schneller Konfigurationsvertrag.
- `tests/web/navigation.spec.mjs`: sichtbares Verhalten im gebauten Webauftritt.

### Dokumentation

- diese Designspezifikation;
- der zugehörige Implementierungsplan.

Es werden keine Inhalte, Quellen, Karten, Wissensgraphdaten, Exporte, Abhängigkeiten oder CI-Berechtigungen verändert.

## Akzeptanzkriterien

Die Umsetzung ist akzeptiert, wenn alle folgenden Bedingungen erfüllt sind:

- [ ] Auf `/` sind **Grundlagen** und **Vertiefung** geschlossen.
- [ ] Ein manueller Klick auf **Grundlagen** öffnet Grundlagen, ohne Vertiefung zu öffnen.
- [ ] Auf `/01-Grundlagen/01-Was-ist-ADHS/` ist Grundlagen geöffnet und Vertiefung geschlossen.
- [ ] Auf `/02-Vertiefung/01-Pharmakologie-und-Psychotherapie/` ist Vertiefung geöffnet und Grundlagen geschlossen.
- [ ] Die jeweils aktive Karte ist in der linken Navigation sichtbar.
- [ ] Es existiert keine neue Zustands- oder Persistenzlogik.
- [ ] Der vollständige MkDocs-Build läuft im Strict-Modus.
- [ ] Die Playwright-Webtests sind grün.
- [ ] Die übrigen Repository-Gates bleiben grün.

## Rollback

Ein Rollback besteht ausschließlich darin, `navigation.sections` wieder in `theme.features` aufzunehmen und die zugehörigen neuen Regressionstests anzupassen oder zurückzunehmen. Es gibt keine Datenmigration und keinen gespeicherten Clientzustand, der bereinigt werden müsste.
