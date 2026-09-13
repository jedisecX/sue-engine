#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.equations import LIBRARY, bridge, find, recall_lines
from sue.parse import parse
from sue.personality import Personality


class EquationTests(unittest.TestCase):
    def test_find_uncertainty(self):
        hits = find("heisenberg uncertainty")
        self.assertTrue(hits)
        self.assertEqual(hits[0].id, "heisenberg")

    def test_eq_ask(self):
        p = parse("talk about the schrodinger wavefunction", Personality().stop)
        self.assertTrue(p.features.get("eq_ask"))

    def test_bridge_not_a_law(self):
        by_id = {e.id: e for e in LIBRARY}
        note = bridge(by_id["entropy"], by_id["shannon"])
        self.assertTrue(note)

    def test_engine_stores_eq_trace(self):
        with tempfile.TemporaryDirectory() as td:
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=2)
            reply = s.respond("what is the uncertainty principle")
            self.assertTrue(reply)
            self.assertTrue(any(t.kind == "eq" for t in s.memory.traces))
            self.assertTrue(s.respond("recall that conversation"))

    def test_recall_lines(self):
        lines = recall_lines("cronbach alpha reliability")
        self.assertTrue(lines)
