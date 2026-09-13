"""Terminal surface. Commands are not the personality."""

from __future__ import annotations

import sys
from pathlib import Path

from .engine import Sue

HELP = """commands
  /state /memory /forget /feeds /ingest /news
lexicon
  /lexicon              menu + bank size
  /lexicon [word]       class, gloss, neighbors
  /define [word]        gloss only
  /lexicon chat         words from this talk
code
  /lib [module]         stdlib cards
  /script save [name.py]
session
  /reset /summary /help /quit
"""

LEX_MENU = """lexicon menu
  /lexicon              this menu + dictionary size
  /lexicon [word]       class, gloss, neighbors
  /define [word]        gloss only
  /lexicon chat         words pulled from this talk
  /forget lex           drop learned-word traces
"""

PINK, GRAY, DIM, BOLD = "\033[95m", "\033[90m", "\033[2m", "\033[1m"


def _tty() -> bool:
    return sys.stdout.isatty()


def c(code: str, text: str) -> str:
    return text if not _tty() else f"{code}{text}\033[0m"


def banner(sue: Sue) -> None:
    print()
    print(c(PINK + BOLD, "  ( · ·)  sue"))
    print(c(GRAY, "  " + sue.startup_line()))
    print(c(DIM, "  /help  /lexicon  /news  /lib  ·  /quit to fold."))
    print()


def _lexicon_menu(sue: Sue, line: str) -> bool:
    parts = line.strip().split()
    verb = parts[0].lower() if parts else "/lexicon"
    arg = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
    if verb == "/define" and not arg:
        print(c(GRAY, "  usage: /define river"))
        return True
    if arg.lower() in {"help", "menu", "?"}:
        print(c(GRAY, LEX_MENU))
        return True
    show_chat = arg.lower() == "chat"
    lookup = None if (not arg or show_chat) else arg
    if verb == "/define" and lookup:
        gloss = sue.personality.lexicon.define(lookup) if hasattr(sue.personality.lexicon, "define") else ""
        print(c(GRAY, f"  {lookup}: {gloss or '(no gloss yet)'}"))
        return True
    try:
        info = sue.inspect_lexicon(lookup)
    except Exception as e:
        print(c(GRAY, f"  lexicon hitch: {e}"))
        print(c(GRAY, LEX_MENU))
        return True
    if lookup:
        flag = "known" if info.get("known") else "unknown"
        print(c(GRAY, f"  {info.get('query')}  [{info.get('class') or '-'}] {flag}"))
        gloss = info.get("gloss") or ""
        if hasattr(sue.personality.lexicon, "define") and not gloss:
            gloss = sue.personality.lexicon.define(lookup)
        print(c(GRAY, f"  gloss: {gloss or '(none)'}"))
        print(c(GRAY, "  neighbors: " + (", ".join(info.get("neighbors") or []) or "(none yet)")))
        return True
    sz = info.get("size") or {}
    print(c(GRAY, LEX_MENU))
    print(c(GRAY, f"  bank  nodes {sz.get('nodes')}  classed {sz.get('classified')}  learned {sz.get('learned', 0)}"))
    if info.get("just_acquired"):
        print(c(GRAY, "  just acquired: " + ", ".join(info["just_acquired"])))
    rows = info.get("from_chat") or []
    if show_chat or rows:
        print(c(GRAY, "  from chat:" if rows else "  from chat: (empty)"))
        for r in rows[:16]:
            print(c(GRAY, f"    {r.get('word')}  {r.get('class')}"))
    return True


def handle_command(sue: Sue, line: str) -> bool:
    cmd = line.strip().lower()
    if cmd in {"/quit", "/exit", "/bye"}:
        try:
            sue.persist()
        except OSError:
            pass
        print(c(GRAY, "sue · folded into files."))
        return False
    if cmd in {"/help", "/?"}:
        print(HELP)
        return True
    if cmd == "/state":
        for k, v in sue.inspect_state().items():
            print(c(GRAY, f"  {k:14} {v}"))
        return True
    if cmd == "/memory":
        rows = sue.inspect_memory()
        print(c(GRAY, "  (empty drawer)" if not rows else ""))
        for r in rows:
            print(c(GRAY, f"  [{r['id']}:{r['kind']}] {r['text']}"))
        return True
    if cmd.startswith("/forget"):
        parts = line.strip().split()
        kind = parts[1].lower() if len(parts) > 1 else None
        n = sue.forget(kind)
        print(c(GRAY, f"  dropped {n if kind else 'all'}."))
        return True
    if cmd == "/feeds":
        from .ingest import load_feeds
        feeds = load_feeds(sue.memory.path.with_name("feeds.json"))
        if not feeds:
            print(c(GRAY, "  no feeds.json"))
            return True
        for f in feeds:
            print(c(GRAY, f"  {f.tag}  {f.url}"))
        return True
    if cmd == "/news":
        rows = sue.inspect_news()
        if not rows:
            print(c(GRAY, "  (no news traces)"))
            return True
        for r in rows:
            print(c(GRAY, f"  {r['text']}"))
        return True
    if cmd.split()[0] in {"/lex", "/lexicon", "/dict", "/dictionary", "/define"}:
        return _lexicon_menu(sue, line)
    if cmd.split()[0] in {"/lib", "/stdlib"}:
        from .coder import MODULES, describe
        parts = line.strip().split(maxsplit=1)
        if len(parts) > 1:
            print(c(GRAY, "  " + (describe(parts[1]) or "not in the stdlib card")))
            return True
        for k in list(MODULES)[:18]:
            print(c(GRAY, f"  {k:22} {MODULES[k]}"))
        return True
    if cmd.startswith("/script"):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] in {"save", "write"} and hasattr(sue, "write_last_script"):
            path = sue.write_last_script(parts[2] if len(parts) > 2 else "sue_script.py")
            print(c(GRAY, f"  wrote {path}"))
            return True
        print(getattr(sue, "last_script", None) or c(GRAY, "  no draft yet."))
        return True
    if cmd == "/ingest":
        report, feeds = sue.ingest_feeds()
        if not feeds:
            print(c(GRAY, "  no feeds.json"))
            return True
        print(c(GRAY, f"  ingested {report.stored} skipped {report.skipped} learned {getattr(report,'learned',0)}"))
        return True
    if cmd == "/reset":
        sue.reset_session()
        print(c(GRAY, f"  session {sue.state.session}"))
        return True
    if cmd == "/summary":
        sue.show_summary = not sue.show_summary
        return True
    print(c(GRAY, "  unknown command. /help"))
    return True


def speak(sue: Sue, text: str) -> None:
    tag = ""
    if sue.show_summary and sue.last_thought:
        tag = c(DIM, "  [" + sue.realizer.thought_summary(sue.last_thought) + "]") + "\n"
    print(tag + c(PINK, "sue") + c(GRAY, " · ") + text)


def loop(memory_path: Path | None = None) -> int:
    try:
        sue = Sue(memory_path=memory_path)
    except Exception as e:
        print(f"sue failed to wake: {e}", file=sys.stderr)
        return 1
    banner(sue)
    while True:
        try:
            raw = input(c(GRAY, "you · "))
        except (EOFError, KeyboardInterrupt):
            print()
            handle_command(sue, "/quit")
            return 0
        line = raw.strip()
        if line.startswith("/"):
            try:
                if not handle_command(sue, line):
                    return 0
            except Exception as e:
                print(c(GRAY, f"  command error: {e}"))
            continue
        try:
            speak(sue, sue.respond(raw))
        except Exception as e:
            print(c(GRAY, f"  (engine hitch: {e}) i am still here."))
    return 0
