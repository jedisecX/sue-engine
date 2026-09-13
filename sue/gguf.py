"""Optional 2B GGUF realizer.

Sue still runs with ComposeRealizer if llama-cpp-python or the
.gguf file is missing. Personality, memory, and state stay the same.
Only the last sentence assembly is swapped.
"""

from __future__ import annotations

import os
from pathlib import Path

from .generate import ComposeRealizer
from .parse import Parsed
from .personality import Personality
from .reasoning import Thought
from .state import State


def default_gguf() -> Path | None:
    raw = os.environ.get("SUE_GGUF", "").strip()
    if raw:
        p = Path(raw).expanduser()
        return p if p.is_file() else None
    here = Path(__file__).resolve().parent.parent
    for cand in here.glob("*.gguf"):
        return cand
    models = here / "models"
    if models.is_dir():
        found = list(models.glob("*.gguf"))
        if found:
            return found[0]
    return None


def _prompt(thought: Thought, parsed: Parsed, state: State) -> str:
    mats = ", ".join(thought.materials[:8])
    mem = "; ".join(m.text[:80] for m in thought.memories[:3])
    return (
        "You are Sue, a small terminal creature. Short sentences. No lists.\n"
        f"intent={thought.intent} topic={thought.topic} "
        f"mood warmth={state.warmth:.2f} curiosity={state.curiosity:.2f} "
        f"play={state.play:.2f} confidence={state.confidence:.2f}\n"
        f"materials: {mats}\n"
        f"memory: {mem}\n"
        f"user: {parsed.raw}\n"
        "sue:"
    )


class GgufRealizer:
    def __init__(self, personality: Personality, rng, path: Path, n_ctx: int = 2048):
        from llama_cpp import Llama

        self.p = personality
        self.rng = rng
        self.path = path
        self.fallback = ComposeRealizer(personality, rng)
        self.llm = Llama(
            model_path=str(path),
            n_ctx=n_ctx,
            n_threads=max(1, (os.cpu_count() or 2) // 2),
            verbose=False,
        )

    def thought_summary(self, thought: Thought) -> str:
        return self.fallback.thought_summary(thought) + " · gguf"

    def realize(self, thought: Thought, parsed: Parsed, state: State) -> str:
        if thought.intent == "code" or parsed.features.get("code_ask"):
            return self.fallback.realize(thought, parsed, state)
        if parsed.features.get("eq_ask") or parsed.features.get("program_ask"):
            return self.fallback.realize(thought, parsed, state)
        try:
            out = self.llm(
                _prompt(thought, parsed, state),
                max_tokens=96,
                temperature=0.35 + 0.45 * state.play,
                top_p=0.9,
                stop=["\nuser:", "\nyou ·", "\nYou:"],
            )
            text = (out["choices"][0]["text"] or "").strip()
            text = " ".join(text.split())
            if not text:
                return self.fallback.realize(thought, parsed, state)
            return text[:400]
        except Exception:
            return self.fallback.realize(thought, parsed, state)


def attach(personality: Personality, rng, path: Path | None = None):
    gguf = path or default_gguf()
    if gguf is None:
        return ComposeRealizer(personality, rng), None
    try:
        return GgufRealizer(personality, rng, gguf), gguf
    except Exception:
        return ComposeRealizer(personality, rng), None
