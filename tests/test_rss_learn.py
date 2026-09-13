#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.ingest import FeedSpec, ingest
from sue.lexicon import default_lexicon


class BankTests(unittest.TestCase):
    def test_five_thousand(self):
        lex = default_lexicon()
        self.assertGreaterEqual(lex.size()["classified"], 5000)
        self.assertIn("bridge", lex.related("river"))

    def test_dictionary_covers_bank(self):
        lex = default_lexicon()
        self.assertIn("flowing", lex.define("river"))
        self.assertTrue(lex.define("bridge"))
        sample = [w for w in list(lex.klass)[200:240] if len(w) >= 4]
        hits = sum(1 for w in sample if lex.define(w))
        self.assertGreaterEqual(hits, 20)


class RssLearnTests(unittest.TestCase):
    def test_ingest_teaches_lexicon(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        with tempfile.TemporaryDirectory() as td:
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=2)
            ingest(
                s.memory,
                [FeedSpec(url=str(fixture), tag="wire")],
                fetch=lambda u: Path(u).read_text(encoding="utf-8"),
                state=s.state,
                lexicon=s.personality.lexicon,
            )
            news = [t for t in s.memory.traces if t.kind == "news"]
            self.assertTrue(news)
            self.assertTrue(
                s.personality.lexicon.knows("river")
                or s.personality.lexicon.knows("lantern")
            )
            s.state.topic = "river"
            reply = s.respond("any news about the river")
            low = reply.lower()
            self.assertTrue(
                "wire" in low or "river" in low or "bridge" in low or "water" in low
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
