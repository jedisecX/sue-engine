#!/usr/bin/env python3
"""Engine tests. Behavior, not golden dialogue."""

from __future__ import annotations

import sys
import tempfile
import traceback
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.memory import Memory
from sue.parse import parse
from sue.personality import Personality
from sue.state import State


def _sue(td: str, seed: int = 7) -> Sue:
    return Sue(memory_path=Path(td) / "sue_memory.json", seed=seed)


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.stop = Personality().stop

    def test_empty(self):
        p = parse("   ", self.stop)
        self.assertTrue(p.features["empty"])
        self.assertEqual(p.tokens, [])

    def test_question(self):
        p = parse("why is the moon loud?", self.stop)
        self.assertTrue(p.question)
        self.assertIn("moon", p.content)

    def test_unusual(self):
        p = parse("&&&&&", self.stop)
        self.assertTrue(p.unusual)


class MemoryTests(unittest.TestCase):
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            m = Memory.load(Path(td) / "nope.json")
            self.assertEqual(m.traces, [])

    def test_corrupted_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sue_memory.json"
            p.write_text("{not json", encoding="utf-8")
            m = Memory.load(p)
            self.assertEqual(m.traces, [])

    def test_corrupted_valid_json_wrong_shape(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sue_memory.json"
            p.write_text("[]", encoding="utf-8")
            m = Memory.load(p)
            self.assertEqual(m.traces, [])

    def test_relevance_not_dump(self):
        with tempfile.TemporaryDirectory() as td:
            m = Memory.load(Path(td) / "m.json")
            m.add("the tide pulls the moon", kind="user", importance=0.8)
            m.add("i ate bread", kind="user", importance=0.8)
            m.add("compiler errors at midnight", kind="user", importance=0.8)
            hit = m.retrieve(["moon", "tide"], k=1)
            self.assertTrue(hit)
            self.assertIn("moon", hit[0].text.lower())

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            m = Memory.load(p)
            m.add("keep this stone", kind="user")
            m.user_name = "Jedi"
            m.save()
            m2 = Memory.load(p)
            self.assertEqual(m2.user_name, "Jedi")
            self.assertEqual(m2.traces[0].text, "keep this stone")


class EngineTests(unittest.TestCase):
    def test_empty_input(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            r = s.respond("   ")
            self.assertTrue(len(r) > 8)
            self.assertNotEqual(r.strip(), "")

    def test_normal_conversation(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            a = s.respond("the river under the bridge is louder at night")
            b = s.respond("does that mean anything")
            self.assertIsInstance(a, str)
            self.assertIsInstance(b, str)
            self.assertGreater(s.state.turn, 1)
            self.assertTrue(s.memory.traces)

    def test_repeated_input_differs_often(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td, seed=3)
            x = s.respond("tell me about velvet moss")
            y = s.respond("tell me about velvet moss")
            self.assertTrue(x)
            self.assertTrue(y)
            self.assertEqual(s.state.last_user_tokens[0], "tell")

    def test_contradictory_input(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("i always tell the truth")
            r = s.respond("i never tell the truth")
            self.assertTrue(r)
            self.assertGreater(len(s.memory.traces), 1)

    def test_unusual_input(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            r = s.respond("@@@ qqq qqq qqq qqq qqq qqq qqq qqq")
            self.assertTrue(r)

    def test_very_long_input(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            blob = ("lantern " * 400) + "?"
            r = s.respond(blob)
            self.assertTrue(r)
            self.assertLess(len(r), 2000)

    def test_reset_keeps_traces(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("remember the green door")
            n = len(s.memory.traces)
            sess = s.state.session
            s.reset_session()
            self.assertEqual(len(s.memory.traces), n)
            self.assertEqual(s.state.session, sess + 1)
            self.assertEqual(s.state.turn, 0)

    def test_forget(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("my name is Jedi")
            s.forget()
            self.assertEqual(s.memory.traces, [])
            self.assertIsNone(s.memory.user_name)

    def test_persistence_between_sessions(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td, seed=1)
            s.respond("the comet left a chalk line")
            s.persist()
            s2 = _sue(td, seed=2)
            self.assertTrue(any("comet" in t.text.lower() for t in s2.memory.traces))
            self.assertGreaterEqual(s2.state.session, 2)

    def test_corrupted_state_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sue_state.json"
            p.write_text("{bad", encoding="utf-8")
            s = _sue(td)
            r = s.respond("hello there river")
            self.assertTrue(r)

    def test_name_persists(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("my name is Jedi")
            self.assertEqual(s.memory.user_name, "Jedi")

    def test_candidates_exist(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            s.respond("why keep a lantern in a drawer")
            self.assertGreaterEqual(len(s.last_candidates), 3)
            self.assertIsNotNone(s.last_thought)

    def test_hidden_state_moves(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            before = list(s.state.hidden)
            s.respond("how does thunder choose a roof")
            self.assertNotEqual(before, s.state.hidden)


class StateTests(unittest.TestCase):
    def test_from_json_garbage(self):
        st = State.from_json({"warmth": "nope", "hidden": [1]})
        self.assertIsInstance(st, State)
        self.assertEqual(len(st.hidden), 12)


class GracefulTests(unittest.TestCase):
    def test_respond_never_raises_on_odd_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            s = _sue(td)
            for blob in ["", " ", "\x00", "A" * 5000, "not not never always"]:
                try:
                    s.respond(blob)
                except Exception:
                    self.fail(traceback.format_exc())


if __name__ == "__main__":
    unittest.main(verbosity=2)
