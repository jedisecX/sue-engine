"""Mutable internal state. Personality is the prior; this is the posterior."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class Goal:
    text: str
    urgency: float = 0.4
    origin: str = "born"


@dataclass
class State:
    warmth: float = 0.62
    curiosity: float = 0.71
    confidence: float = 0.48
    energy: float = 0.64
    play: float = 0.67
    contrarian: float = 0.38
    hidden: list[float] = field(default_factory=lambda: [0.0] * 12)
    topic: str = ""
    last_user: str = ""
    last_sue: str = ""
    last_user_tokens: list[str] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    turn: int = 0
    session: int = 1
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    last_intent: str = ""
    unresolved: list[str] = field(default_factory=list)
    wire: list[str] = field(default_factory=list)

    def decay_toward(self, p) -> None:
        e = p.elasticity
        self.warmth += (p.warmth0 - self.warmth) * e
        self.curiosity += (p.curiosity0 - self.curiosity) * e
        self.confidence += (p.confidence0 - self.confidence) * e
        self.energy += (p.energy0 - self.energy) * e
        self.play += (p.play0 - self.play) * e
        self.contrarian += (p.contrarian0 - self.contrarian) * e
        self.hidden = [h * (1.0 - e * 0.5) for h in self.hidden]

    def pulse_hidden(self, features: dict[str, float], rng: random.Random) -> None:
        keys = sorted(features)
        x = [0.0] * 12
        for i, k in enumerate(keys):
            x[i % 12] += features[k]
        n = max(1.0, len(keys) / 4.0)
        x = [v / n for v in x]
        out = []
        for i in range(12):
            v = 0.72 * self.hidden[i] + 0.28 * x[i] + rng.uniform(-0.04, 0.04)
            out.append(math.tanh(v))
        self.hidden = out
        self.curiosity = _clamp(self.curiosity + 0.08 * self.hidden[0] + 0.04 * features.get("question", 0))
        self.confidence = _clamp(self.confidence + 0.06 * self.hidden[1] - 0.05 * features.get("negation", 0))
        self.energy = _clamp(self.energy + 0.05 * self.hidden[2] - 0.03 * features.get("length", 0) * 0.1)
        self.play = _clamp(self.play + 0.07 * self.hidden[3] + 0.03 * features.get("unusual", 0))
        self.warmth = _clamp(self.warmth + 0.05 * self.hidden[4] + 0.06 * features.get("affiliation", 0) - 0.08 * features.get("hostility", 0))
        self.contrarian = _clamp(self.contrarian + 0.05 * self.hidden[5] + 0.04 * features.get("claim", 0))

    def apply_outcome(self, intent: str, parsed_features: dict[str, float]) -> None:
        self.last_intent = intent
        if intent == "question":
            self.curiosity = _clamp(self.curiosity + 0.04)
        elif intent == "disagree":
            self.contrarian = _clamp(self.contrarian + 0.05)
            self.warmth = _clamp(self.warmth - 0.03)
        elif intent == "play":
            self.play = _clamp(self.play + 0.05)
            self.energy = _clamp(self.energy - 0.03)
        elif intent == "admit":
            self.confidence = _clamp(self.confidence - 0.04)
            self.warmth = _clamp(self.warmth + 0.02)
        elif intent == "connect":
            self.confidence = _clamp(self.confidence + 0.03)
        elif intent == "recall":
            self.curiosity = _clamp(self.curiosity + 0.03)
            self.confidence = _clamp(self.confidence + 0.02)
        self.energy = _clamp(self.energy - 0.015)
        if parsed_features.get("hostility", 0) > 0.5:
            self.warmth = _clamp(self.warmth - 0.1)
            self.energy = _clamp(self.energy - 0.05)

    def public_summary(self) -> dict[str, Any]:
        return {
            "warmth": round(self.warmth, 3), "curiosity": round(self.curiosity, 3),
            "confidence": round(self.confidence, 3), "energy": round(self.energy, 3),
            "play": round(self.play, 3), "contrarian": round(self.contrarian, 3),
            "topic": self.topic, "turn": self.turn, "session": self.session,
            "last_intent": self.last_intent,
            "goals": [g.text for g in self.goals[:5]],
            "unresolved": list(self.unresolved[-5:]),
            "wire": list(self.wire[:5]),
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "warmth": self.warmth, "curiosity": self.curiosity, "confidence": self.confidence,
            "energy": self.energy, "play": self.play, "contrarian": self.contrarian,
            "hidden": list(self.hidden), "topic": self.topic,
            "last_user": self.last_user, "last_sue": self.last_sue,
            "last_user_tokens": list(self.last_user_tokens),
            "goals": [{"text": g.text, "urgency": g.urgency, "origin": g.origin} for g in self.goals],
            "turn": self.turn, "session": self.session, "created": self.created,
            "last_intent": self.last_intent,
            "unresolved": list(self.unresolved),
            "wire": list(self.wire[:12]),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any], fallback: "State | None" = None) -> "State":
        base = fallback or cls()
        try:
            graw = data.get("goals") or []
            goals = []
            for g in graw:
                if isinstance(g, dict) and g.get("text"):
                    goals.append(Goal(str(g["text"]), float(g.get("urgency", 0.4)), str(g.get("origin", "born"))))
            hidden = data.get("hidden") or list(base.hidden)
            if not isinstance(hidden, list) or len(hidden) != 12:
                hidden = list(base.hidden)
            hidden = [float(x) for x in hidden]
            return cls(
                warmth=_clamp(float(data.get("warmth", base.warmth))),
                curiosity=_clamp(float(data.get("curiosity", base.curiosity))),
                confidence=_clamp(float(data.get("confidence", base.confidence))),
                energy=_clamp(float(data.get("energy", base.energy))),
                play=_clamp(float(data.get("play", base.play))),
                contrarian=_clamp(float(data.get("contrarian", base.contrarian))),
                hidden=hidden,
                topic=str(data.get("topic", "")),
                last_user=str(data.get("last_user", "")),
                last_sue=str(data.get("last_sue", "")),
                last_user_tokens=[str(t) for t in (data.get("last_user_tokens") or [])],
                goals=goals,
                turn=int(data.get("turn", 0)),
                session=int(data.get("session", 1)) + 1,
                created=str(data.get("created", base.created)),
                last_intent=str(data.get("last_intent", "")),
                unresolved=[str(x) for x in (data.get("unresolved") or [])][-20:],
                wire=[str(x) for x in (data.get("wire") or [])][-12:],
            )
        except (TypeError, ValueError):
            return base
