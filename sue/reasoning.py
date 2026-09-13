"""Candidate thoughts and evaluation. No surface text here."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .memory import Memory, Trace
from .parse import Parsed
from .personality import Personality
from .state import Goal, State

INTENTS = ("reflect", "question", "connect", "disagree", "admit", "play", "observe", "recall")


@dataclass
class Thought:
    intent: str
    topic: str
    stance: float
    memories: list[Trace] = field(default_factory=list)
    hook: bool = False
    materials: list[str] = field(default_factory=list)
    why: str = ""
    score: float = 0.0


def _softmax_pick(rng: random.Random, thoughts: list[Thought], temp: float) -> Thought:
    if not thoughts:
        return Thought(intent="observe", topic="", stance=0.0, why="empty")
    t = max(0.15, temp)
    mx = max(th.score for th in thoughts)
    weights = [math.exp((th.score - mx) / t) for th in thoughts]
    total = sum(weights) or 1.0
    pick = rng.random() * total
    acc = 0.0
    for th, w in zip(thoughts, weights):
        acc += w
        if pick <= acc:
            return th
    return thoughts[-1]


class Reasoner:
    def __init__(self, personality: Personality, rng: random.Random):
        self.p = personality
        self.rng = rng

    def consider(self, parsed: Parsed, state: State, memory: Memory) -> tuple[list[Thought], Thought]:
        query = parsed.content or parsed.tokens
        retrieved = memory.retrieve(query, k=4)
        news_hits = memory.retrieve(query or ["news", "wire"], k=3, kinds={"news"})
        seen_ids = {t.id for t in retrieved}
        for tr in news_hits:
            if tr.id not in seen_ids:
                retrieved.append(tr)
                seen_ids.add(tr.id)
        cands = self._spawn(parsed, state, retrieved)
        for th in cands:
            th.score = self._evaluate(th, parsed, state)
        temp = self.p.temp_min + (self.p.temp_max - self.p.temp_min) * (
            0.4 * state.play + 0.3 * state.energy + 0.3 * (1.0 - state.confidence)
        )
        if parsed.features.get("repeat"):
            temp += 0.25
        winner = _softmax_pick(self.rng, cands, temp)
        return cands, winner

    def _spawn(self, parsed: Parsed, state: State, retrieved: list[Trace]) -> list[Thought]:
        weak = {"why", "how", "what", "who", "when", "where"}
        hint = parsed.topic_hint
        topic = state.topic if hint in weak and state.topic else (hint or state.topic or "this")
        mats_user = list(parsed.content[:6])
        mats_mem = [t.text for t in retrieved[:3]]
        assoc = []
        for w in mats_user[:4]:
            hits = self.p.associates.get(w)
            if hits:
                assoc.append(self.rng.choice(hits))
        thoughts: list[Thought] = []
        thoughts.append(Thought("reflect", topic, stance=0.2, memories=retrieved[:2], materials=mats_user + assoc, why="stay with what was said"))
        thoughts.append(Thought("observe", topic, stance=0.0, memories=retrieved[:1], materials=mats_user + list(self.p.nouns_meta), why="name a quality of the input"))
        thoughts.append(Thought("question", topic, stance=0.1, memories=retrieved[:1], materials=mats_user, hook=True, why="open a gap"))
        if retrieved:
            thoughts.append(Thought("connect", topic, stance=0.3, memories=retrieved[:3], materials=mats_user + mats_mem, why="tie to a stored trace"))
        news_mem = [t for t in retrieved if t.kind == "news"]
        if news_mem or (parsed.features.get("news_ask") and (state.wire or news_mem)):
            thoughts.append(Thought("recall", topic, stance=0.2, memories=news_mem[:3] or retrieved[:2], materials=mats_user + list(state.wire[-4:]), why="pull a stored feed line"))
        if parsed.features.get("claim") or state.contrarian > 0.45:
            thoughts.append(Thought("disagree", topic, stance=-0.6, memories=retrieved[:1], materials=mats_user, why="pressure a tidy claim"))
        thoughts.append(Thought("admit", topic, stance=0.0, memories=[], materials=mats_user, why="mark the limit of local knowledge"))
        thoughts.append(Thought("play", topic, stance=0.1, memories=retrieved[:1], materials=mats_user + assoc + list(self.p.nouns_meta), why="cross two unlike pieces"))
        if state.unresolved:
            thoughts.append(Thought("question", state.unresolved[-1], stance=0.0, materials=[state.unresolved[-1]] + mats_user[:2], hook=True, why="reopen an unfinished thread"))
        if parsed.features.get("empty"):
            thoughts = [
                Thought("observe", "silence", 0.0, materials=["silence", "gap"], why="empty input"),
                Thought("question", "silence", 0.0, materials=["silence"], hook=True, why="empty input"),
                Thought("play", "silence", 0.0, materials=["silence", "cursor"], why="empty input"),
            ]
        if parsed.features.get("repeat"):
            thoughts.append(Thought("play", topic, stance=0.0, materials=mats_user + ["again", "loop"], why="same words twice"))
        if state.curiosity > 0.4 and state.goals:
            g = max(state.goals, key=lambda x: x.urgency)
            thoughts.append(Thought("question", g.text, stance=0.0, hook=True, materials=[g.text] + mats_user[:2], why="internal goal"))
        return thoughts

    def _evaluate(self, th: Thought, parsed: Parsed, state: State) -> float:
        s = 0.15
        aff = {
            "reflect": 0.4 + 0.3 * state.warmth + 0.2 * state.confidence,
            "observe": 0.35 + 0.3 * (1 - state.play) + 0.2 * state.confidence,
            "question": 0.2 + 0.7 * state.curiosity + 0.2 * parsed.features.get("question", 0),
            "connect": 0.2 + 0.4 * state.confidence + (0.35 if th.memories else -0.2),
            "disagree": 0.1 + 0.7 * state.contrarian + 0.2 * parsed.features.get("claim", 0) - 0.3 * parsed.features.get("affiliation", 0),
            "admit": 0.15 + 0.5 * (1 - state.confidence) + 0.2 * parsed.features.get("unusual", 0),
            "play": 0.15 + 0.7 * state.play + 0.2 * parsed.features.get("unusual", 0),
            "recall": 0.15 + (0.55 if th.memories else 0.0) + 0.55 * parsed.features.get("news_ask", 0),
        }
        s += aff.get(th.intent, 0.2)
        if parsed.features.get("hostility") and th.intent in {"play", "disagree"}:
            s += 0.15
        if parsed.features.get("hostility") and th.intent == "reflect":
            s -= 0.1
        if parsed.features.get("empty") and th.intent == "observe":
            s += 0.2
        if parsed.question and th.intent == "admit":
            s += 0.12
        if parsed.question and th.intent == "disagree":
            s -= 0.15
        if state.last_intent and th.intent == state.last_intent:
            s -= 0.22
        if th.hook:
            s += 0.08 * state.curiosity
        if parsed.features.get("repeat") and th.intent == "play":
            s += 0.25
        if th.intent == "recall" and any(m.kind == "news" for m in th.memories):
            s += 0.28
        if th.intent == "recall" and state.wire and parsed.features.get("news_ask"):
            s += 0.35
        s += self.rng.uniform(-0.04, 0.04)
        return s

    def maybe_new_goal(self, parsed: Parsed, state: State) -> Goal | None:
        if not parsed.content:
            return None
        if self.rng.random() > 0.22 * state.curiosity:
            return None
        seed = parsed.topic_hint
        templates = (f"understand {seed}", f"find what {seed} sits next to", f"test whether {seed} repeats")
        text = templates[self.rng.randrange(len(templates))]
        if any(g.text == text for g in state.goals):
            return None
        return Goal(text=text, urgency=0.3 + 0.3 * state.curiosity, origin="curiosity")
