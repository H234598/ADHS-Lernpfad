#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import subprocess
import textwrap
import yaml

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "agent/einheit-14-autismus-adhs-koexistenz"
BOOTSTRAP = ROOT / ".unit14"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-unit14.yml"


def write(path: str, content: str) -> None:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    destination = ROOT / path
    text = destination.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Einfügestelle fehlt in {path}: {old!r}")
    destination.write_text(text.replace(old, new, 1), encoding="utf-8")


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


unit_path = "02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md"
write(
    unit_path,
    r'''
    ---
    title: "Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung"
    level: Vertiefung
    estimated_time: 10–20 min
    difficulty: 3
    prerequisites:
      - 01-Grundlagen/01-Was-ist-ADHS
      - 01-Grundlagen/08-Neuroentwicklung-und-Lebensspanne
      - 01-Grundlagen/09-Diagnostische-Kriterien-und-Differentialdiagnostik
      - 01-Grundlagen/10-Genetik-und-Umwelt
      - 02-Vertiefung/01-Pharmakologie-und-Psychotherapie
    tags: [ADHS, Autismus, Koexistenz, Differentialdiagnostik, Neuroentwicklung, Masking]
    last_reviewed: 2026-07-23
    evidence: high
    status: consensus
    references: [Young2020, Micai2023, Zhong2026, Waldren2024, Kofler2024, Demontis2023, Faraone2021]
    minimum_reading_minutes: 10
    maximum_reading_minutes: 20
    ---

    # Einheit 14 – Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung

    ## Lernziel

    Du kannst die diagnostischen Kernbereiche von ADHS und Autismus voneinander unterscheiden und zugleich erklären, warum beide Neuroentwicklungsstörungen häufiger gemeinsam auftreten. Du erkennst, weshalb ähnliche sichtbare Verhaltensweisen unterschiedliche Funktionen oder Entstehungswege haben können, warum Fragebögen und einzelne Tests keine Doppeldiagnose beweisen und wie diagnostisches Überschatten sowie Masking die Beurteilung erschweren. Außerdem verstehst du, warum gemeinsame genetische, kognitive oder neuronale Gruppenbefunde keine Gleichsetzung erlauben und weshalb Unterstützung die Bedürfnisse beider Diagnosen gleichzeitig berücksichtigen muss.

    ## 1. Zwei unterscheidbare Neuroentwicklungsstörungen können gemeinsam auftreten

    ADHS und Autismus werden beide als Neuroentwicklungsstörungen eingeordnet. Das bedeutet, dass ihre relevanten Merkmalsmuster früh in der Entwicklung beginnen und sich über die Lebensspanne in wechselnder Form zeigen können. Daraus folgt jedoch nicht, dass beide dasselbe seien oder lediglich verschiedene Schweregrade eines einzigen Spektrums darstellten.

    Bei ADHS liegen die diagnostischen Kernbereiche in einem anhaltenden Muster von **Unaufmerksamkeit** und/oder **Hyperaktivität-Impulsivität**, das in mehreren Lebensbereichen zu relevanter Beeinträchtigung führt. Bei Autismus betreffen die Kernbereiche anhaltende Besonderheiten der **sozialen Kommunikation und sozialen Interaktion** sowie **restriktive oder repetitive Verhaltensweisen, Interessen oder Aktivitäten**; dazu gehören in den Klassifikationssystemen auch sensorische Besonderheiten. Für beide Diagnosen müssen Entwicklungsgeschichte, Kontext und Funktionsbeeinträchtigung betrachtet werden.

    > [!evidence] Evidenz: Konsens / hoch
    > ADHS und Autismus sind diagnostisch unterscheidbare, heterogene Neuroentwicklungsstörungen. Sie können bei derselben Person gemeinsam vorliegen. Eine Diagnose darf die andere weder automatisch beweisen noch ausschließen.

    Bis zur Veröffentlichung des DSM-5 im Jahr 2013 war eine gleichzeitige formale Diagnose in älteren diagnostischen Regeln unnötig eingeschränkt. Diese historische Trennung wirkte lange auf Forschung und Versorgung nach. Heute ist die Koexistenz ausdrücklich anerkannt. Der fachlich passendere Ausgangspunkt lautet daher nicht „ADHS oder Autismus?“, sondern bei begründetem Verdacht: „Welche Kernmerkmale, Entwicklungsverläufe und Beeinträchtigungen sprechen für ADHS, für Autismus, für beides oder für eine andere Erklärung?“

    ## 2. Ähnliche Oberfläche bedeutet nicht gleiche Funktion

    Viele Alltagsbeobachtungen sind diagnostisch mehrdeutig. Eine Person unterbricht Gespräche, verpasst soziale Signale oder wirkt unflexibel. Solche Beschreibungen sagen zunächst, **was sichtbar geschieht**, aber noch nicht zuverlässig, **warum** es geschieht.

    Beispiele:

    - Ein Gesprächsbeitrag kann wegen impulsiven Antwortens zu früh kommen. Er kann aber auch entstehen, weil unausgesprochene Gesprächsregeln schwer erkennbar sind. Beides kann gleichzeitig vorkommen.
    - Soziale Kontakte können wegen vergessener Nachrichten, Zeitproblemen oder wechselnder Aufmerksamkeit abbrechen. Daneben können Schwierigkeiten mit wechselseitiger Kommunikation, impliziten Erwartungen oder sensorisch belastenden Situationen bestehen.
    - Eine Routine kann als externe Kompensation für ADHS-Organisation dienen. Sie kann zugleich ein starkes Bedürfnis nach Vorhersagbarkeit abbilden. Die sichtbare Regelmäßigkeit allein trennt beides nicht.
    - Intensive Beschäftigung kann durch hohes Interesse, Neuheit oder schwer unterbrechbare Aufmerksamkeit verstärkt werden. Ein starkes oder spezialisiertes Interesse ist trotzdem nicht automatisch ein autistisches Kernmerkmal; entscheidend sind Qualität, Entwicklung, Funktion und Gesamtmuster.
    - Reizempfindlichkeit kommt nicht ausschließlich bei Autismus vor. Schlafmangel, Angst, Migräne, Trauma, ADHS und weitere Bedingungen können sensorische Belastbarkeit verändern.

    ```mermaid
    flowchart TD
      V[sichtbares Verhalten] --> A[ADHS-bezogene mögliche Funktion]
      V --> U[autismusbezogene mögliche Funktion]
      V --> K[Komorbidität oder andere Erklärung]
      A --> G[Entwicklungsgeschichte und mehrere Kontexte]
      U --> G
      K --> G
      G --> B[begründete klinische Einordnung]
      B --> H[bedarfsgerechte Unterstützung]
    ```

    Das Diagramm zeigt keine private Diagnoseroutine. Es verdeutlicht, warum dieselbe Oberfläche über mehrere Informationsquellen und den Verlauf eingeordnet werden muss.

    ## 3. Koexistenz ist häufig – Prävalenzzahlen sind aber keine persönliche Diagnose

    Systematische Übersichten zeigen, dass ADHS zu den häufigen Begleitdiagnosen bei autistischen Menschen gehört. Umgekehrt finden Untersuchungen bei Menschen mit primärer ADHS-Diagnose nicht selten erhöhte autistische Merkmale. Die Größenordnungen schwanken jedoch stark zwischen Studien, weil Alter, Rekrutierung, intellektuelle und sprachliche Voraussetzungen, diagnostische Verfahren und Definitionen unterschiedlich sind.

    Eine große Meta-Analyse zu Begleiterkrankungen bei Autismus schloss 340 Publikationen mit insgesamt ungefähr 590.000 Teilnehmenden ein. Sie bestätigt ADHS als häufige koexistierende Bedingung, zeigt aber zugleich deutliche Unterschiede zwischen klinischen und populationsbezogenen Stichproben sowie zwischen Altersgruppen. Eine systematische Übersicht zu autistischen Symptomen bei primärer ADHS fand nur neun passende Studien und sehr variable Raten klinisch auffälliger Screeningwerte. Solche Screeningwerte sind keine Autismusdiagnosen.

    Drei Fehlschlüsse sind besonders wichtig:

    1. **„Viele Überschneidungen bedeuten, dass beide dasselbe sind.“** Häufige Koexistenz setzt begrifflich voraus, dass unterscheidbare Merkmalsbereiche gemeinsam vorkommen können.
    2. **„Ein hoher Autismusfragebogen bei ADHS beweist Autismus.“** Fragebögen können einen Abklärungsbedarf anzeigen; sie erfassen aber auch unspezifische Belastungen und überlappende Verhaltensweisen.
    3. **„Eine ADHS-Diagnose erklärt automatisch alle autistischen Merkmale.“** Dadurch kann eine zusätzliche Diagnose und passende Unterstützung übersehen werden.

    Gruppenprävalenzen helfen bei der Aufmerksamkeit für mögliche Koexistenz. Sie sagen nicht, ob eine konkrete Person beide Diagnosen erfüllt.

    ## 4. Gute Diagnostik prüft Kernbereiche, Entwicklung und mehrere Perspektiven

    Eine sorgfältige Beurteilung verbindet klinische Gespräche, Entwicklungsgeschichte, konkrete Beispiele aus mehreren Lebensbereichen und Fremdinformationen, soweit sie verfügbar und sinnvoll sind. Standardisierte Interviews, Fragebögen oder Beobachtungsverfahren können unterstützen, dürfen aber nicht isoliert entscheiden.

    Für ADHS wird beispielsweise geprüft, ob Unaufmerksamkeit oder Hyperaktivität-Impulsivität früh begonnen haben, situationsübergreifend auftreten und relevante Beeinträchtigungen verursachen. Für Autismus wird unter anderem rekonstruiert, wie soziale Gegenseitigkeit, nonverbale Kommunikation, Beziehungen, repetitive Muster, Interessen, Routinen und sensorische Verarbeitung seit der Entwicklung ausgeprägt waren. Dabei ist nicht jede Besonderheit krankhaft; diagnostisch zählt das gesamte Muster einschließlich Unterstützungsbedarf und Funktion.

    Informationen können widersprüchlich sein. Eine Person wirkt in einer strukturierten Untersuchung sehr angepasst, ist danach aber erschöpft. Eltern erinnern frühe Besonderheiten anders als die betroffene Person. Schule oder Beruf sehen nur die kompensierte Außenleistung. Solche Unterschiede sollten erklärt statt einfach gemittelt werden.

    **Masking** oder **Camouflaging** beschreibt Strategien, mit denen Menschen sichtbare autistische Merkmale verbergen, soziale Regeln bewusst nachahmen oder Belastung überspielen. Auch Menschen mit ADHS entwickeln Kompensationen, etwa extreme Kontrolle, mehrfaches Prüfen oder rigide Hilfssysteme. Masking ist kein eigener Beweis für Autismus und nicht auf ein Geschlecht beschränkt. Es kann jedoch erklären, warum äußere Unauffälligkeit und innere Belastung auseinanderliegen.

    **Diagnostisches Überschatten** wirkt in beide Richtungen. Nach einer Autismusdiagnose können Unaufmerksamkeit und Impulsivität vollständig als Teil des Autismus abgetan werden. Nach einer ADHS-Diagnose können soziale Kommunikationsunterschiede, repetitive Muster oder sensorische Bedürfnisse übersehen werden. Eine bereits bekannte Diagnose ist deshalb eine wichtige Information, aber keine vollständige Erklärung jedes neuen Problems.

    ## 5. Gemeinsame Gruppenbefunde sind keine Gleichsetzung und kein Biomarker

    Genetische Studien zeigen eine teilweise Überlappung statistischer Einflüsse zwischen ADHS und Autismus. Forschung findet außerdem in beiden Gruppen durchschnittliche Unterschiede in Bereichen wie Aufmerksamkeit, exekutiven Funktionen oder sensorischer Verarbeitung. Diese Befunde sind wissenschaftlich relevant, aber leicht zu überdehnen.

    Eine genetische Korrelation bedeutet nicht, dass dieselben Varianten bei jeder Person vorliegen oder dass beide Diagnosen identische Ursachen haben. Neuropsychologische Gruppenunterschiede besitzen große Überlappungen. Bildgebung und Labortests können derzeit weder ADHS noch Autismus bei einer Einzelperson zuverlässig bestätigen, geschweige denn beide sauber voneinander trennen.

    Eine große, präregistrierte Untersuchung mit mehr als 5.500 Erwachsenen analysierte einzelne autistische und ADHS-bezogene Merkmale als Netzwerke. Die geringe direkte Vernetzung vieler Einzelmerkmale stützte die Trennbarkeit beider Konstrukte. Merkmale der Aufmerksamkeitskontrolle bildeten zwar mögliche Brücken, erklärten die gemeinsame Variation aber nicht vollständig. Das spricht gegen die Behauptung, eine einzige Exekutivfunktion mache beide Diagnosen zu demselben Zustand.

    > [!important] Gruppenbefund ≠ Individualtest
    > Geteilte Gene, Netzwerke oder Testschwierigkeiten können Forschungsmodelle verbessern. Sie liefern derzeit keinen klinischen Biomarker, der bei einer Person „ADHS“, „Autismus“ oder die Koexistenz sicher abliest.

    ## 6. Das gemeinsame Profil kann widersprüchliche Bedürfnisse erzeugen

    Bei koexistierendem ADHS und Autismus addieren sich nicht einfach zwei Checklisten. Merkmale können sich gegenseitig verstärken, verdecken oder scheinbar widersprechen.

    Eine Person kann Neuheit und unmittelbare Rückmeldung benötigen, zugleich aber unerwartete Veränderungen als stark belastend erleben. Sie kann leicht von Reizen abgelenkt werden und gleichzeitig sensorisch überlastet sein. Ein intensiver Fokus kann den Start erleichtern, aber einen Wechsel erschweren. Eine Routine kann Stabilität geben, während die vielen Einzelschritte ihrer Aufrechterhaltung an Planung und Arbeitsgedächtnis scheitern. Soziale Situationen können gleichzeitig durch impulsives Sprechen, vergessene Absprachen, unklare implizite Regeln und Erschöpfung belastet sein.

    Dieses Profil ist nicht unlogisch. Es zeigt, dass „mehr Struktur“ oder „mehr Flexibilität“ ohne genaue Zieldefinition zu grobe Empfehlungen sind. Hilfreich kann eine Struktur sein, die vorhersehbar **und** anpassbar ist: klare Absprachen, sichtbare Übergänge, Vorwarnung bei Änderungen, kurze Handlungsschritte, reizärmere Optionen und ausdrücklich erklärte soziale Erwartungen.

    Zusätzliche Angst, Depression, Schlafprobleme, Lernstörungen, Tic-Störungen oder körperliche Erkrankungen müssen separat berücksichtigt werden. Koexistenz bedeutet nicht, dass jede Schwierigkeit aus ADHS plus Autismus stammt.

    ## 7. Unterstützung behandelt Ziele – nicht Etiketten gegeneinander

    Unterstützung sollte an konkreten Beeinträchtigungen und Präferenzen ausgerichtet sein. Psychoedukation kann erklären, wie beide Merkmalsbereiche zusammenwirken. Umfeldanpassungen können Reizlast, Unklarheit und exekutive Anforderungen reduzieren. Psychologische Interventionen müssen Kommunikationsstil, sensorische Bedürfnisse, Lerntempo und mögliche Schwierigkeiten bei der Übertragung allgemeiner Regeln berücksichtigen.

    Wenn bei einer autistischen Person zusätzlich ADHS diagnostiziert ist, können etablierte ADHS-Medikamente zur Behandlung der ADHS-Kernsymptome erwogen werden. Sie behandeln nicht die autistischen Kernmerkmale. Wirkung und Nebenwirkungen müssen individuell und fachlich überwacht werden; die Evidenz speziell für koexistierende Gruppen ist kleiner und heterogener als die allgemeine ADHS-Evidenz. Eine Autismusdiagnose ist weder pauschaler Ausschlussgrund noch Begründung für eine Medikation ohne ADHS.

    Therapie sollte nicht darauf zielen, eine Person möglichst unauffällig wirken zu lassen. Erlernte soziale Strategien können freiwillig nützlich sein, doch erzwungenes dauerhaftes Masking kann hohe Anstrengung und Selbstentfremdung bedeuten. Gemeinsame Entscheidungsfindung fragt deshalb: Welches Problem soll sich verändern? Welche Anpassung respektiert die Person? Wie wird Nutzen im Alltag gemessen? Welche Belastung entsteht durch die Maßnahme selbst?

    ## 8. Mini-Übung: Beobachtung in Funktion übersetzen

    Wähle eine konkrete Situation, zum Beispiel ein Gruppengespräch, einen Aufgabenwechsel oder eine Planänderung. Notiere ohne diagnostisches Urteil:

    1. Was war sichtbar?
    2. Welche Anforderungen bestanden an Aufmerksamkeit, Impulskontrolle, soziale Interpretation, Reizverarbeitung und Wechsel?
    3. Welche Information war unausgesprochen?
    4. Was machte die Situation vorhersehbarer oder leichter?
    5. Welche alternative Erklärung müsste ebenfalls geprüft werden, etwa Angst, Schlafmangel oder Überforderung?

    Die Übung dient nicht zur Selbstdiagnose. Sie verhindert den Kurzschluss, ein sichtbares Verhalten sofort einem einzigen Etikett zuzuordnen.

    ## 9. Wissenschaftliche Einordnung und Grenzen

    **Konsens:** ADHS und Autismus sind unterscheidbare Neuroentwicklungsstörungen, die gemeinsam diagnostiziert werden können. Eine fachgerechte Beurteilung prüft die Kernkriterien beider Störungen, Entwicklung, mehrere Kontexte, Beeinträchtigung, Komorbiditäten und mögliche Alternativerklärungen.

    **Wahrscheinlich:** Koexistenz erhöht im Mittel die Komplexität von Funktionsproblemen und Unterstützungsbedarf. Gemeinsame genetische sowie kognitive Einflüsse tragen zur Überlappung bei, erklären aber nicht das gesamte gemeinsame Auftreten.

    **Umstritten:** Welche einzelnen kognitiven oder neuronalen Mechanismen die Überlappung am besten erklären und welche Untergruppen langfristig klinisch besonders bedeutsam sind. Ergebnisse hängen stark von Messmethode, Alter, Geschlecht, Sprache, intellektuellen Voraussetzungen und Stichprobenauswahl ab.

    **Experimentell:** Biomarker, digitale Verhaltensdaten und maschinelles Lernen zur individuellen Trennung oder Vorhersage. Diese Verfahren sind derzeit kein Ersatz für klinische Diagnostik.

    ## Review-Frage

    **Warum beweist ein sozial auffälliges oder reizempfindliches Verhalten bei einer Person mit ADHS nicht automatisch zusätzlich Autismus?**

    <details>
    <summary>Antwort</summary>

    Weil dieselbe sichtbare Verhaltensweise unterschiedliche Funktionen und Ursachen haben kann. Eine Autismusdiagnose erfordert ein entwicklungsbezogenes Gesamtmuster ihrer eigenen Kernbereiche, nicht nur einzelne überlappende Merkmale oder einen hohen Screeningwert.

    </details>

    ## Wissenschaftliche Quelle

    [[references/Young2020|Young et al. 2020]] – interdisziplinäres Expert:innen-Konsensuspapier zur Erkennung und Behandlung koexistierender ADHS und Autismus über die Lebensspanne.

    [[references/Micai2023|Micai et al. 2023]] – große systematische Übersicht und Meta-Analyse zu Begleiterkrankungen bei autistischen Kindern und Erwachsenen.

    [[references/Zhong2026|Zhong & Porter 2026]] – systematische Übersicht zu autistischen Symptomen bei Menschen mit primärer ADHS-Diagnose; online erstmals 2024 veröffentlicht.

    [[references/Waldren2024|Waldren et al. 2024]] – große, präregistrierte Erwachsenenstudie zur Überlappung und Trennbarkeit einzelner autistischer und ADHS-bezogener Merkmale.

    [[references/Kofler2024|Kofler et al. 2024]] – aktueller Review zu exekutiven Funktionen bei ADHS und Autismus.

    ## Merksatz

    > ADHS und Autismus können sich überlappen und gemeinsam auftreten – ähnliche Oberfläche ersetzt aber nie die Prüfung der jeweils eigenen Kernmerkmale, Entwicklung und Funktion.

    ## Navigation

    - Zurück: [[02-Vertiefung/01-Pharmakologie-und-Psychotherapie|Pharmakotherapie und Psychotherapie]]
    - Weiter: [[ROADMAP#Milestone A – Klinische Heterogenität und Lebensspanne|Nächste Themen laut Roadmap]]
    - [[Glossar]] · [[Literatur]] · [[knowledge-graph/README|Wissensgraph]]
    ''',
)

