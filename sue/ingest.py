"""Optional RSS intake. Writes Memory traces. Does not speak.

Network is opt-in. Tests should pass a local XML path or a fetch function.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from html import unescape

from .memory import Memory, tokenize
from .state import Goal, State

FetchFn = Callable[[str], str]

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class FeedSpec:
    url: str
    tag: str = "wire"
    max_items: int = 8


@dataclass
class Item:
    guid: str
    title: str
    summary: str
    link: str
    source: str


@dataclass
class IngestReport:
    feeds: int = 0
    fetched: int = 0
    stored: int = 0
    skipped: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _strip_html(text: str) -> str:
    text = unescape(TAG_RE.sub(" ", text or ""))
    return WS_RE.sub(" ", text).strip()


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return _strip_html("".join(el.itertext()))


def parse_feed(xml_text: str, source_tag: str) -> list[Item]:
    xml_text = xml_text.strip()
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tag = root.tag.lower()
    items: list[Item] = []
    if tag.endswith("rss") or tag.endswith("rdf"):
        channel = root.find("channel")
        nodes = (channel.findall("item") if channel is not None else root.findall("item"))
        for node in nodes:
            title = _text(node.find("title"))
            link = _text(node.find("link"))
            guid = _text(node.find("guid")) or link or title
            desc = _text(node.find("description")) or _text(node.find("content:encoded", NS))
            if not title:
                continue
            items.append(Item(guid=guid, title=title, summary=desc, link=link, source=source_tag))
    else:
        for node in root.findall("atom:entry", NS) or root.findall("entry"):
            title = _text(node.find("atom:title", NS)) or _text(node.find("title"))
            link_el = node.find("atom:link", NS)
            if link_el is None:
                link_el = node.find("link")
            href = ""
            if link_el is not None:
                href = link_el.get("href") or _text(link_el)
            ident = _text(node.find("atom:id", NS)) or _text(node.find("id")) or href or title
            summary = _text(node.find("atom:summary", NS)) or _text(node.find("summary"))
            if not summary:
                summary = _text(node.find("atom:content", NS)) or _text(node.find("content"))
            if not title:
                continue
            items.append(Item(guid=ident, title=title, summary=summary, link=href, source=source_tag))
    return items


def default_fetch(url: str, timeout: float = 8.0) -> str:
    if url.startswith("file:"):
        path = url[5:]
        if path.startswith("//"):
            path = path[2:]
        return Path(path).read_text(encoding="utf-8", errors="replace")
    path = Path(url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SueEngine/2.0 (+local; rss-ingest)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def load_feeds(path: Path) -> list[FeedSpec]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[FeedSpec] = []
    rows = data if isinstance(data, list) else data.get("feeds") or []
    for row in rows:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        out.append(
            FeedSpec(
                url=str(row["url"]),
                tag=str(row.get("tag") or "wire"),
                max_items=max(1, min(20, int(row.get("max") or row.get("max_items") or 8))),
            )
        )
    return out


def _seen_keys(memory: Memory) -> set[str]:
    keys = set()
    for t in memory.traces:
        if t.kind != "news":
            continue
        keys.add(t.text.lower())
        for tok in t.tokens:
            if tok.startswith("guid:"):
                keys.add(tok[5:])
    return keys


def _line(item: Item) -> str:
    gist = item.summary[:160] if item.summary else ""
    if gist:
        return f"news: {item.source} · {item.title} · {gist}"
    return f"news: {item.source} · {item.title}"


def ingest(
    memory: Memory,
    feeds: list[FeedSpec],
    *,
    fetch: FetchFn | None = None,
    state: State | None = None,
    cap_total: int = 12,
) -> IngestReport:
    report = IngestReport(feeds=len(feeds))
    if not feeds:
        return report
    fetch = fetch or default_fetch
    seen = _seen_keys(memory)
    topic_tokens = set(tokenize(state.topic)) if state and state.topic else set()

    for spec in feeds:
        try:
            xml_text = fetch(spec.url)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as e:
            report.errors.append(f"{spec.tag}: {e}")
            continue
        report.fetched += 1
        items = parse_feed(xml_text, spec.tag)[: spec.max_items]
        for item in items:
            if report.stored >= cap_total:
                report.skipped += 1
                continue
            line = _line(item)
            key = (item.guid or line).lower()
            compact = re.sub(r"[^a-z0-9]+", "", key)
            if key in seen or compact in seen or line.lower() in seen:
                report.skipped += 1
                continue
            imp = 0.42
            bag = set(tokenize(item.title + " " + item.summary))
            if topic_tokens and bag & topic_tokens:
                imp = 0.62
            tr = memory.add(line, kind="news", importance=imp)
            guid_tok = "guid:" + re.sub(r"[^a-z0-9]+", "", key)[:40]
            if guid_tok not in tr.tokens:
                tr.tokens.append(guid_tok)
            seen.add(key)
            seen.add(compact)
            seen.add(line.lower())
            report.stored += 1
            if state and topic_tokens and bag & topic_tokens:
                gtext = f"understand {spec.tag} on {state.topic}"
                if not any(g.text == gtext for g in state.goals):
                    state.goals.append(Goal(text=gtext, urgency=0.35, origin="news"))
                    state.goals = state.goals[-8:]
    return report
