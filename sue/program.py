"""Frame-echo reader for stored news. Motif count, not a forecast."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from .memory import Memory, tokenize

FRAMES = {
    "war": frozenset("war strike missile troop invade attack bomb drone ceasefire front".split()),
    "cyber": frozenset("hack breach malware ransomware exploit leak dump phishing".split()),
    "plague": frozenset("virus outbreak pandemic vaccine variant quarantine infection".split()),
    "disaster": frozenset("flood fire quake storm hurricane crash spill collapse famine".split()),
    "power": frozenset("grid blackout meter nuclear reactor energy outage plant pipeline".split()),
    "market": frozenset("market stock crash bank rate inflation tariff trade debt".split()),
    "state": frozenset("court law ban bill vote election congress senate agency warrant".split()),
    "border": frozenset("border migrant visa wall crossing deport asylum patrol".split()),
    "techctrl": frozenset("ai model surveillance camera chip ban censor platform algorithm".split()),
    "prime": frozenset("warn prepare coming imminent inevitable drill scenario simulation".split()),
}

@dataclass
class Echo:
    frame: str
    score: float
    line: str
    prior: str

def frames_in(text: str):
    bag = set(tokenize(text))
    hits = [(name, len(bag & keys)) for name, keys in FRAMES.items() if bag & keys]
    hits.sort(key=lambda x: -x[1])
    return hits

def scan(memory: Memory, topic: str = "", limit: int = 6):
    news = [t for t in memory.traces if t.kind == "news"]
    if not news:
        return []
    recent, prior = news[-8:], news[:-1] if len(news) > 1 else []
    out = []
    topic_toks = tokenize(topic) if topic else []
    for item in reversed(recent):
        fr = frames_in(item.text)
        frame = fr[0][0] if fr else "plain"
        best, best_prior = 0.0, ""
        sa = set(item.tokens)
        for old in prior[-24:]:
            if old.id == item.id:
                continue
            sb = set(old.tokens)
            s = (len(sa & sb) / float(len(sa | sb))) if sa and sb else 0.0
            if topic_toks:
                st = set(topic_toks)
                s += 0.15 * ((len(sa & st) / float(len(sa | st))) if st else 0.0)
            if s > best:
                best, best_prior = s, old.text
        out.append(Echo(frame, round(best, 3), item.text, best_prior))
        if len(out) >= limit:
            break
    return out

def tally(memory: Memory):
    c = Counter()
    for t in memory.traces:
        if t.kind != "news":
            continue
        for name, n in frames_in(t.text):
            c[name] += n
    return c.most_common(8)

def speak(echoes, tallies):
    if not echoes and not tallies:
        return ["no stored headlines to read for repeating frames"]
    lines = []
    if tallies:
        lines.append("frames on the pile: " + ", ".join(f"{n} {k}" for k, n in tallies[:3]))
    if echoes:
        e = echoes[0]
        lines.append(f"this line sits in the {e.frame} frame")
        if e.prior and e.score >= 0.08:
            prior = e.prior.split(" · ", 1)[-1]
            lines.append(f"it rhymes with an older line: {prior[:120]}")
        else:
            lines.append("no close rhyme in the drawer yet")
    lines.append("that is a motif count, not a forecast")
    return lines[:4]
