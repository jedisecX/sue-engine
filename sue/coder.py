"""Stdlib coding library + compositional script writer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MODULES = {
    "argparse": "command-line flags and help text",
    "json": "read and write JSON",
    "pathlib": "paths without string glue",
    "urllib.request": "HTTP GET with stdlib",
    "xml.etree.ElementTree": "parse XML / RSS",
    "csv": "read and write tables",
    "hashlib": "checksums",
    "datetime": "clocks and stamps",
    "re": "patterns",
    "sys": "argv and exit",
    "logging": "trace output",
    "collections": "counters and deques",
    "subprocess": "run other programs",
    "http.server": "tiny local HTTP",
    "sqlite3": "local SQL",
    "zipfile": "archives",
    "shutil": "copy and remove trees",
    "unittest": "tests",
}


@dataclass
class Job:
    kind: str
    title: str
    tokens: list[str]
    modules: list[str]


def classify(text: str) -> Job:
    raw = text.lower()
    tokens = [t for t in raw.replace("/", " ").split() if t.isalpha()]

    def has(*words: str) -> bool:
        return any(w in raw for w in words)

    if has("rss", "feed", "atom", "xml"):
        return Job("rss", "fetch and parse an rss/atom feed", tokens, ["urllib.request", "xml.etree.ElementTree"])
    if has("json"):
        return Job("json", "read or write json", tokens, ["json", "pathlib"])
    if has("hash", "md5", "sha", "checksum"):
        return Job("hash", "checksum a file", tokens, ["hashlib", "pathlib"])
    if has("list", "directory", "folder", "walk") and has("file", "dir", "folder", "path", "directory"):
        return Job("listdir", "list files in a folder", tokens, ["pathlib"])
    if has("http", "url", "download", "fetch"):
        return Job("http", "http get a url", tokens, ["urllib.request"])
    return Job("cli", "small argparse tool", tokens, ["argparse", "pathlib", "sys"])


def compose(job: Job) -> str:
    builders = {"rss": _rss, "json": _json, "hash": _hash, "listdir": _listdir, "http": _http, "cli": _cli}
    body = builders.get(job.kind, _cli)(job)
    return (
        "#!/usr/bin/env python3\n"
        f'"""{job.title}.\n\nComposed by Sue from the stdlib coding library.\n'
        f"Modules: {', '.join(job.modules)}\n"
        '"""\n\n'
        + body
    )


def _rss(job: Job) -> str:
    return (
        "from __future__ import annotations\n\n"
        "import sys\nimport urllib.request\nimport xml.etree.ElementTree as ET\n\n"
        "def fetch(url, timeout=8.0):\n"
        "    req = urllib.request.Request(url, headers={'User-Agent': 'SueScript/1.0'})\n"
        "    with urllib.request.urlopen(req, timeout=timeout) as resp:\n"
        "        return resp.read().decode('utf-8', errors='replace')\n\n"
        "def titles(xml_text):\n"
        "    root = ET.fromstring(xml_text)\n"
        "    return [n.text.strip() for n in root.iter() if n.tag.lower().endswith('title') and n.text]\n\n"
        "def main():\n"
        "    url = sys.argv[1] if len(sys.argv) > 1 else 'https://example.com/feed.xml'\n"
        "    for line in titles(fetch(url))[:20]:\n"
        "        print(line)\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def _json(job: Job) -> str:
    return (
        "from pathlib import Path\nimport json, sys\n\n"
        "def main():\n"
        "    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('data.json')\n"
        "    if path.exists():\n"
        "        print(json.dumps(json.loads(path.read_text(encoding='utf-8')), indent=2))\n"
        "        return 0\n"
        "    path.write_text('{\"ok\": true}\n', encoding='utf-8')\n"
        "    print(f'wrote {path}')\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def _hash(job: Job) -> str:
    return (
        "from pathlib import Path\nimport hashlib, sys\n\n"
        "def main():\n"
        "    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__)\n"
        "    data = path.read_bytes()\n"
        "    print('md5', hashlib.md5(data).hexdigest())\n"
        "    print('sha256', hashlib.sha256(data).hexdigest())\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def _listdir(job: Job) -> str:
    return (
        "from pathlib import Path\nimport sys\n\n"
        "def main():\n"
        "    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')\n"
        "    for p in sorted(root.iterdir()):\n"
        "        print(p.name + ('/' if p.is_dir() else ''))\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def _http(job: Job) -> str:
    return (
        "import sys, urllib.request\n\n"
        "def main():\n"
        "    url = sys.argv[1] if len(sys.argv) > 1 else 'https://example.com'\n"
        "    req = urllib.request.Request(url, headers={'User-Agent': 'SueScript/1.0'})\n"
        "    with urllib.request.urlopen(req, timeout=8) as resp:\n"
        "        print(resp.read(2000).decode('utf-8', errors='replace'))\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def _cli(job: Job) -> str:
    return (
        "import argparse\nfrom pathlib import Path\n\n"
        "def main():\n"
        "    p = argparse.ArgumentParser(description='sue script')\n"
        "    p.add_argument('path', nargs='?', default='.')\n"
        "    args = p.parse_args()\n"
        "    print(Path(args.path).resolve())\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    )


def write_script(source: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(source, encoding="utf-8")
    dest.chmod(dest.stat().st_mode | 0o111)
    return dest


def describe(name: str) -> str:
    key = name.lower().strip()
    if key in MODULES:
        return f"{key}: {MODULES[key]}"
    hits = [f"{k}: {v}" for k, v in MODULES.items() if key in k or key in v]
    return hits[0] if hits else ""
