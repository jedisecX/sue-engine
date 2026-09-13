# Sue

A small experimental **generative personality engine** for the terminal.

Not a person. Not an LLM. Not a dialogue tree.

```bash
python3 sue.py
```

Python 3.10+, standard library only.

## Commands

On wake: `/help  /lexicon  /news  /lib`

| command | effect |
|---|---|
| `/state` | public state summary |
| `/memory` | recent traces |
| `/forget` | wipe traces, name, goals, and the wire |
| `/forget news` | drop only news traces and the wire |
| `/feeds` | list RSS sources from `feeds.json` |
| `/ingest` | pull feeds into memory and teach the lexicon |
| `/news` | stored feed traces |
| `/lexicon` | dictionary menu + bank size |
| `/lexicon [word]` | class, gloss, neighbors |
| `/define [word]` | gloss only |
| `/lexicon chat` | words from this talk |
| `/lib [module]` | stdlib coding library |
| `/script save [name.py]` | write last composed script |
| `/reset` | new session; keep long-term memory **and** the wire |
| `/summary` | toggle the short thought tag |
| `/help` | rails |
| `/quit` | save and exit |

## Pipeline

parse → retrieve → state → candidate thoughts → evaluate → softmax → realize → update

Intents: reflect, observe, question, connect, disagree, admit, play, recall, code.

## Pieces

- `sue/engine.py` — facade
- `sue/lexicon.py` + `sue/dictionary.py` — word bank and glosses
- `sue/ingest.py` — RSS, offline-first, teaches lexicon
- `sue/coder.py` — stdlib script composer
- `sue/ui.py` — terminal menu

```bash
python3 -m unittest discover -s tests
```

v2.1.0: reset keeps the news wire; full forget clears it; scripts are not stored whole in memory; lexicon lookup uses `related()` instead of copying the 5k graph each turn.
