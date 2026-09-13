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


def _sue(td: str, seed: int = 11) -> Sue:
    return Sue(memory_path=Path(td) / "sue_memory.json", seed=seed)


class RecallTests(unittest.TestCase):
    def test_recall_uses_news_on_news_ask(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            ingest(
                s.memory,
                [FeedSpec(url=str(fixture), tag="wire")],
                fetch=lambda u: Path(u).read_text(encoding="utf-8"),
                state=s.state,
            )
            self.assertTrue(s.state.wire)
            reply = s.respond("any news about the river and the bridge")
            self.assertTrue(reply)
            intents = {th.intent for th in s.last_candidates}
            self.assertIn("recall", intents)

    def test_forget_news_clears_wire(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_rss.xml"
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            ingest(
                s.memory,
                [FeedSpec(url=str(fixture), tag="wire")],
                fetch=lambda u: Path(u).read_text(encoding="utf-8"),
                state=s.state,
            )
            s.forget("news")
            self.assertEqual(s.state.wire, [])
            self.assertEqual(s.inspect_news(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