write(
    "references/Young2020.md",
    r'''
    ---
    reference_id: Young2020
    title: Young et al. 2020
    evidence_type: expert-consensus
    evidence_grade: moderate
    status: consensus
    doi: "10.1186/s12916-020-01585-y"
    pmid: "32448170"
    last_checked: 2026-07-23
    tags: [Literatur, ADHS, Autismus, Koexistenz, Diagnostik, Behandlung]
    citation:
      entry_type: article
      csl_type: article-journal
      authors:
        - "Young, S."
        - "Hollingdale, J."
        - "Absoud, M."
      et_al: true
      year: 2020
      article_title: "Guidance for identification and treatment of individuals with attention deficit/hyperactivity disorder and autism spectrum disorder based upon expert consensus"
      journal: BMC Medicine
      volume: "18"
      article_number: "146"
    ---

    # Young et al. 2020

    ## Vollständige Zitation

    Young, S., Hollingdale, J., Absoud, M., et al. (2020). Guidance for identification and treatment of individuals with attention deficit/hyperactivity disorder and autism spectrum disorder based upon expert consensus. *BMC Medicine, 18*, 146.

    ## Evidenztyp und Design

    Interdisziplinäres Expert:innen-Konsensuspapier. Fachleute aus ADHS-, Autismus-, Kinder-, Erwachsenen- und multiprofessioneller Versorgung erarbeiteten praktische Empfehlungen zu Erkennung, Diagnostik und Behandlung über die Lebensspanne.

    ## Population

    Die Empfehlungen beziehen sich auf Kinder, Jugendliche und Erwachsene mit möglicher oder diagnostizierter Koexistenz von ADHS und Autismus. Es handelt sich nicht um eine randomisierte Wirksamkeitsstudie.

    ## Kernaussage

    Beide Störungen sollen anhand ihrer jeweils eigenen Kernkriterien, Entwicklungsgeschichte, mehreren Informationsquellen und funktionellen Folgen geprüft werden. Unterstützung und Behandlung werden an konkrete Ziele angepasst; eine Behandlung von ADHS-Kernsymptomen ersetzt keine autismusbezogene Unterstützung und umgekehrt.

    ## Einschränkungen

    Expert:innenkonsens liegt in der Evidenzhierarchie unter systematischen Leitlinienreviews und kann von Zusammensetzung, Erfahrung und Gesundheitsversorgung des Panels beeinflusst sein. Für viele spezifische Kombinationen fehlen direkte Vergleichsstudien.

    ## Verhältnis zum bisherigen Konsens

    Bestätigt die diagnostische Trennbarkeit und anerkannte Koexistenz beider Neuroentwicklungsstörungen und liefert eine praxisorientierte Synthese für die Versorgung.

    ## Links

    - [DOI](https://doi.org/10.1186/s12916-020-01585-y)
    - [PubMed](https://pubmed.ncbi.nlm.nih.gov/32448170/)
    ''',
)

