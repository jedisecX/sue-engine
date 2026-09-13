"""Sue facade. Wires parse -> reason -> realize -> state/memory update."""

from __future__ import annotations

import random
from pathlib import Path

from .generate import ComposeRealizer
from .memory import Memory
from .parse import parse
from .personality import Personality
from .reasoning import Reasoner, Thought
from .state import State


class Sue:
    def __init__(self, memory_path: Path | None = None, seed: int | None = None):
        self.personality = Personality()
        self.rng = random.Random(seed)
        self.memory = Memory.load(memory_path or Path("sue_memory.json"))
        self.state = State(
            warmth=self.personality.warmth0,
            curiosity=self.personality.curiosity0,
            confidence=self.personality.confidence0,
            energy=self.personality.energy0,
            play=self.personality.play0,
            contrarian=self.personality.contrarian0,
        )
        self._restore_state()
        self.reasoner = Reasoner(self.personality, self.rng)
        self.realizer = ComposeRealizer(self.personality, self.rng)
        self.last_thought: Thought | None = None
        self.last_candidates: list[Thought] = []
        self.show_summary = True

    def _state_blob_path(self) -> Path:
        return self.memory.path.with_name("sue_state.json")

    def _restore_state(self) -> None:
        p = self._state_blob_path()
        if not p.exists():
            return
        try:
            import json

            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.state = State.from_json(data, fallback=self.state)
        except (OSError, ValueError, TypeError):
            return

    def persist(self) -> None:
        import json

        self.memory.save()
        blob = self.state.to_json()
        tmp = self._state_blob_path().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        tmp.replace(self._state_blob_path())

    def startup_line(self) -> str:
        name = self.memory.user_name
        visits = self.state.session
        if visits <= 1 and not self.memory.traces:
            return (
                "sue. a small generative engine in a terminal. "
                "not a model, not a person — state, memory, and a composer."
            )
        who = name or "you"
        return f"sue again. session {visits}. hello {who}."

    def respond(self, raw: str) -> str:
        parsed = parse(raw, self.personality.stop, self.state.last_user_tokens)
        self.state.decay_toward(self.personality)
        self.state.pulse_hidden(parsed.features, self.rng)
        self.state.turn += 1
        weak = {"why", "how", "what", "who", "when", "where"}
        if parsed.topic_hint and parsed.topic_hint not in weak:
            self.state.topic = parsed.topic_hint
        elif parsed.topic_hint and not self.state.topic:
            self.state.topic = parsed.topic_hint
        self._maybe_name(parsed)
        cands, thought = self.reasoner.consider(parsed, self.state, self.memory)
        self.last_candidates = cands
        self.last_thought = thought
        text = self.realizer.realize(thought, parsed, self.state)
        self.state.apply_outcome(thought.intent, parsed.features)
        self.state.last_user = parsed.raw
        self.state.last_sue = text
        self.state.last_user_tokens = list(parsed.tokens)
        self._write_memories(parsed, thought, text)
        goal = self.reasoner.maybe_new_goal(parsed, self.state)
        if goal:
            self.state.goals.append(goal)
            self.state.goals = self.state.goals[-8:]
        if thought.intent == "question" and thought.topic:
            q = thought.topic
            if q not in self.state.unresolved:
                self.state.unresolved.append(q)
                self.state.unresolved = self.state.unresolved[-12:]
        try:
            self.persist()
        except OSError:
            pass
        return text

    def _maybe_name(self, parsed) -> None:
        tokens = parsed.tokens
        if "name" in tokens and tokens:
            import re

            m = re.search(
                r"(?:my name is|i am|i'm|call me)\s+([A-Za-z][A-Za-z0-9_-]{1,24})",
                parsed.raw,
                re.I,
            )
            if m:
                self.memory.user_name = m.group(1)
                self.memory.add(f"user name is {m.group(1)}", kind="decision", importance=0.85)

    def _write_memories(self, parsed, thought: Thought, reply: str) -> None:
        if parsed.raw and not parsed.features.get("empty"):
            imp = 0.35
            if parsed.features.get("claim"):
                imp += 0.15
            if parsed.features.get("affiliation"):
                imp += 0.1
            if len(parsed.content) >= 3:
                imp += 0.1
            self.memory.add(parsed.raw, kind="user", importance=imp)
        if thought.intent in {"connect", "play"} and thought.topic:
            self.memory.add(f"topic:{thought.topic}", kind="topic", importance=0.4)
        if thought.intent == "disagree":
            self.memory.add(f"disputed:{thought.topic}", kind="decision", importance=0.55)
        if self.state.turn % 3 == 0:
            self.memory.add(reply, kind="sue", importance=0.25)

    def reset_session(self) -> None:
        p = self.personality
        kept_goals = list(self.state.goals)
        self.state = State(
            warmth=p.warmth0,
            curiosity=p.curiosity0,
            confidence=p.confidence0,
            energy=p.energy0,
            play=p.play0,
            contrarian=p.contrarian0,
            session=self.state.session + 1,
            created=self.state.created,
            goals=kept_goals,
        )
        self.last_thought = None
        self.last_candidates = []
        self.persist()

    def forget(self, kind: str | None = None) -> int:
        if kind:
            n = self.memory.forget_kind(kind)
            self.persist()
            return n
        self.memory.forget_all()
        self.memory.user_name = None
        self.state.unresolved.clear()
        self.state.goals.clear()
        self.state.topic = ""
        self.persist()
        return 0

    def ingest_feeds(self, feeds_path: Path | None = None, fetch=None):
        from .ingest import ingest, load_feeds

        path = feeds_path or self.memory.path.with_name("feeds.json")
        feeds = load_feeds(path)
        report = ingest(self.memory, feeds, fetch=fetch, state=self.state)
        try:
            self.persist()
        except OSError:
            pass
        return report, feeds

    def inspect_state(self) -> dict:
        d = self.state.public_summary()
        d["user_name"] = self.memory.user_name
        d["traces"] = len(self.memory.traces)
        if self.last_thought:
            d["last_thought"] = self.realizer.thought_summary(self.last_thought)
        return d

    def inspect_memory(self, limit: int = 12) -> list[dict]:
        return self.memory.public_list(limit=limit)
