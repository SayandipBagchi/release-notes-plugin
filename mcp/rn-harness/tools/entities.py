"""Entity ledger and diff, used to prove a rewrite kept every fact (entity_ledger, entity_diff).

Extraction order: urls, dates, ticket keys, versions, numbers. Each match is masked
before the next category runs, so nothing is counted twice.
A dotted number is a version when it has a 'v' prefix, three parts, a pre-release
suffix, or follows a release word (version, release, build, sdk, api, app, ios,
android, firmware); otherwise it is a decimal number.
"""
import re

from . import ToolError
from .evidence import extract_ticket_keys

CATS = ("ticket_keys", "versions", "dates", "numbers", "urls")
_MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
URL_RE = re.compile(r"https?://\S+")
DATE_RES = [
    re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)"),
    re.compile(r"(?<![\w])\d{1,2}\s+" + _MON + r"\s+\d{4}(?!\d)", re.I),
    re.compile(r"(?<![\w])" + _MON + r"\s+\d{1,2},?\s+\d{4}(?!\d)", re.I),
    re.compile(r"(?<![\w/])\d{1,2}/\d{1,2}/\d{4}(?![\d/])"),
]
VERSION_RE = re.compile(r"(?<![\w.])(v)?(\d+\.\d+)(\.\d+)?(-[A-Za-z0-9][\w.]*)?(?![\w]|\.\d)", re.I)
VERSION_CTX_RE = re.compile(r"(?:version|ver\.?|release|build|sdk|api|app|ios|android|firmware)\s*$", re.I)
NUMBER_RE = re.compile(r"(?<![\w.:/])\d+(?:,\d{3})*(?:\.\d+)?%?(?![\w:]|\.\d)")


def _mask(text, s, e):
    return text[:s] + " " * (e - s) + text[e:]


def entity_ledger(text, project_keys=None) -> dict:
    if not isinstance(text, str):
        raise ToolError("text must be a string")
    found = {c: set() for c in CATS}
    work = text
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?)]}'\">")
        found["urls"].add(u)
        work = _mask(work, m.start(), m.start() + len(u))
    for rx in DATE_RES:
        for m in rx.finditer(work):
            found["dates"].add(" ".join(m.group(0).split()))
            work = _mask(work, m.start(), m.end())
    for k in extract_ticket_keys(work, project_keys or None)["keys"]:
        found["ticket_keys"].add(k["key"])
    # mask every occurrence of each key, not only the first
    for key in found["ticket_keys"]:
        for m in re.finditer(r"(?<![A-Za-z0-9_-])" + re.escape(key) + r"\b", work):
            work = _mask(work, m.start(), m.end())
    for m in VERSION_RE.finditer(work):
        v, three, suffix = m.group(1), m.group(3), m.group(4)
        ctx = VERSION_CTX_RE.search(work[max(0, m.start() - 12):m.start()])
        if v or three or suffix or ctx:
            found["versions"].add(m.group(0))
            work = _mask(work, m.start(), m.end())
    for m in NUMBER_RE.finditer(work):
        found["numbers"].add(m.group(0))
    return {c: sorted(found[c]) for c in CATS}


def entity_diff(before, after, project_keys=None) -> dict:
    a = entity_ledger(before, project_keys)
    b = entity_ledger(after, project_keys)
    added, removed = {}, {}
    for c in CATS:
        add = sorted(set(b[c]) - set(a[c]))
        rem = sorted(set(a[c]) - set(b[c]))
        if add:
            added[c] = add
        if rem:
            removed[c] = rem
    return {"equal": not added and not removed, "added": added, "removed": removed}
