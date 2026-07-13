# Anki-Karten

`cards/cards.yaml` ist die editierbare Quelle. `scripts/build_anki.py` erzeugt daraus `build/ADHS-Lernpfad.apkg`.

```bash
python3 -m pip install -r requirements-export.txt
python3 scripts/build_anki.py
```

Die Karten sind bewusst knapp. Sie ersetzen nicht die Kapitel, sondern unterstützen aktives Abrufen und verteiltes Wiederholen.
