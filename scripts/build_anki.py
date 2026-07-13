#!/usr/bin/env python3
from pathlib import Path
import yaml, genanki
R=Path(__file__).resolve().parents[1]; data=yaml.safe_load((R/'cards/cards.yaml').read_text(encoding='utf-8'))
model=genanki.Model(1761321701,'ADHS Lernpfad Basis',fields=[{'name':'Frage'},{'name':'Antwort'},{'name':'Einheit'}],templates=[{'name':'Karte','qfmt':'<div class="unit">Einheit {{Einheit}}</div><h2>{{Frage}}</h2>','afmt':'{{FrontSide}}<hr><div>{{Antwort}}</div>'}],css='.card{font-family:sans-serif;font-size:20px;text-align:left;line-height:1.45}.unit{font-size:14px;opacity:.7}')
deck=genanki.Deck(2059400110,data['deck'])
for c in data['cards']:
    n=genanki.Note(model=model,fields=[c['front'],c['back'],str(c['unit'])],tags=c.get('tags',[]),guid=genanki.guid_for(str(c['id'])))
    deck.add_note(n)
out=R/'build'; out.mkdir(exist_ok=True); genanki.Package(deck).write_to_file(out/'ADHS-Lernpfad.apkg')
print(f"Anki: {len(data['cards'])} Karten")
