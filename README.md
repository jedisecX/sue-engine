# Sue

A small experimental **generative personality engine** for the terminal.

Not a person. Not an LLM. Not a dialogue tree.

```bash
python3 sue.py
```

Requires Python 3.10+ and the standard library only.

## Commands

- `/state` `/memory` `/reset` `/summary` `/help` `/quit`
- `/forget` wipe traces; `/forget news` drop only news
- `/feeds` list RSS sources from `feeds.json`
- `/ingest` pull feeds into `kind=news` memory traces

## RSS (optional, offline-safe)

```bash
cp feeds.example.json feeds.json
```

`sue/ingest.py` uses stdlib urllib + xml. Fetch is not called from `respond()`.
Tests use `tests/fixtures/sample_rss.xml` and never touch the network.

```bash
python3 tests/test_sue.py tests/test_ingest.py
```

## Files

- `sue.py` launcher
- `sue/` package including `ingest.py`
- `feeds.example.json`
- `tests/`
