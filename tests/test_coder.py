#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sue.coder import classify, compose, write_script
from sue.engine import Sue
from sue.parse import parse
from sue.personality import Personality


class CoderTests(unittest.TestCase):
    def test_code_ask(self):
        p = parse("write a script that hashes a file", Personality().stop)
        self.assertTrue(p.features.get("code_ask"))

    def test_rss_job(self):
        job = classify("write a python script to fetch an rss feed")
        self.assertEqual(job.kind, "rss")
        src = compose(job)
        self.assertIn("xml.etree", src)
        self.assertIn("urllib.request", src)

    def test_write_and_engine(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "h.py"
            write_script(compose(classify("hash this file")), dest)
            self.assertTrue(dest.exists())
            s = Sue(memory_path=Path(td) / "sue_memory.json", seed=1)
            s.respond("write a script that lists a directory")
            self.assertTrue(s.last_script)
            path = s.write_last_script("list_dir.py")
            self.assertTrue(path.exists())
            self.assertIn("Path", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
