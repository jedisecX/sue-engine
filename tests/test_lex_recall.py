#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.parse import parse
from sue.personality import Personality


class LexRecallTests(unittest.TestCase):
    def test_word_ask_feature(self):
        p = parse("what does bayou mean", Personality().stop)
        self.assertTrue(p.features.get("word_ask"))

    def test_learn_writes_lex_trace(self):
        with tempfile.TemporaryDirectory() as td:
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=4)
            s.respond("the green bayou sits by the river")
            lex = [t for t in s.memory.traces if t.kind == "lex"]
            self.assertTrue(lex)
            self.assertTrue(any("bayou" in t.text for t in lex))

    def test_lex_survives_session(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sue_memory.json"
            a = Sue(memory_path=path, seed=4)
            a.respond("the green bayou sits by the river")
            b = Sue(memory_path=path, seed=5)
            self.assertTrue(any(t.kind == "lex" for t in b.memory.traces))
            info = b.inspect_lexicon("bayou")
            self.assertTrue(info.get("known"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
