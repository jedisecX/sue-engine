# Sue

A small experimental generative personality engine for the terminal.

Not a person. Not an LLM. Not a dialogue tree.

```bash
python3 sue.py
```

Python 3.10+, standard library only.

## Interface

On wake: `/help  /lexicon  /news  /lib`

```
/lexicon              dictionary menu + bank size
/lexicon [word]       class, gloss, neighbors
/define [word]        gloss only
/lexicon chat         words from this talk
/news                 stored feed traces
/ingest               pull feeds.json into memory and teach the lexicon
/lib [module]         stdlib coding library
/script save name.py  write last composed script
```

Ask in sentences. Commands are plumbing.

## Pieces

- `sue/engine.py` — parse → reason → realize → memory
- `sue/lexicon.py` + `sue/data/wordbank5000.txt` — 5k-word bank
- `sue/dictionary.py` — glosses (core / composed / learned from feeds)
- `sue/ingest.py` — RSS, offline-first, teaches lexicon
- `sue/coder.py` — stdlib script composer
- `sue/ui.py` — terminal menu

```bash
python3 -m unittest tests.test_sue tests.test_rss_learn tests.test_coder
```
