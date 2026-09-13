#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.engine import Sue
from sue.generate import ComposeRealizer
from sue.gguf import attach


class GgufHookTests(unittest.TestCase):
    def test_missing_file_falls_back(self):
        from sue.personality import Personality
        import random
        r, path = attach(Personality(), random.Random(1), path=Path("/no/such/model.gguf"))
        self.assertIsInstance(r, ComposeRealizer)
        self.assertIsNone(path)

    def test_engine_wakes_without_llama(self):
        with tempfile.TemporaryDirectory() as td:
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=1)
            self.assertTrue(s.respond("hello river"))
            self.assertTrue(hasattr(s, "gguf_path"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
