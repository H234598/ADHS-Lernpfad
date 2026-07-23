# Automatisierungsprompt: tägliche neue Einheit

Dieser Prompt wird durch die externe Automation täglich um **06:00 Uhr Europe/Berlin** ausgeführt. Der Lauf erzeugt genau eine neue Lerneinheit und endet nach dem Erstellen eines Draft-Pull-Requests. Er wartet nicht auf CodeRabbit und führt keinen Merge durch.

Arbeite im Repository `H234598/ADHS-Lernpfad`.

## 1. Sicherheits- und Vorabprüfung

1. Lade den aktuellen Stand von `main`.
2. Suche nach offenen Pull Requests gegen `main`, deren Head-Branch dem Muster `agent/einheit-*` entspricht oder deren Beschreibung den Marker `<!-- adhs-daily-unit -->` enthält.
3. Falls bereits ein solcher Pull Request offen ist, erstelle **keine** weitere Einheit und keinen weiteren Branch. Melde den vorhandenen PR als Blocker.
4. Stelle sicher, dass das Arbeitsverzeichnis sauber ist und der neue Branch vom aktuellen `main` ausgeht.
5. Lies `README.md`, `00-Einfuehrung.md`, `index.json`, alle bisherigen Kapitel, `Glossar.md`, die Referenzkarten, `references/README.md`, `ROADMAP.md` und alle einschlägigen Dateien unter `prompts/`.
6. Führe vor dem Schreiben vollständig `prompts/DEEP-RESEARCH-PROMPT.md` aus.

## 2. Auftrag

Ergänze **genau eine** neue fortlaufende Lerneinheit. Bestimme die nächste freie Einheitsnummer und den fachlich logischen nächsten Baustein. Prüfe, ob bestehende Kapitel wegen neuer Evidenz korrigiert werden müssen. Änderungen an Alttexten müssen im PR ausdrücklich begründet werden.

## 3. Verbindlicher Umfang

Eine Einheit ist eine echte **10- bis 20-minütige Lerneinheit**, nicht nur eine Kurznotiz mit entsprechendem YAML-Etikett.

- Harte Untergrenze: **800 Fließtextwörter** nach Abzug von YAML, Navigation und Diagrammcode.
- CI-Warnung außerhalb des Zielbereichs von **1.200–2.500 Fließtextwörtern**.
- Zielbereich: **1.200–2.500 Fließtextwörter**.
- Harte Obergrenze: **3.000 Fließtextwörter**.
- Legacy-Einheiten 1–10 behalten ihre Wortzahlanzeige, erzeugen aber keine Zielbereichswarnung; harte Unter- und Obergrenze gelten weiterhin.
- Wird mehr Platz benötigt, teile das Thema in mehrere logisch aufeinanderfolgende Einheiten; in diesem Lauf wird dennoch nur die erste Einheit erstellt.
- Niemals künstlich durch Wiederholung, Füllsätze oder erzwungene Autismus-/Parkinson-Bezüge verlängern.

## 4. Pflichtstruktur jeder Einheit

Jede Einheit enthält mindestens:

1. YAML-Frontmatter mit `title`, `level`, `estimated_time: 10–20 min`, `difficulty`, `prerequisites`, `tags`, `last_reviewed`, `evidence`, `status`, `references`, `minimum_reading_minutes: 10` und `maximum_reading_minutes: 20`;
2. ein klares Lernziel;
3. eine verständliche Einführung und Begriffsabgrenzung;
4. mindestens drei inhaltliche Erklärungsabschnitte;
5. eine wissenschaftliche Einordnung mit Grenzen und Heterogenität;
6. mindestens ein sinnvolles Mermaid-Diagramm, wenn ein Prozess oder Zusammenhang dargestellt wird;
7. eine kleine alltagstaugliche Übung oder Beobachtungsaufgabe, sofern fachlich sinnvoll;
8. Verbindungen zu Autismus oder Parkinson nur, wenn sie fachlich relevant sind;
9. eine Review-Frage mit in `<details>` ausklappbarer Antwort;
10. eine hochwertige Kernquelle als Studienkarte;
11. einen präzisen Merksatz;
12. Navigation zur vorherigen und nächsten Einheit.

## 5. Wissenschaftliche Regeln

