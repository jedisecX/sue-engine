#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.ingest import FeedSpec, ingest, parse_feed


def _sue(td: str, seed: int = 7) -> Sue:
    return Sue(memory_path=Path(td) / "sue_memory.json", seed=seed)


class IngestTests(unittest.TestCase):
    def test_parse_and_store_from_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        xml = fixture.read_text(encoding="utf-8")
        items = parse_feed(xml, "wire")
        self.assertGreaterEqual(len(items), 2)
        self.assertTrue(any("River" in i.title for i in items))
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            spec = FeedSpec(url=str(fixture), tag="wire", max_items=8)
            fetch = lambda u: Path(u).read_text(encoding="utf-8")
            r1 = ingest(s.memory, [spec], fetch=fetch, state=s.state)
            self.assertEqual(r1.stored, 2)
            r2 = ingest(s.memory, [spec], fetch=fetch, state=s.state)
            self.assertEqual(r2.stored, 0)
            self.assertGreater(r2.skipped, 0)
            news = [t for t in s.memory.traces if t.kind == "news"]
            self.assertEqual(len(news), 2)

    def test_relevance_can_hit_news(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.state.topic = "bridge"
            ingest(
                s.memory,
                [FeedSpec(url=str(fixture), tag="wire")],
                fetch=lambda u: Path(u).read_text(encoding="utf-8"),
                state=s.state,
            )
            hit = s.memory.retrieve(["river", "bridge"], k=3)
            self.assertTrue(any(t.kind == "news" for t in hit))

    def test_forget_news_only(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("the green door stays shut")
            ingest(
                s.memory,
                [FeedSpec(url=str(fixture), tag="wire")],
                fetch=lambda u: Path(u).read_text(encoding="utf-8"),
            )
            n = s.forget("news")
            self.assertGreater(n, 0)
            self.assertTrue(any("green door" in t.text for t in s.memory.traces))
            self.assertFalse(any(t.kind == "news" for t in s.memory.traces))

    def test_bad_xml_is_empty_not_crash(self):
        self.assertEqual(parse_feed("<<<not xml", "x"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
