"""Glosses for Sue's word bank.

Not WordNet. Not a reply table.
Priority: learned (from chat/feeds) > hand core > composed from class + neighbors.
Every classified word can return a gloss.
"""

from __future__ import annotations

CORE: dict[str, str] = {
    "river": "a flowing body of water, usually inland",
    "bridge": "a span that carries a path over a gap or water",
    "water": "the liquid that fills rivers, rain, and bodies",
    "flood": "water rising over its usual banks",
    "news": "a recent report of something that happened",
    "wire": "the incoming feed of headlines Sue stores",
    "feed": "a stream of items, often RSS",
    "headline": "the short title of a news item",
    "source": "where a report came from",
    "memory": "a stored trace Sue can retrieve later",
    "word": "a unit of language she can class and link",
    "lexicon": "her dictionary of classes, neighbors, and glosses",
    "town": "a settled place smaller than a city",
    "parish": "a local civil or church district",
    "storm": "violent weather with wind and often rain",
    "power": "capacity to act, or electrical supply",
    "meter": "a device that measures flow or use",
    "grid": "a network that carries power or data",
    "code": "instructions a machine can run",
    "server": "a machine that answers requests",
    "signal": "a change that carries information",
    "noise": "unwanted signal that hides the useful part",
    "law": "a rule a court can enforce",
    "court": "the place a case is heard",
    "death": "the end of a life",
    "life": "the span of living",
    "fear": "the sense that harm is near",
    "hope": "the sense that something better can arrive",
    "pain": "hurt in body or mind",
    "trust": "readiness to rely on someone or something",
    "doubt": "the gap where proof should be",
    "war": "organized fighting between groups",
    "peace": "the stretch without that fighting",
    "house": "a building people live in",
    "door": "the opening you pass to enter",
    "fire": "burning that gives heat and light",
    "light": "what makes things visible",
    "night": "the dark half of the day",
    "sleep": "the rest state of a body",
    "dream": "images that arrive in sleep, or a want",
    "body": "the physical person",
    "heart": "the pump in the chest, or the felt center",
    "machine": "an assembled tool that does work",
    "engine": "the part that turns energy into motion",
    "money": "the token used to trade",
    "work": "effort toward a task",
    "play": "effort without that task pressure",
    "think": "to turn something over in the mind",
    "feel": "to register a quality or mood",
    "love": "a strong pull to keep someone or something",
    "hate": "a strong push away",
    "ask": "to open a question",
    "answer": "what closes a question, if it can",
    "claim": "a statement offered as true",
    "proof": "what would make a claim hold",
    "lie": "a claim offered as true that is not",
    "fact": "a claim that already held up",
    "lantern": "a portable light in a case",
    "drawer": "a sliding box that holds things",
    "bayou": "a slow waterway, often swampy",
    "current": "the push of water or electricity",
    "bank": "the edge of a river, or a money house",
    "stone": "hard mineral stuff",
    "road": "a prepared path for travel",
    "field": "open ground, often for work or crop",
    "rain": "water falling from cloud",
    "wind": "moving air",
    "cloud": "visible water or ice hanging in air",
    "sky": "the space above the ground",
    "sun": "the star that lights the day",
    "moon": "the body that lights some nights",
    "star": "a distant sun",
    "ocean": "the great salt water",
    "ship": "a large vessel on water",
    "border": "the line between two places",
    "flag": "a cloth sign for a group",
    "nation": "a people under one political roof",
    "record": "a kept account of what happened",
    "case": "a matter before a court, or an instance",
    "breach": "a break in a wall, promise, or system",
    "exploit": "a use of a weakness, often in a system",
}


def compose(word: str, tag: str | None, neighbors: list[str]) -> str:
    w = word.lower()
    tag = tag or "word"
    near = ", ".join(neighbors[:3]) if neighbors else ""
    if tag == "verb":
        base = f"to {w}, an action"
    elif tag == "adj":
        base = f"{w}: a quality of a thing"
    elif tag == "qual":
        base = f"{w}: a felt or structural quality"
    elif tag == "name":
        base = f"{w}: a name she has stored"
    else:
        base = f"{w}: a {tag}"
    if near:
        return f"{base}; sits near {near}"
    return base


def short_gloss(text: str, n: int = 14) -> str:
    words = text.replace(";", ".").split()
    if len(words) <= n:
        return text.rstrip(".")
    return " ".join(words[:n]).rstrip(".,") + "…"