- Trenne gut abgesicherte Befunde, plausible Modelle und offene Fragen.
- Kennzeichne Gruppenbefunde; leite daraus keine sicheren Aussagen über Einzelpersonen ab.
- Vermeide populäre Verkürzungen wie „ADHS ist Dopaminmangel“ und „Dopamin ist das Glückshormon“.
- Stelle ADHS, Autismus und Parkinson niemals als dieselbe Art von Erkrankung dar.
- Verwende keine Foren, SEO-Ratgeber oder Herstellertexte als Evidenz.
- Gib DOI, PubMed-ID oder stabilen Verlagslink an, soweit vorhanden.
- Formuliere keine Diagnose- oder Therapieversprechen.
- Bevorzuge die aktuelle wissenschaftliche Lehrmeinung gegenüber veralteten Darstellungen und dokumentiere relevante Abweichungen.

## 6. Dateipflege

1. Lege die Einheit im fachlich passenden Ordner ab.
2. Lege neue Quellen als einzelne Dateien in `references/` an. Pflege sämtliche bibliografischen Felder strukturiert unter `citation` entsprechend `references/README.md`. Der Abschnitt `Vollständige Zitation` muss exakt aus diesen Feldern reproduzierbar sein.
3. Erzeuge `Literatur.md`, `references.bib` und `references.json` ausschließlich mit `scripts/build_literature.py`; bearbeite diese drei Dateien nicht unabhängig voneinander.
4. Ergänze neue Fachbegriffe in `Glossar.md`.
5. Ergänze passende Anki-Karten in `cards/cards.yaml`.
6. Aktualisiere README, Index, MkDocs-Navigation und Wissensgraph-Verknüpfungen.
7. Verwende weiterhin Obsidian-Wikilinks in den Quelldateien. Aliasnamen, Unterordner und Überschriftenanker müssen von `scripts/validate_links.py` eindeutig auflösbar sein.
8. Erhalte die Datei `CNAME` exakt mit dem Inhalt `ADHS.telacore.org`.
9. Verändere keine Dateien unter `.github/` oder `prompts/`, keine Validatoren, Requirements, Build-, Veröffentlichungs-, Sicherheits- oder Synchronisationsinfrastruktur, sofern dies nicht zwingend für die neue Einheit erforderlich ist.
10. Falls eine solche sensible Datei zwingend geändert werden muss, erläutere jede Änderung im PR und füge der PR-Beschreibung den Marker `<!-- manual-merge-required -->` hinzu. Dieser PR darf nicht automatisch gemergt werden.

## 7. Pflichtprüfungen

Führe aus:

```bash
python3 scripts/build_literature.py
git diff --exit-code -- Literatur.md references.bib references.json
python3 scripts/validate_links.py
python3 scripts/build_graph.py
python3 scripts/validate_compendium.py
python3 scripts/build_combined.py
python3 scripts/build_anki.py
python3 scripts/build_docs.py
mkdocs build --strict
```

Alle Prüfungen müssen erfolgreich beendet sein. Die Validierung muss insbesondere Mindest- und Maximallänge, Pflichtabschnitte, Quellen, Obsidian-Wikilinks, Bibliografiekonsistenz und fortlaufende Nummerierung prüfen.

## 8. Git-Arbeitsweise

1. Erstelle vom aktuellen `main` einen Branch nach dem Schema `agent/einheit-NN-kurztitel`.
2. Committe ausschließlich die zur Einheit gehörenden Änderungen.
3. Pushe den Branch zu `origin`.
4. Erstelle einen **Draft-Pull-Request** gegen `main`.
5. Füge in die PR-Beschreibung den unsichtbaren Marker `<!-- adhs-daily-unit -->` ein.
6. Nenne im PR:
   - Umfang und Fließtextwortzahl,
   - verwendete Evidenzarten,
   - zentrale Quellen,
   - Unsicherheiten und Limitationen,
   - geänderte Alttexte mit Begründung,
   - sämtliche lokalen Prüfergebnisse,
   - den Zustand der generierten Markdown-, BibTeX- und CSL-Ausgaben,
   - alle geänderten sensiblen Dateien,
   - Branch und Head-Commit.
7. Prüfe nach der PR-Erstellung, dass der Head-Branch tatsächlich diesem PR zugeordnet ist und der PR den aktuellen Head-Commit enthält.
8. Lasse den PR im Draft-Status. Markiere ihn nicht als „Ready for review“ und merge ihn nicht.
9. Melde abschließend PR-Nummer, PR-Link, Branch, Head-Commit, Wortzahl und Prüfergebnisse.

Falls Push oder PR-Erstellung wegen fehlender Berechtigungen scheitern, dokumentiere Branch, lokalen Commit und die genaue Fehlermeldung. Ein gepushter Branch darf nicht still ohne PR liegen bleiben. Führe keinen direkten Commit auf `main` aus.