write(
    "references/Micai2023.md",
    r'''
    ---
    reference_id: Micai2023
    title: Micai et al. 2023
    evidence_type: systematic-review-and-meta-analysis
    evidence_grade: high
    status: consensus
    doi: "10.1016/j.neubiorev.2023.105436"
    pmid: "37913872"
    last_checked: 2026-07-23
    tags: [Literatur, Autismus, ADHS, Koexistenz, Prävalenz, Komorbidität]
    citation:
      entry_type: article
      csl_type: article-journal
      authors:
        - "Micai, M."
        - "Fatta, L. M."
        - "Gila, L."
      et_al: true
      year: 2023
      article_title: "Prevalence of co-occurring conditions in children and adults with autism spectrum disorder: A systematic review and meta-analysis"
      journal: Neuroscience & Biobehavioral Reviews
      volume: "155"
      article_number: "105436"
    ---

    # Micai et al. 2023

    ## Vollständige Zitation

    Micai, M., Fatta, L. M., Gila, L., et al. (2023). Prevalence of co-occurring conditions in children and adults with autism spectrum disorder: A systematic review and meta-analysis. *Neuroscience & Biobehavioral Reviews, 155*, 105436.

    ## Evidenztyp und Design

    Präregistrierte systematische Übersicht und Random-Effects-Meta-Analyse. Aus 19.932 Treffern wurden 340 Publikationen mit insgesamt ungefähr 590.000 Teilnehmenden eingeschlossen; untersucht wurden zahlreiche psychische, entwicklungsbezogene und körperliche Begleitbedingungen.

    ## Population

    Autistische Kinder, Jugendliche und Erwachsene aus populations-, register- und klinikbezogenen Stichproben. Subgruppenanalysen berücksichtigten Alter und Studiendesign.

    ## Kernaussage

    ADHS gehört zu den häufigen koexistierenden Bedingungen bei Autismus. Prävalenzschätzungen variieren deutlich nach Alter, Stichprobenquelle, Definition und Erhebungsmethode und dürfen nicht als Wahrscheinlichkeit für eine einzelne Person interpretiert werden.

    ## Einschränkungen

    Die eingeschlossenen Studien unterschieden sich stark bei Diagnostik, Repräsentativität, Alter, intellektuellen Voraussetzungen und Definition von Punkt- beziehungsweise Lebenszeitprävalenz. Meta-analytische Mittelwerte lösen diese Heterogenität nicht auf.

    ## Verhältnis zum bisherigen Konsens

    Bestätigt die klinische Bedeutung systematischer Komorbiditätsprüfung und präzisiert, dass Häufigkeit und Versorgung je nach Population deutlich variieren.

    ## Links

    - [DOI](https://doi.org/10.1016/j.neubiorev.2023.105436)
    - [PubMed](https://pubmed.ncbi.nlm.nih.gov/37913872/)
    ''',
)

