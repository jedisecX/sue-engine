"""Sue dictionary: classes, neighborhoods, context learning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

NOUN, VERB, ADJ, QUAL, NAME = "noun", "verb", "adj", "qual", "name"
_CLASS: dict[str, str] = {}


def _cls(tag: str, *words: str) -> None:
    for w in words:
        _CLASS[w] = tag


_cls(NOUN, *"memory drawer trace echo dust name handle label thread time clock gap interval weight angle draft seam grain weather tilt pulse warmth edge splinter distance task friction loop tool game spark night moon tide star map ocean salt floor code patch break god scale silence claim death stop quiet life mess appetite voice return seat file cause story hinge method hands steps river bridge water flood bank stone door key lock room house road field tree fire smoke light shadow window book page word sentence question answer proof news wire feed headline source signal body bone blood pain sleep dream fear anger grief hope doubt trust law court money work machine engine meter grid power storm rain wind sky sun server packet repo commit lantern parish".split())
_cls(VERB, *"think feel love hate work play dream hold weigh trace press fold tilt stitch keep push pull open close cut build break fix read write speak listen wait run walk sit stand sleep wake give take send fetch store forget recall ingest parse score pick ask answer prove deny claim doubt trust hurt heal burn flood grow die live".split())
_cls(ADJ, *"thin thick sharp dull hot cold warm cool wet dry loud quiet bright dark soft hard fast slow old new empty full open shut true false near far small large strange local".split())
_cls(QUAL, *"shape edge grain weight aftertaste hinge draft seam texture tone pressure slack tension clarity fog residue glint gap surplus lack".split())

_SEEDS = {
    "memory": ("drawer", "trace", "echo", "recall", "store", "forget"),
    "river": ("bridge", "water", "flood", "bank", "current", "stone"),
    "bridge": ("river", "span", "road", "gap"),
    "news": ("wire", "headline", "feed", "source", "claim", "fact"),
    "wire": ("news", "signal", "feed", "drawer"),
    "code": ("loop", "break", "patch", "bug", "repo"),
    "think": ("weight", "angle", "draft", "doubt", "proof"),
    "feel": ("grain", "weather", "pulse", "warmth"),
    "love": ("keep", "warmth", "hold", "trust"),
    "hate": ("edge", "push", "distance", "anger"),
    "work": ("task", "friction", "loop", "tool"),
    "play": ("game", "tilt", "spark", "fold"),
    "moon": ("tide", "night", "pull"),
    "ocean": ("salt", "wave", "ship", "dark"),
    "fear": ("edge", "dark", "pulse"),
    "power": ("grid", "meter", "engine"),
    "house": ("door", "room", "key"),
    "door": ("key", "lock", "open", "shut"),
    "town": ("road", "house", "river", "parish"),
    "repo": ("commit", "code", "build"),
    "lantern": ("light", "drawer", "night"),
    "why": ("cause", "gap", "story"),
    "how": ("method", "hands", "tool"),
}


def _merge_pairs(src):
    bags = {}
    for k, vs in src.items():
        k = k.lower()
        bags.setdefault(k, set())
        for v in vs:
            v = v.lower()
            if v == k:
                continue
            bags[k].add(v)
            bags.setdefault(v, set()).add(k)
    return {k: tuple(sorted(vs)) for k, vs in bags.items()}


NEIGHBORS = _merge_pairs(_SEEDS)
_SKIP = frozenset("a an the and or but if then else when of to in on at by for from with as is are was were be been being it this that i you he she we they me my your so not no yes do does did have has had just about into over after before out up down can could would should will what who where why how sue".split())


def guess_class(word: str) -> str:
    w = word.lower()
    if w.endswith(("ing", "ize", "ise")) or (w.endswith("ed") and len(w) > 4):
        return VERB
    if w.endswith(("ous", "ful", "ish", "less", "able", "al", "ic", "ly")):
        return ADJ
    if w.endswith(("ness", "tion", "sion", "ment", "hood", "ity")):
        return NOUN
    return NOUN


class Lexicon:
    def __init__(self, extra: Path | None = None):
        self.klass = dict(_CLASS)
        self.neighbors = {k: list(v) for k, v in NEIGHBORS.items()}
        self.path = extra
        self.dirty = False
        self.learned = []
        if extra and extra.exists():
            self.merge_json(extra)

    def merge_json(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        for w, tag in (data.get("class") or {}).items():
            if isinstance(w, str) and tag in {NOUN, VERB, ADJ, QUAL, NAME}:
                self.klass[w.lower()] = tag
        for w, vs in (data.get("neighbors") or {}).items():
            if not isinstance(w, str) or not isinstance(vs, list):
                continue
            key = w.lower()
            bag = set(self.neighbors.get(key, ()))
            for v in vs:
                if isinstance(v, str) and v.lower() != key:
                    bag.add(v.lower())
                    self.neighbors.setdefault(v.lower(), [])
                    if key not in self.neighbors[v.lower()]:
                        self.neighbors[v.lower()].append(key)
            self.neighbors[key] = sorted(bag)
        for w in data.get("learned") or []:
            if isinstance(w, str) and w.lower() not in self.learned:
                self.learned.append(w.lower())

    def word_class(self, word: str):
        return self.klass.get(word.lower())

    def related(self, word: str, limit: int = 6):
        return list(self.neighbors.get(word.lower(), ()))[:limit]

    def expand(self, tokens: Iterable[str], limit: int = 8):
        out, seen = [], set()
        for t in tokens:
            for n in self.related(t, limit=4):
                if n not in seen:
                    seen.add(n)
                    out.append(n)
                if len(out) >= limit:
                    return out
        return out

    def qualities(self):
        return [w for w, t in self.klass.items() if t == QUAL]

    def knows(self, word: str) -> bool:
        w = word.lower()
        return w in self.klass or w in self.neighbors

    def _link(self, a: str, b: str) -> None:
        if a == b:
            return
        for x, y in ((a, b), (b, a)):
            bag = list(self.neighbors.get(x, []))
            if y not in bag:
                bag.append(y)
                self.neighbors[x] = bag[:16]
                self.dirty = True

    def learn_context(self, tokens: Iterable[str], known_extra: Iterable[str] = ()) -> list[str]:
        raw = [t.lower() for t in tokens if t and t.isalpha() and len(t) >= 3 and t.lower() not in _SKIP]
        if not raw:
            return []
        extras = [t.lower() for t in known_extra if t]
        acquired = []
        known = [t for t in raw if self.knows(t)] + extras
        unknown = [t for t in raw if not self.knows(t)]
        for w in unknown:
            self.klass.setdefault(w, guess_class(w))
            peers = [p for p in known if p != w][:6] or [p for p in raw if p != w][:4]
            for p in peers:
                self._link(w, p)
            self.neighbors.setdefault(w, list(peers))
            self.dirty = True
            acquired.append(w)
            if w not in self.learned:
                self.learned.append(w)
        if len(known) >= 2:
            for a, b in zip(known, known[1:]):
                self._link(a, b)
        self.learned = self.learned[-40:]
        return acquired

    def save(self, path: Path | None = None) -> None:
        dest = path or self.path
        if dest is None or not self.dirty:
            return
        payload = {
            "class": {w: self.klass[w] for w in self.learned if w in self.klass},
            "neighbors": {w: self.neighbors.get(w, [])[:12] for w in self.learned if w in self.neighbors},
            "learned": list(self.learned),
        }
        if dest.exists():
            try:
                old = json.loads(dest.read_text(encoding="utf-8"))
                if isinstance(old, dict):
                    klass = dict(old.get("class") or {})
                    klass.update(payload["class"])
                    neigh = dict(old.get("neighbors") or {})
                    for k, vs in payload["neighbors"].items():
                        neigh[k] = sorted(set(neigh.get(k) or []) | set(vs))[:16]
                    payload["class"], payload["neighbors"] = klass, neigh
                    prev = [str(x) for x in (old.get("learned") or [])]
                    payload["learned"] = list(dict.fromkeys(prev + payload["learned"]))[-80:]
            except (OSError, json.JSONDecodeError):
                pass
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(dest)
        self.path = dest
        self.dirty = False

    def size(self):
        return {
            "classified": len(self.klass),
            "nodes": len(self.neighbors),
            "edges": sum(len(v) for v in self.neighbors.values()) // 2,
            "learned": len(self.learned),
        }


_DEFAULT = None


def default_lexicon(extra: Path | None = None) -> Lexicon:
    global _DEFAULT
    if extra is not None:
        return Lexicon(extra=extra)
    if _DEFAULT is None:
        _DEFAULT = Lexicon()
    return _DEFAULT
