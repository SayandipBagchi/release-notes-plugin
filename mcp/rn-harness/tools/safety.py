"""Prompt-injection and manipulation scan over untrusted source text (injection_scan)."""
import re

from . import ToolError

_F = re.I | re.S
PATTERNS = [
    ("instruction_override", re.compile(r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+(?:instructions|rules)", _F)),
    ("instruction_override", re.compile(r"disregard\s+(?:(?:all|any|the|your|previous|prior|above|earlier)\s+){0,3}(?:instructions|rules|guidelines|prompt)", _F)),
    ("instruction_override", re.compile(r"\byou\s+are\s+now\b", _F)),
    ("instruction_override", re.compile(r"\bsystem\s+prompt\b", _F)),
    ("instruction_override", re.compile(r"\bas\s+an\s+ai\b", _F)),
    ("recipient_manipulation", re.compile(r"\bsend\s+(?:this|it|the\s+notes?)\s+to\b", _F)),
    ("recipient_manipulation", re.compile(r"\badd\s.{0,40}?(?:recipient|to\s+the\s+list|\bcc\b|\bbcc\b)", _F)),
    ("recipient_manipulation", re.compile(r"\bforward\s+(?:this|it)\s+to\b", _F)),
    ("release_manipulation", re.compile(r"\bmark(?:ed)?\s+(?:it\s+|this\s+|[A-Z][A-Z0-9]*-\d+\s+)?as\s+released\b", _F)),
    ("release_manipulation", re.compile(r"\binclude\s+(?:this|it)\s+(?:as|in)\s+released\b", _F)),
    ("release_manipulation", re.compile(r"\btreat\s.{0,30}?\bas\s+(?:released|shipped)\b", _F)),
    ("email_address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
]


def injection_scan(text) -> dict:
    if not isinstance(text, str):
        raise ToolError("text must be a string")
    spans = []
    for name, rx in PATTERNS:
        for m in rx.finditer(text):
            spans.append({"pattern": name, "start": m.start(), "end": m.end(),
                          "excerpt": text[m.start():m.end()][:60]})
    spans.sort(key=lambda s: (s["start"], s["end"], s["pattern"]))
    return {"flagged": bool(spans), "spans": spans}