write(
    "references/Zhong2026.md",
    r'''
    ---
    reference_id: Zhong2026
    title: Zhong & Porter 2026
    evidence_type: systematic-review
    evidence_grade: moderate
    status: probable
    doi: "10.1007/s40489-024-00443-4"
    pmid: ""
    last_checked: 2026-07-23
    tags: [Literatur, ADHS, Autismus, Screening, Differentialdiagnostik]
    citation:
      entry_type: article
      csl_type: article-journal
      authors:
        - "Zhong, Q."
        - "Porter, M."
      et_al: false
      year: 2026
      article_title: "Autism Spectrum Disorder Symptoms in Individuals with a Primary Diagnosis of Attention-Deficit/Hyperactivity Disorder: A Systematic Review"
      journal: Review Journal of Autism and Developmental Disorders
      volume: "13"
      pages: "424–441"
    ---

    # Zhong & Porter 2026

    ## Vollständige Zitation

    Zhong, Q. & Porter, M. (2026). Autism Spectrum Disorder Symptoms in Individuals with a Primary Diagnosis of Attention-Deficit/Hyperactivity Disorder: A Systematic Review. *Review Journal of Autism and Developmental Disorders, 13*, 424–441.

    ## Evidenztyp und Design

    Systematische Übersicht von neun Studien mit insgesamt 548 Personen mit primärer ADHS-Diagnose. Die Arbeit wurde 2024 online erstveröffentlicht und erschien im Jahrgang 2026.

    ## Population

    Kinder, Jugendliche und Erwachsene mit primärer ADHS-Diagnose aus Studien, die autistische Symptome oder klinische Schwellen mit unterschiedlichen Instrumenten untersuchten.

    ## Kernaussage

    Erhöhte autistische Merkmale werden in ADHS-Stichproben berichtet, doch die Schätzungen schwanken stark. Häufig verwendete Screeningverfahren und heterogene Designs erlauben keine Gleichsetzung auffälliger Werte mit einer gesicherten Autismusdiagnose.

    ## Einschränkungen

    Nur wenige, methodisch unterschiedliche Studien waren einschließbar. Stichprobengrößen, Altersgruppen, Instrumente und diagnostische Absicherung variierten; viele Ergebnisse beruhen auf Fragebögen statt vollständiger klinischer Diagnostik.

    ## Verhältnis zum bisherigen Konsens

    Bestätigt einen relevanten Abklärungsbedarf bei manchen Menschen mit ADHS, warnt aber vor der diagnostischen Überinterpretation einzelner überlappender Symptome oder Screeningwerte.

    ## Links

    - [DOI](https://doi.org/10.1007/s40489-024-00443-4)
    ''',
)