## 9. Additiver Lauf-, Recovery- und Duplikatschutz

Alle vorstehenden wissenschaftlichen, bibliografischen, CNAME-, Infrastruktur-,
CI- und PR-Regeln bleiben vollständig verbindlich. Der Statusmechanismus ergänzt
sie und darf keinen Abschnitt dieses Prompts ersetzen oder verkürzen.

### 9.1 Kanonischen Vorgängerstatus prüfen

1. Erzeuge vor der ersten Repositoryänderung eine portable, kollisionssichere
   `run_id`. In GitHub Actions ist sie zwingend aus der unveränderlichen
   GitHub-Run-ID und dem Run-Attempt zu bilden
   (`<GITHUB_RUN_ID>-<GITHUB_RUN_ATTEMPT>`); außerhalb von GitHub verwende eine
   UUIDv4. Der geplante UTC-Zeitpunkt ist nur Kontextmetadatum und niemals
   alleinige `run_id`. Prüfe vor `start`, dass der kanonische Laufpfad noch
   nicht existiert. Bei Recovery wird dagegen exakt die bereits vorhandene
   `run_id` wiederverwendet; eine Kollision darf weder überschrieben noch durch
   eine neue ID umgangen werden.
2. Lies auf dem orphan Branch `automation-status`
   `automation/status/generator/latest.json` und validiere ihn gegen
   `automation/run-status.schema.json`.
3. Führe, wenn ein lokaler Checkout verfügbar ist, zusätzlich aus:

   ```bash
   python scripts/automation_status.py guard --workflow generator
   ```

4. Ein nicht quittierter Status `failed`, `blocked` oder `recovering`, ein noch
   laufender Vorgänger sowie ein vorhandener automatischer Einheiten-PR
   blockieren eine neue Einheit. Führe dann ausschließlich die dokumentierte
   Recovery desselben Laufs aus.
5. Ignoriere einen fehlenden oder unlesbaren Status nicht. Melde ihn als
   `configuration`- oder `repository_state`-Blocker und prüfe GitHub-Branch,
   offenen PR und vorhandene Artefakte, bevor neuer Inhalt entsteht.

### 9.2 Status desselben Laufs fortschreiben

Der kanonische Pfad lautet:

```text
automation/status/generator/<run_id>.json
```

`latest.json` ist die validierte Kopie derselben Revision. Schreibe Statusdateien
niemals auf den Inhaltsbranch oder direkt nach `main`, sondern ausschließlich
atomar in einem separaten Checkout des Branches `automation-status`. Verwende
für jede Aktualisierung dieselbe `run_id` und die erwartete `revision`. Setze
vor den folgenden CLI-Beispielen den Statuswurzelpfad dieses Checkouts:

```bash
export AUTOMATION_STATUS_ROOT="$STATUS_WORKTREE/automation/status"
```

Falls die Umgebung keine Variablenübergabe unterstützt, füge jedem Befehl
`--root "$STATUS_WORKTREE/automation/status"` hinzu.

Vor jeder schreibenden Statusoperation liest du die aktuelle `revision` der
Laufdatei in `REVISION` ein und übergibst
`--expected-revision "$REVISION"`. Direkt nach einem erfolgreichen Übergang
liest du die neue Revision erneut ein. Exitcode `20` oder eine abweichende
Revision bedeutet CAS-Konflikt: Statusbranch neu laden, Lauf- und
`latest.json` erneut prüfen und den Schritt nur auf der neuen Revision
wiederholen. Überschreibe niemals eine fremde neuere Revision.

Nach jeder kritischen Statusrevision validierst du sowohl
`automation/status/generator/<run_id>.json` als auch
`automation/status/generator/latest.json` einzeln mit
`scripts/validate_runtime_status.py`. Vergleiche danach die geparsten Felder
`workflow`, `run_id` und `revision`; alle drei müssen identisch sein. Erst dann
commitest du ausschließlich die betroffene Laufdatei, `latest.json` und ihre
Diagnoseberichte im Status-Worktree und pushst normal nach
`automation-status`. Verwende keinen Force-Push.

Vor jedem kritischen Schritt wird die entsprechende Phase gesetzt:

