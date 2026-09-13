# Sue

A small experimental **generative personality engine** for the terminal.

Not a person. Not an LLM. Not a dialogue tree.

```bash
python3 sue.py
```

Requires Python 3.10+ and the standard library only.

## What she is

Sue is a pipeline:

```
user input
    -> parse (features, content words)
    -> memory retrieve (relevance, not full dump)
    -> internal state (floats + 12-d hidden vector)
    -> candidate thoughts (structured, not sentences)
    -> evaluation against personality parameters
    -> softmax sample a winner
    -> compositional realization
    -> update state + memory
```

Personality is parameters and lexical parts. Responses are assembled.
There is no `if user says X: return Y` path that chooses the spoken line.

## Commands

- `/state` public state summary
- `/memory` recent traces
- `/forget` wipe traces, name, goals
- `/reset` new session; keep long-term memory
- `/summary` toggle the short thought tag
- `/help` rails
- `/quit` save and exit

Commands are plumbing. They are not her personality.

## Tests

```bash
python3 tests/test_sue.py
```

## Limitations

No large language model. Vocabulary is banks + user tokens + stored traces.
English-only shallow parse. She is not conscious or sentient.

## Files

- `sue.py` launcher
- `sue/` package
- `tests/test_sue.py`