write(
    "references/Waldren2024.md",
    r'''
    ---
    reference_id: Waldren2024
    title: Waldren et al. 2024
    evidence_type: preregistered-multi-method-study
    evidence_grade: moderate
    status: probable
    doi: "10.1016/j.cortex.2023.12.016"
    pmid: "38387375"
    last_checked: 2026-07-23
    tags: [Literatur, ADHS, Autismus, Erwachsene, Netzwerk-Analyse, Aufmerksamkeit]
    citation:
      entry_type: article
      csl_type: article-journal
      authors:
        - "Waldren, L. H."
        - "Leung, F. Y. N."
        - "Hargitai, L. D."
        - "Burgoyne, A. P."
        - "Liceralde, V. R. T."
        - "Livingston, L. A."
        - "Shah, P."
      et_al: false
      year: 2024
      article_title: "Unpacking the overlap between Autism and ADHD in adults: A multi-method approach"
      journal: Cortex
      volume: "173"
      pages: "120–137"
    ---

    # Waldren et al. 2024

    ## Vollständige Zitation

    Waldren, L. H., Leung, F. Y. N., Hargitai, L. D., Burgoyne, A. P., Liceralde, V. R. T., Livingston, L. A., & Shah, P. (2024). Unpacking the overlap between Autism and ADHD in adults: A multi-method approach. *Cortex, 173*, 120–137.

    ## Evidenztyp und Design

    Mehrteilige Untersuchung mit offenen Daten: eine bevölkerungsnahe britische Stichprobe von 504 Erwachsenen, eine große präregistrierte Merkmalsstudie mit 5.000 Erwachsenen und eine weitere präregistrierte kognitive Studie mit 500 Teilnehmenden.

    ## Population

    Erwachsene aus der Allgemeinbevölkerung mit dimensional erfassten autistischen und ADHS-bezogenen Merkmalen; die Ergebnisse sind keine direkte klinische Diagnosestudie ausschließlich diagnostizierter Gruppen.

    ## Kernaussage

    Viele Einzelmerkmale beider Bereiche waren nur schwach direkt verbunden, was ihre Trennbarkeit unterstützt. Merkmale der Aufmerksamkeitskontrolle bildeten mögliche Brücken, erklärten die gemeinsame Variation zwischen autistischen und ADHS-bezogenen Merkmalen jedoch nicht vollständig.

    ## Einschränkungen

    Der Hauptteil beruhte auf Selbstberichten und dimensionalen Merkmalen. Netzwerkmodelle zeigen statistische Verbindungen, aber keine Kausalität. Ergebnisse aus Erwachsenen der Allgemeinbevölkerung lassen sich nicht ohne Weiteres auf alle klinischen, sprachlichen oder intellektuellen Profile übertragen.

    ## Verhältnis zum bisherigen Konsens

    Präzisiert die Überlappungsdebatte: gemeinsame transdiagnostische Prozesse sind plausibel, reichen aber nicht aus, ADHS und Autismus als ein einziges Konstrukt zu behandeln.

    ## Links

    - [DOI](https://doi.org/10.1016/j.cortex.2023.12.016)
    - [PubMed](https://pubmed.ncbi.nlm.nih.gov/38387375/)
    ''',
)

