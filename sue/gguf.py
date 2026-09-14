"""Optional 2B GGUF realizer. Default file: ~/models/2b.gguf"""
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
    candidates: list[Path] = []
    if raw:
        candidates.append(Path(raw).expanduser())
    home = Path.home()
    candidates.append(home / "models" / "2b.gguf")
    candidates.append(home / "models" / "2B.gguf")
    here = Path(__file__).resolve().parent.parent
    candidates.append(here / "models" / "2b.gguf")
    candidates.extend(sorted(here.glob("*.gguf")))
    models = here / "models"
    if models.is_dir():
        candidates.extend(sorted(models.glob("*.gguf")))
    seen: set[Path] = set()
    for p in candidates:
        try:
            p = p.expanduser().resolve()
        except OSError:
            continue
        if p in seen:
            continue
        seen.add(p)
        if p.is_file():
            return p
    return None

def _prompt(thought: Thought, parsed: Parsed, state: State) -> str:
    mats = ", ".join(thought.materials[:8])
    mem = "; ".join(m.text[:80] for m in thought.memories[:3])
    return (
        "You are Sue, a small terminal creature. Short sentences. No lists.\n"
        f"intent={thought.intent} topic={thought.topic} "
        f"mood warmth={state.warmth:.2f} curiosity={state.curiosity:.2f} "
        f"play={state.play:.2f} confidence={state.confidence:.2f}\n"
        f"materials: {mats}\nmemory: {mem}\nuser: {parsed.raw}\nsue:"
    )

class GgufRealizer:
    def __init__(self, personality: Personality, rng, path: Path, n_ctx: int = 2048):
        from llama_cpp import Llama
        self.p = personality
        self.rng = rng
        self.path = path
        self.fallback = ComposeRealizer(personality, rng)
        self.llm = Llama(model_path=str(path), n_ctx=n_ctx, n_threads=max(1, (os.cpu_count() or 2) // 2), verbose=False)
    def thought_summary(self, thought: Thought) -> str:
        return self.fallback.thought_summary(thought) + " · gguf"
    def realize(self, thought: Thought, parsed: Parsed, state: State) -> str:
        if thought.intent == "code" or parsed.features.get("code_ask"):
            return self.fallback.realize(thought, parsed, state)
        if parsed.features.get("eq_ask") or parsed.features.get("program_ask"):
            return self.fallback.realize(thought, parsed, state)
        try:
            out = self.llm(_prompt(thought, parsed, state), max_tokens=96, temperature=0.35 + 0.45 * state.play, top_p=0.9, stop=["\nuser:", "\nyou ·", "\nYou:"])
            text = " ".join((out["choices"][0]["text"] or "").split())
            return text[:400] if text else self.fallback.realize(thought, parsed, state)
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
