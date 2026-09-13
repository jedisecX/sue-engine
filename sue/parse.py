"""Shallow parse. Features, not meaning."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .memory import tokenize

HOSTILE = frozenset("hate stupid dumb suck worthless shut idiot trash shutup".split())
WARM = frozenset("love like thanks thank glad happy nice good miss welcome".split())
CLAIM = frozenset("always never everyone nobody must should definitely obviously true false".split())
SELF = frozenset("i im i'm me my mine".split())
OTHER = frozenset("you your you're youre sue".split())


@dataclass
class Parsed:
    raw: str
    tokens: list[str]
    content: list[str]
    question: bool
    negation: bool
    unusual: bool
    features: dict[str, float] = field(default_factory=dict)
    topic_hint: str = ""


def parse(text: str, stop: frozenset[str], last_tokens: list[str] | None = None) -> Parsed:
    raw = text.strip()
    tokens = tokenize(raw)
    content = [t for t in tokens if t not in stop and t not in {"sue"}]
    qmark = "?" in raw
    wh = bool(tokens and tokens[0] in {"what", "why", "how", "who", "where", "when", "which"})
    question = qmark or wh
    negation = any(t in {"not", "no", "never", "dont", "don't", "cant", "can't"} for t in tokens)
    unusual = (
        len(raw) > 280
        or bool(re.search(r"[^\w\s?.,!'\"-]", raw))
        or len(set(tokens)) <= 2 and len(tokens) >= 8
        or (len(tokens) == 1 and tokens[0] not in stop)
    )
    affiliation = 1.0 if (WARM & set(tokens)) else 0.0
    hostility = 1.0 if (HOSTILE & set(tokens)) else 0.0
    claim = 1.0 if (CLAIM & set(tokens) or (not question and len(content) >= 3)) else 0.0
    if last_tokens:
        same = last_tokens == tokens
        repeat = 1.0 if same else 0.0
    else:
        repeat = 0.0
    length = min(len(tokens) / 40.0, 1.0)
    topic_hint = content[0] if content else (tokens[0] if tokens else "")
    if len(content) >= 2:
        topic_hint = sorted(content, key=len, reverse=True)[0]
    news_ask = 1.0 if (
        set(tokens) & {"news", "feed", "feeds", "headline", "headlines", "wire", "rss", "ingest"}
        or any(w in raw.lower() for w in ("what's on the wire", "what is on the wire", "any news", "recall the"))
    ) else 0.0
    features = {
        "question": 1.0 if question else 0.0,
        "negation": 1.0 if negation else 0.0,
        "unusual": 1.0 if unusual else 0.0,
        "affiliation": affiliation,
        "hostility": hostility,
        "claim": claim,
        "repeat": repeat,
        "length": length,
        "self": 1.0 if (SELF & set(tokens)) else 0.0,
        "other": 1.0 if (OTHER & set(tokens)) else 0.0,
        "empty": 1.0 if not tokens else 0.0,
        "news_ask": news_ask,
    }
    return Parsed(
        raw=raw, tokens=tokens, content=content, question=question,
        negation=negation, unusual=unusual, features=features, topic_hint=topic_hint,
    )