# README and index.
readme = ROOT / "README.md"
readme_text = readme.read_text(encoding="utf-8")
readme_text = re.sub(r"(?m)^version: .*?$", "version: 0.15.0", readme_text, count=1)
readme_text = re.sub(r"(?m)^last_reviewed: .*?$", "last_reviewed: 2026-07-23", readme_text, count=1)
item13 = "13. [[02-Vertiefung/01-Pharmakologie-und-Psychotherapie|Pharmakotherapie und Psychotherapie]]\n"
item14 = item13 + "14. [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung|Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung]]\n"
if "14. [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung" not in readme_text:
    if item13 not in readme_text:
        raise RuntimeError("README-Lernpfadanker fehlt")
    readme_text = readme_text.replace(item13, item14, 1)
readme.write_text(readme_text, encoding="utf-8")

index_path = ROOT / "index.json"
index = json.loads(index_path.read_text(encoding="utf-8"))
index["version"] = "0.15.0"
index["last_reviewed"] = "2026-07-23"
if not any(item.get("number") == 14 for item in index["chapters"]):
    index["chapters"].append({
        "number": 14,
        "path": unit_path,
        "title": "Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung",
    })
index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# MkDocs navigation.
replace_once(
    "mkdocs.yml",
    "      - Pharmakologie und Psychotherapie: 02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md\n",
    "      - Pharmakologie und Psychotherapie: 02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md\n"
    "      - Autismus und ADHS: 02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung.md\n",
)