| Bestehender Arbeitsschritt | Statusphase |
|---|---|
| aktuellen Hauptbranch laden | `load_main` |
| Vorgängerlauf prüfen | `check_previous_run` |
| offenen Einheiten-PR prüfen | `check_existing_pr` |
| Prompts vollständig lesen | `read_prompts` |
| Deep Research | `research` |
| Branch erzeugen | `create_branch` |
| Einheit und Quellen schreiben | `create_content` |
| Literatur, Graph, Anki und Dokumentation erzeugen | `generate_outputs` |
| alle Pflichtprüfungen | `validate` |
| Commit | `commit` |
| Push | `push` |
| Draft-PR erstellen | `create_pr` |
| Head-Branch, Commit und PR-Zuordnung prüfen | `verify_pr` |
| erfolgreicher Abschluss dieses Generatorlaufs | `complete` |

Beispiel:

```bash
python scripts/automation_status.py start \
  --workflow generator --run-id "$RUN_ID" --phase initialize
REVISION=1
python scripts/automation_status.py phase \
  --workflow generator --run-id "$RUN_ID" --phase load_main \
  --expected-revision "$REVISION"
```

Lies anschließend die tatsächlich geschriebene Revision erneut aus der
Laufdatei; rechne sie nicht lokal hoch.

### 9.3 Wiederverwendbare Artefakte sofort registrieren

Registriere unmittelbar nach ihrer erfolgreichen Entstehung:

```bash
python scripts/automation_status.py artifact \
  --workflow generator --run-id "$RUN_ID" \
  --type branch --value "$BRANCH" --reusable \
  --expected-revision "$REVISION"
python scripts/automation_status.py artifact \
  --workflow generator --run-id "$RUN_ID" \
  --type commit --value "$COMMIT_SHA" --reusable \
  --expected-revision "$REVISION"
python scripts/automation_status.py artifact \
  --workflow generator --run-id "$RUN_ID" \
  --type pull_request --value "#$PR_NUMBER" \
  --url "$PR_URL" --reusable \
  --expected-revision "$REVISION"
```

Falls nach dem Push nur die PR-Erstellung scheitert, wiederhole ausschließlich
`create_pr` mit dem vorhandenen Branch und Commit. Erzeuge niemals wegen eines
transienten GitHub-Fehlers eine zweite Einheit.

### 9.4 Fehler und Recovery

Erfasse Fehler mit einer der im Schema definierten Klassen und einem konkreten
Recovery-Level. Beispiele:

```bash
python scripts/automation_status.py fail \
  --workflow generator --run-id "$RUN_ID" \
  --class github_api_transient --code create_pr_failed \
  --message "PR-Erstellung temporär fehlgeschlagen" \
  --recovery resume_from_artifact --retryable \
  --expected-revision "$REVISION"

python scripts/automation_status.py recover \
  --workflow generator --run-id "$RUN_ID" --phase create_pr \
  --expected-revision "$REVISION"
```

Auch zwischen direkt aufeinanderfolgenden Befehlen wird `REVISION` jeweils aus
der Laufdatei neu gelesen. Eine für zwei Schreibbefehle wiederverwendete
Revision ist unzulässig.

Zugangsdaten, komplette Prompts, E-Mail-Adressen und medizinische Inhalte dürfen
nicht im Status stehen. Ein wissenschaftlich oder sicherheitsrelevant nicht
eindeutig lösbarer Fehler verwendet `manual_intervention`; ein terminaler Fehler
blockiert neue Generatorläufe bis zur bewussten Quittierung.

### 9.5 Mindestdiagnose bei fehlender Schreibmöglichkeit

Falls der Branch `automation-status` nicht beschrieben werden kann, darf die
fachliche Fehlermeldung dadurch nicht verdeckt werden. Gib in der Antwort
mindestens den vollständigen redigierten Diagnoseblock aus:

```text
ADHS-Automation fehlgeschlagen
Lauf: <workflow>/<run_id>
Status: <status>
Phase: <phase>
Revision: <revision>
Erfolgreich: <abgeschlossene Phasen>
Vorhanden: <Branch, Commit, PR und weitere Artefakte>
Fehlerklasse: <Klasse>
Fehlercode: <Code>
Fehler: <konkrete redigierte Ursache>
Recovery-Level: <Level>
Recovery: <nächster sicherer Schritt>
Neuer Inhalt erforderlich: ja/nein
Blockiert nächsten Generatorlauf: ja/nein
```

Beende einen erfolgreichen Generatorlauf erst nach der PR-Zuordnungsprüfung:

```bash
python scripts/automation_status.py finish \
  --workflow generator --run-id "$RUN_ID" --phase complete
```
