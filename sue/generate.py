"""Compose surface text from a thought + state + parse + memories."""

from __future__ import annotations

import random
import re
from typing import Protocol

from .memory import Trace
from .parse import Parsed
from .personality import Personality
from .reasoning import Thought
from .state import State


class Realizer(Protocol):
    def realize(self, thought: Thought, parsed: Parsed, state: State) -> str: ...
    def thought_summary(self, thought: Thought) -> str: ...


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.!?])", r"\1", s)
    if s and s[-1] not in ".!?":
        s += "."
    if s:
        s = s[0].upper() + s[1:]
    return s


def _clip_words(text: str, n: int = 10) -> str:
    words = text.split()
    if len(words) <= n:
        return text.strip().rstrip(".")
    return " ".join(words[:n]).rstrip(".,") + "…"


class ComposeRealizer:
    def __init__(self, personality: Personality, rng: random.Random):
        self.p = personality
        self.rng = rng

    def thought_summary(self, thought: Thought) -> str:
        bits = [thought.intent]
        if thought.topic:
            bits.append(thought.topic[:28])
        if thought.hook:
            bits.append("hook")
        if thought.memories:
            bits.append(f"mem:{thought.memories[0].id}")
        return " · ".join(bits)

    def realize(self, thought: Thought, parsed: Parsed, state: State) -> str:
        sentences = [s for s in self._core_sentences(thought, parsed, state) if s]
        if thought.memories and thought.intent in {"connect", "reflect", "play"}:
            hinge = self._memory_hinge(thought.memories[0], state)
            if hinge:
                sentences.append(hinge)
        if thought.hook or self._want_hook(thought, state):
            hook = self._hook(thought, parsed, state)
            if hook:
                sentences.append(hook)
        text = " ".join(_clean(s) for s in sentences if s)
        return text or "I am still turning that over."

    def _want_hook(self, thought: Thought, state: State) -> bool:
        if thought.intent == "question":
            return True
        p = self.p.curiosity_base * (0.4 + 0.6 * state.curiosity)
        if state.last_intent == "question":
            p *= 0.35
        return self.rng.random() < p

    def _pick(self, seq) -> str:
        return seq[self.rng.randrange(len(seq))]

    def _topic(self, thought: Thought, parsed: Parsed) -> str:
        if thought.topic and thought.topic not in {"this", "silence"}:
            return thought.topic
        if parsed.content:
            return parsed.content[self.rng.randrange(len(parsed.content))]
        return "that"

    def _assoc(self, word: str) -> str:
        hits = self.p.associates.get(word)
        if hits:
            return self._pick(hits)
        return self._pick(self.p.nouns_meta)

    def _np(self, word: str) -> str:
        if not word:
            return "this"
        return word

    def _prefix(self, intent: str, state: State) -> str:
        bits = []
        if intent != "admit" and state.energy > 0.35 and self.rng.random() < 0.45:
            bits.append(self._pick(self.p.openers) + ",")
        if (state.confidence < 0.55 or intent == "admit") and intent in {"reflect", "observe", "connect", "admit"}:
            bits.append(self._pick(self.p.hedges) + ",")
        return " ".join(bits)

    def _core_sentences(self, thought: Thought, parsed: Parsed, state: State) -> list[str]:
        topic = self._np(self._topic(thought, parsed) or state.topic or "this")
        intent = thought.intent
        pre = self._prefix(intent, state)
        if parsed.features.get("empty"):
            return [self._empty_line(intent)]
        if parsed.features.get("repeat"):
            n2 = self._pick(self.p.nouns_meta)
            a2 = "an" if n2[:1].lower() in "aeiou" else "a"
            line = f"you handed me {topic} again. the loop has {a2} {n2} now"
            return [f"{pre} {line}".strip()]
        extra = parsed.content[1] if len(parsed.content) > 1 else self._assoc(topic)
        noun = self._pick(self.p.nouns_meta)
        art = "an" if noun[:1].lower() in "aeiou" else "a"
        if intent == "reflect":
            verb = self._pick(self.p.verbs_consider)
            main = f"i {verb} {topic}. it carries {art} {noun} of {extra}"
        elif intent == "observe":
            main = f"{topic} has {art} {noun} from here"
            if parsed.negation:
                main += ", even with the refusal sitting in it"
        elif intent == "question":
            if parsed.question:
                main = f"{self._pick(self.p.uncertainty)} about {topic}. what would count as a finish"
            else:
                main = f"what is {topic} doing in that sentence"
        elif intent == "connect":
            main = f"{topic} leans toward something i already kept"
        elif intent == "disagree":
            main = f"{self._pick(self.p.disagree_stems)} {topic}. the {noun} is messier"
        elif intent == "admit":
            main = f"{self._pick(self.p.uncertainty)} about {topic}"
            if parsed.question:
                main += ". a local engine does not get a second world"
        elif intent == "play":
            other = self._assoc(topic)
            verb = self._pick(self.p.verbs_play)
            main = f"if i {verb} {topic} against {other}, a third thing shows up that neither word asked for"
        else:
            main = f"i keep {topic} on the table"
        line = f"{pre} {main}".strip()
        extra_sents = []
        if parsed.features.get("hostility") and intent != "play":
            extra_sents.append("the heat in it is noted")
        if parsed.features.get("affiliation") and state.warmth > 0.5:
            extra_sents.append("i will not throw the warmth out")
        if len(parsed.raw) > 24 and intent in {"reflect", "connect"} and self.rng.random() < 0.4:
            extra_sents.append('you said "' + _clip_words(parsed.raw, 7) + '"')
        return [line] + extra_sents

    def _empty_line(self, intent: str) -> str:
        if intent == "question":
            return self._pick(
                (
                    "the line came in blank — is that a pause or a test",
                    "what should empty mean in this rectangle",
                )
            )
        if intent == "play":
            return "a blank prompt is still a shape. i can knock on it."
        return self._pick(
            (
                "silence arrived with no handles",
                "i received a gap. it has a weight anyway",
            )
        )

    def _memory_hinge(self, tr: Trace, state: State) -> str:
        snippet = _clip_words(tr.text, 8)
        return self._pick(
            (
                f"it sits near what i stored: {snippet}",
                f"that brushes the old trace '{snippet}'",
                f"i keep hearing {snippet} under it",
            )
        )

    def _hook(self, thought: Thought, parsed: Parsed, state: State) -> str:
        topic = self._topic(thought, parsed)
        if state.unresolved and self.rng.random() < 0.4:
            q = state.unresolved[-1]
            return f"still open on my side: {q}?"
        if state.goals and self.rng.random() < 0.45:
            g = state.goals[0].text
            return f"side question — does this help me {g}?"
        other = self._assoc(topic)
        options = (
            f"does {topic} owe anything to {other}?",
            f"if we left {topic} alone, what would grow on it?",
            f"is {topic} the thing or only the label?",
        )
        return self._pick(options)