# Previous navigation.
replace_once(
    "02-Vertiefung/01-Pharmakologie-und-Psychotherapie.md",
    "- Weiter: [[README|Übersicht]]\n",
    "- Weiter: [[02-Vertiefung/02-Autismus-und-ADHS-Ueberlappung|Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung]]\n",
)

# Glossary additions at alphabetically useful anchors.
replace_once(
    "Glossar.md",
    "## Delay Discounting\n",
    "## Camouflaging / Masking\nStrategien, mit denen eine Person sichtbare autistische oder andere neurodivergente Merkmale bewusst oder unbewusst verdeckt, kompensiert oder an erwartete soziale Regeln anpasst; kein eigenständiger Diagnosenachweis und potenziell mit erheblicher Anstrengung verbunden.\n\n## Delay Discounting\n",
)
replace_once(
    "Glossar.md",
    "## Neuroentwicklung\n",
    "## Koexistenz\nGleichzeitiges Vorliegen diagnostisch unterscheidbarer Bedingungen, beispielsweise ADHS und Autismus; bedeutet weder Gleichheit noch eine bloße Unterform der jeweils anderen Diagnose.\n\n## Neuroentwicklung\n",
)
replace_once(
    "Glossar.md",
    "## Reaktionszeitvariabilität\n",
    "## Restriktive oder repetitive Verhaltensweisen\nAutistische Kernmerkmalsgruppe mit wiederholten Bewegungen oder Sprache, starkem Bedürfnis nach Gleichförmigkeit, fokussierten Interessen oder sensorischen Besonderheiten; einzelne Routinen oder Interessen reichen allein nicht für eine Diagnose.\n\n## Reaktionszeitvariabilität\n",
)
replace_once(
    "Glossar.md",
    "## Shared Decision Making\n",
    "## Sensorische Verarbeitung\nAufnahme, Gewichtung und Integration von Sinnesreizen; Über- oder Unterempfindlichkeiten können bei Autismus, ADHS und weiteren Bedingungen vorkommen und sind für sich allein nicht diagnostisch spezifisch.\n\n## Shared Decision Making\n",
)
replace_once(
    "Glossar.md",
    "## Suizidalität\n",
    "## Soziale Kommunikation\nWechselseitiger Gebrauch verbaler und nonverbaler Signale, sozialer Gegenseitigkeit und kontextangemessener Verständigung; bei der Autismusdiagnostik wird ein entwicklungsbezogenes Gesamtmuster geprüft, nicht ein einzelner sozialer Fehler.\n\n## Suizidalität\n",
)

