"""
Parses config.md — a markdown file with KEY=VALUE pairs inside fenced code blocks.
Returns a flat dict of all key/value pairs found across all code blocks.
"""

import re
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.md"

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_KV_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def load(path: Path = _CONFIG_PATH) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for block in _FENCE_RE.finditer(text):
        for line in block.group(1).splitlines():
            line = line.strip()
            m = _KV_RE.match(line)
            if m:
                val = m.group(2)
                # strip inline # comments
                if " #" in val:
                    val = val[: val.index(" #")]
                result[m.group(1)] = val.strip()
    return result


def get_urls(cfg: dict[str, str], prefix: str) -> list[str]:
    """Return all non-empty values for keys matching PREFIX_1, PREFIX_2, …"""
    urls = []
    i = 1
    while True:
        val = cfg.get(f"{prefix}_{i}", "").strip()
        if val:
            urls.append(val)
        elif f"{prefix}_{i}" not in cfg:
            break
        i += 1
    return urls
