#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.lexicon import Lexicon, default_lexicon
from sue.personality import Personality


class LexiconTests(unittest.TestCase):
    def test_river_has_neighbors(self):
        lex = default_lexicon()
        rel = set(lex.related("river"))
        self.assertTrue({"bridge", "water", "flood"} & rel)
        self.assertEqual(lex.word_class("river"), "noun")

    def test_unknown_is_empty_not_crash(self):
        lex = default_lexicon()
        self.assertEqual(lex.related("xqzzy"), [])
        self.assertIsNone(lex.word_class("xqzzy"))

    def test_merge_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lex.json"
            p.write_text('{"neighbors": {"river": ["bayou"]}, "class": {"bayou": "noun"}}', encoding="utf-8")
            lex = Lexicon(extra=p)
            self.assertIn("bayou", lex.related("river"))
            self.assertEqual(lex.word_class("bayou"), "noun")

    def test_personality_uses_lexicon(self):
        p = Personality()
        self.assertIn("bridge", p.associates.get("river", ()))

    def test_learns_unknown_from_context(self):
        lex = Lexicon()
        got = lex.learn_context(["bayou", "river", "flood"])
        self.assertIn("bayou", got)
        self.assertTrue(lex.knows("bayou"))
        self.assertIn("river", lex.related("bayou"))

    def test_learn_persists(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "lexicon.json"
            a = Lexicon(extra=path)
            a.path = path
            a.learn_context(["bayou", "river"])
            a.save()
            b = Lexicon(extra=path)
            self.assertTrue(b.knows("bayou"))
            self.assertIn("river", b.related("bayou"))

    def test_engine_learns_on_respond(self):
        with tempfile.TemporaryDirectory() as td:
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=7)
            s.respond("the green bayou sits by the river")
            self.assertTrue(s.personality.lexicon.knows("bayou"))
            s2 = Sue(memory_path=Path(td) / "sue_memory.json", seed=7)
            self.assertTrue(s2.personality.lexicon.knows("bayou"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