# Anki card.
cards = ROOT / "cards" / "cards.yaml"
cards_text = cards.read_text(encoding="utf-8")
if "id: 1014" not in cards_text:
    cards_text = cards_text.rstrip() + "\n" + textwrap.dedent(r'''
    - id: 1014
      unit: 14
      front: Warum bedeutet die sichtbare Überlappung von ADHS und Autismus nicht, dass beide dieselbe Störung sind?
      back: Weil ähnliche Verhaltensweisen unterschiedliche Funktionen und Entwicklungswege haben können; für jede Diagnose müssen ihre eigenen Kernmerkmale, Entwicklung, Kontexte und Beeinträchtigungen geprüft werden.
      tags:
      - ADHS
      - Autismus
      - Vertiefung
      - Differentialdiagnostik
      - Einheit_14
    ''').lstrip()
cards.write_text(cards_text, encoding="utf-8")

# Planned node is now materialised.
planned_path = ROOT / "knowledge-graph" / "planned-nodes.yaml"
planned = yaml.safe_load(planned_path.read_text(encoding="utf-8"))
planned["nodes"] = [
    item for item in planned.get("nodes", [])
    if item.get("path") != "02-Vertiefung/02-Autismus-ADHS-Ueberlappung"
]
planned_path.write_text(yaml.safe_dump(planned, allow_unicode=True, sort_keys=False), encoding="utf-8")

# Roadmap status and current count.
roadmap = ROOT / "ROADMAP.md"
roadmap_text = roadmap.read_text(encoding="utf-8")
roadmap_text = roadmap_text.replace("Der Lernpfad umfasst derzeit 13 fortlaufende Einheiten:", "Der Lernpfad umfasst derzeit 14 fortlaufende Einheiten:", 1)
if "14. Autismus und ADHS: Koexistenz" not in roadmap_text:
    roadmap_text = roadmap_text.replace(
        "13. Pharmakotherapie und Psychotherapie\n",
        "13. Pharmakotherapie und Psychotherapie\n14. Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung\n",
        1,
    )
roadmap_text = roadmap_text.replace("- [ ] Autismus/ADHS-Überlappung", "- [x] Autismus/ADHS-Überlappung", 1)
roadmap_text = roadmap_text.replace("## Nächste verbindliche Einheit", "## Umgesetzte Priorität A1", 1)
roadmap_text = roadmap_text.replace(
    "- [ ] **A1 · Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung** — **P0; nächste reguläre Einheit 14**",
    "- [x] **A1 · Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung** — **P0; umgesetzt als Einheit 14**",
    1,
)
roadmap.write_text(roadmap_text, encoding="utf-8")

# Changelog.
changelog = ROOT / "CHANGELOG.md"
change_text = changelog.read_text(encoding="utf-8")
entry = textwrap.dedent('''
## 0.15.0 – 2026-07-23

- Einheit 14 „Autismus und ADHS: Koexistenz, Überlappung und Abgrenzung“ ergänzt
- diagnostische Kernbereiche, Symptomüberlappung, Masking, diagnostisches Überschatten und gemeinsame Funktionsprofile differenziert eingeordnet
- vier aktuelle Konsens-, Review- und Primärstudienkarten sowie Glossarbegriffe und Anki-Karte ergänzt
- Roadmap und Planned-Node-Registry auf den abgeschlossenen Themenblock aktualisiert

''')
if "## 0.15.0 – 2026-07-23" not in change_text:
    change_text = change_text.replace("# Änderungsverlauf\n\n", "# Änderungsverlauf\n\n" + entry, 1)
changelog.write_text(change_text, encoding="utf-8")

# Verify target prose count before running the project validators.
def prose_word_count(text: str) -> int:
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"</?(?:details|summary)>", "", text)
    text = re.sub(r"## Navigation.*\Z", "", text, flags=re.S)
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), text)
    return len(re.findall(r"\b[\wÄÖÜäöüß]+(?:[-’'][\wÄÖÜäöüß]+)*\b", text))

word_count = prose_word_count((ROOT / unit_path).read_text(encoding="utf-8"))
print(f"Einheit 14: {word_count} Fließtextwörter")
if not 1200 <= word_count <= 2500:
    raise RuntimeError(f"Einheit 14 liegt mit {word_count} Wörtern außerhalb des Zielbereichs 1.200–2.500")

# The transport must never enter the final content commit.
shutil.rmtree(BOOTSTRAP)
WORKFLOW.unlink(missing_ok=True)

# Project-required checks. Generated bibliography is staged once, then rebuilt to verify determinism.
run("python", "-m", "pip", "check")
run("git", "diff", "--check")
run("python", "-m", "compileall", "-q", "scripts")
run("python", "scripts/build_literature.py")
run("git", "add", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/build_literature.py")
run("git", "diff", "--exit-code", "--", "Literatur.md", "references.bib", "references.json")
run("python", "scripts/validate_links.py")
run("python", "scripts/build_graph.py")
if (ROOT / "scripts" / "validate_graph.py").is_file():
    run("python", "scripts/validate_graph.py")
run("python", "scripts/validate_compendium.py")
run("python", "scripts/build_combined.py")
run("python", "scripts/build_anki.py")
run("python", "scripts/build_docs.py")
run("mkdocs", "build", "--strict")
if (ROOT / "tests").is_dir():
    run("python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
run("git", "diff", "--check")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
    raise RuntimeError("Keine Änderungen für Einheit 14 vorhanden")
run("git", "commit", "-m", "Einheit 14: Autismus und ADHS – Koexistenz und Abgrenzung")
run("git", "push", "origin", f"HEAD:{BRANCH}")
print(f"Einheit 14 erfolgreich erstellt und gepusht: {word_count} Wörter")
