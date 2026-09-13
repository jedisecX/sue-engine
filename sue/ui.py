"""Terminal surface. Commands are not the personality."""

from __future__ import annotations

import sys
from pathlib import Path

from .engine import Sue

HELP = """commands
  /state     public state summary
  /memory    recent traces
  /forget          wipe traces, name, goals
  /forget news     drop only news traces
  /feeds           list configured RSS sources
  /ingest          pull feeds into memory (needs feeds.json)
  /news            list stored feed traces
  /reset           new session, keep long-term memory
  /summary         toggle short thought tag
  /help
  /quit
talk in ordinary sentences. commands are plumbing, not her voice.
"""


def _tty() -> bool:
    return sys.stdout.isatty()


def c(code: str, text: str) -> str:
    if not _tty():
        return text
    return f"{code}{text}\033[0m"


PINK = "\033[95m"
GRAY = "\033[90m"
DIM = "\033[2m"
BOLD = "\033[1m"


def banner(sue: Sue) -> None:
    face = "( · ·)"
    print()
    print(c(PINK + BOLD, f"  {face}  sue"))
    print(c(GRAY, "  " + sue.startup_line()))
    print(c(DIM, "  /help for rails. /quit to fold."))
    print()


def handle_command(sue: Sue, line: str) -> bool:
    cmd = line.strip().lower()
    if cmd in {"/quit", "/exit", "/bye"}:
        print(c(GRAY, "sue · folded into files."))
        try:
            sue.persist()
        except OSError as e:
            print(c(GRAY, f"(could not save: {e})"))
        return False
    if cmd in {"/help", "/?"}:
        print(HELP)
        return True
    if cmd == "/state":
        st = sue.inspect_state()
        for k, v in st.items():
            print(c(GRAY, f"  {k:14} {v}"))
        return True
    if cmd == "/memory":
        rows = sue.inspect_memory()
        if not rows:
            print(c(GRAY, "  (empty drawer)"))
            return True
        for r in rows:
            print(c(GRAY, f"  [{r['id']}:{r['kind']}|{r['importance']}] {r['text']}"))
        return True
    if cmd.startswith("/forget"):
        parts = line.strip().split()
        if len(parts) > 1:
            kind = parts[1].lower()
            n = sue.forget(kind)
            print(c(GRAY, f"  dropped {n} {kind} traces."))
        else:
            sue.forget()
            print(c(GRAY, "  traces cleared."))
        return True
    if cmd == "/feeds":
        from .ingest import load_feeds
        path = sue.memory.path.with_name("feeds.json")
        feeds = load_feeds(path)
        if not feeds:
            print(c(GRAY, f"  no feeds. copy feeds.example.json to {path.name}"))
            return True
        for f in feeds:
            print(c(GRAY, f"  {f.tag:12} {f.max_items:2}  {f.url}"))
        return True
    if cmd == "/news":
        rows = sue.inspect_news()
        if not rows:
            print(c(GRAY, "  (no news traces. /ingest after feeds.json)"))
            return True
        for r in rows:
            print(c(GRAY, f"  [{r['id']}|{r['importance']}] {r['text']}"))
        if sue.state.wire:
            print(c(GRAY, "  wire: " + " | ".join(sue.state.wire[-5:])))
        return True
    if cmd == "/ingest":
        report, feeds = sue.ingest_feeds()
        if not feeds:
            print(c(GRAY, "  no feeds.json beside the memory file."))
            return True
        err = f"  errors: {len(report.errors)}" if report.errors else ""
        print(c(GRAY, f"  ingested {report.stored}  skipped {report.skipped}  feeds {report.fetched}/{report.feeds}{err}"))
        for e in (report.errors or [])[:4]:
            print(c(GRAY, f"  ! {e}"))
        return True
    if cmd == "/reset":
        sue.reset_session()
        print(c(GRAY, f"  session {sue.state.session}. long-term traces kept."))
        return True
    if cmd == "/summary":
        sue.show_summary = not sue.show_summary
        print(c(GRAY, f"  thought tags {'on' if sue.show_summary else 'off'}."))
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
            reply = sue.respond(raw)
        except Exception as e:
            print(c(GRAY, f"  (engine hitch: {e}) i am still here."))
            continue
        speak(sue, reply)
    return 0
