#!/usr/bin/env python3
"""Launch Sue from the terminal."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sue.ui import loop

def main() -> int:
    root = Path(__file__).resolve().parent
    return loop(memory_path=root / "sue_memory.json")

if __name__ == "__main__":
    raise SystemExit(main())
