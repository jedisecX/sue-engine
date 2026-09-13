"""Sue facade. Wires parse -> reason -> realize -> state/memory update."""

from __future__ import annotations

import random
from pathlib import Path

from .generate import ComposeRealizer
from .lexicon import Lexicon
from .memory import Memory
from .parse import parse
from .personality import Personality
from .reasoning import Reasoner, Thought
from .state import State


class Sue:
    def __init__(self, memory_path: Path | None = None, seed: int | None = None):
        mem_path = memory_path or Path("sue_memory.json")
        lex_path = mem_path.with_name("lexicon.json")
        self.lex_path = lex_path
        self.personality = Personality(lexicon=Lexicon(extra=lex_path if lex_path.exists() else None))
        self.personality.lexicon.path = lex_path
        self.last_learned: list[str] = []
        self.rng = random.Random(seed)
        self.memory = Memory.load(mem_path)
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
        try:
            self.personality.lexicon.save(self.lex_path)
        except OSError:
            pass
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
        mem_tokens = []
        for t in self.memory.traces[-8:]:
            mem_tokens.extend(t.tokens[:6])
        chat_words = list(parsed.content) + list(parsed.tokens)
        self.last_learned = list(dict.fromkeys(
            self.personality.lexicon.learn_context(chat_words, mem_tokens)
        ))
        if self.last_learned:
            self.state.curiosity = min(1.0, self.state.curiosity + 0.04)
            lex = self.personality.lexicon
            for w in self.last_learned[:6]:
                neigh = lex.related(w, limit=4)
                line = f"word:{w}" + ((" near " + " ".join(neigh)) if neigh else "")
                self.memory.add(line, kind="lex", importance=0.55)
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
                parsed.raw, re.I,
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
        if thought.intent in {"connect", "play", "recall"} and thought.topic:
            self.memory.add(f"topic:{thought.topic}", kind="topic", importance=0.4)
        if thought.intent == "disagree":
            self.memory.add(f"disputed:{thought.topic}", kind="decision", importance=0.55)
        if self.state.turn % 3 == 0:
            self.memory.add(reply, kind="sue", importance=0.25)

    def reset_session(self) -> None:
        p = self.personality
        kept_goals = list(self.state.goals)
        wire = list(getattr(self.state, "wire", []))
        self.state = State(
            warmth=p.warmth0, curiosity=p.curiosity0, confidence=p.confidence0,
            energy=p.energy0, play=p.play0, contrarian=p.contrarian0,
            session=self.state.session + 1, created=self.state.created,
            goals=kept_goals, wire=wire,
        )
        self.last_thought = None
        self.last_candidates = []
        self.persist()

    def forget(self, kind: str | None = None) -> int:
        if kind:
            n = self.memory.forget_kind(kind)
            if kind == "news" and hasattr(self.state, "wire"):
                self.state.wire.clear()
            self.persist()
            return n
        self.memory.forget_all()
        self.memory.user_name = None
        self.state.unresolved.clear()
        self.state.goals.clear()
        self.state.topic = ""
        if hasattr(self.state, "wire"):
            self.state.wire.clear()
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

    def inspect_lexicon(self, query: str | None = None) -> dict:
        lex = self.personality.lexicon
        chat, seen = [], set()
        for src in (list(self.state.last_user_tokens), list(getattr(self.state, "last_user", "").split())):
            for w in src:
                w = w.lower().strip("..,!?\"'")
                if len(w) >= 3 and w not in seen:
                    seen.add(w)
                    chat.append(w)
        for t in self.memory.traces[-16:]:
            if t.kind not in {"user", "news", "topic", "lex"}:
                continue
            for w in t.tokens[:10]:
                if len(w) >= 3 and w not in seen:
                    seen.add(w)
                    chat.append(w)
        if query:
            q = query.lower()
            return {
                "query": q,
                "class": lex.word_class(q),
                "known": lex.knows(q),
                "neighbors": lex.related(q, limit=10),
                "learned": q in lex.learned,
            }
        rows = [{
            "word": w,
            "class": lex.word_class(w) or "-",
            "known": lex.knows(w),
            "neighbors": lex.related(w, limit=4),
        } for w in chat[:24]]
        return {
            "size": lex.size(),
            "just_acquired": list(self.last_learned),
            "learned": list(lex.learned[-20:]),
            "topic": self.state.topic,
            "topic_neighbors": lex.related(self.state.topic) if self.state.topic else [],
            "from_chat": rows,
        }

    def inspect_news(self, limit: int = 12) -> list[dict]:
        rows = []
        for t in self.memory.traces:
            if t.kind == "news":
                rows.append({"id": t.id, "kind": t.kind, "importance": round(t.importance, 2), "text": t.text})
        return rows[-limit:]
