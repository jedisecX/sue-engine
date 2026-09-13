"""Persistent memory with relevance retrieval. JSON on disk."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9']{1,32}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text)]


@dataclass
class Trace:
    id: int
    text: str
    kind: str
    tokens: list[str]
    importance: float
    created: str
    hits: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind,
            "tokens": self.tokens,
            "importance": self.importance,
            "created": self.created,
            "hits": self.hits,
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Trace | None":
        try:
            return cls(
                id=int(d["id"]),
                text=str(d.get("text", "")),
                kind=str(d.get("kind", "note")),
                tokens=[str(t) for t in (d.get("tokens") or tokenize(str(d.get("text", ""))))],
                importance=float(d.get("importance", 0.4)),
                created=str(d.get("created", "")),
                hits=int(d.get("hits", 0)),
            )
        except (KeyError, TypeError, ValueError):
            return None


@dataclass
class Memory:
    path: Path
    traces: list[Trace] = field(default_factory=list)
    next_id: int = 1
    user_name: str | None = None
    dirty: bool = False

    @classmethod
    def load(cls, path: Path) -> "Memory":
        mem = cls(path=path)
        if not path.exists():
            return mem
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return mem
        if not isinstance(raw, dict):
            return mem
        mem.user_name = raw.get("user_name")
        mem.next_id = int(raw.get("next_id") or 1)
        for item in raw.get("traces") or []:
            if isinstance(item, dict):
                t = Trace.from_json(item)
                if t:
                    mem.traces.append(t)
        if mem.traces:
            mem.next_id = max(mem.next_id, max(t.id for t in mem.traces) + 1)
        return mem

    def save(self) -> None:
        payload = {
            "user_name": self.user_name,
            "next_id": self.next_id,
            "traces": [t.to_json() for t in self.traces[-400:]],
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
        self.dirty = False

    def add(self, text: str, kind: str = "note", importance: float = 0.5) -> Trace:
        text = " ".join(text.split())
        if not text:
            text = "(empty)"
        key = text.lower()
        for t in self.traces[-12:]:
            if t.text.lower() == key and t.kind == kind:
                t.importance = min(1.0, t.importance + 0.05)
                t.hits += 1
                self.dirty = True
                return t
        tr = Trace(
            id=self.next_id,
            text=text[:400],
            kind=kind,
            tokens=tokenize(text),
            importance=max(0.05, min(1.0, importance)),
            created=datetime.now().isoformat(timespec="seconds"),
        )
        self.next_id += 1
        self.traces.append(tr)
        self.traces = self.traces[-400:]
        self.dirty = True
        return tr

    def forget_all(self) -> None:
        self.traces.clear()
        self.dirty = True

    def forget_kind(self, kind: str) -> int:
        before = len(self.traces)
        self.traces = [t for t in self.traces if t.kind != kind]
        dropped = before - len(self.traces)
        if dropped:
            self.dirty = True
        return dropped

    def retrieve(self, query_tokens: list[str], k: int = 4, kinds: set[str] | None = None) -> list[Trace]:
        if not self.traces:
            return []
        q = {t for t in query_tokens if len(t) > 2}
        scored: list[tuple[float, Trace]] = []
        n = len(self.traces)
        for i, tr in enumerate(self.traces):
            if kinds and tr.kind not in kinds:
                continue
            bag = set(tr.tokens)
            if not bag:
                overlap = 0.0
            elif not q:
                overlap = 0.08
            else:
                overlap = len(q & bag) / max(1, len(q))
            recency = 0.35 + 0.65 * ((i + 1) / n)
            score = overlap * 1.6 + tr.importance * 0.5 + recency * 0.25 + min(tr.hits, 6) * 0.03
            if overlap == 0 and kinds is None:
                score *= 0.35
            scored.append((score, tr))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        seen = set()
        for _, tr in scored:
            if tr.id in seen:
                continue
            seen.add(tr.id)
            tr.hits += 1
            out.append(tr)
            if len(out) >= k:
                break
        if out:
            self.dirty = True
        return out

    def public_list(self, limit: int = 12) -> list[dict[str, Any]]:
        rows = []
        for t in self.traces[-limit:]:
            rows.append({"id": t.id, "kind": t.kind, "importance": round(t.importance, 2), "text": t.text})
        return rows
