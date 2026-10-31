"""Apply a tenant's source include/exclude filters to fetched records (apply_filters).

Record values are read from the top level or from record["fields"]:
  subject  <- fields.subject | title          sender  <- fields.sender | author
  folder   <- fields.folder                    channel <- fields.channel
  labels   <- fields.labels                    creator <- fields.creator | author
  headers  <- fields.headers (object)
Excludes are checked first and win. Each non-empty include list must match
(any entry within a list; every list that is set). Subject entries are
case-insensitive regexes, or substrings when the entry is not a valid regex.
Sender/creator entries match the address case-insensitively; an entry starting
with "@" matches the domain.
"""
import re

from . import ToolError
from . import config as cfgmod

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+")


def _get(rec, *names):
    f = rec.get("fields") if isinstance(rec.get("fields"), dict) else {}
    for n in names:
        for src in (f, rec):
            v = src.get(n)
            if v not in (None, "", []):
                return v
    return None


def _subject_match(pattern, text):
    if not isinstance(text, str):
        return False
    try:
        return re.search(pattern, text, re.I) is not None
    except re.error:
        return pattern.casefold() in text.casefold()


def _person_match(entry, value):
    if not isinstance(value, str):
        return False
    found = EMAIL_RE.findall(value)
    cands = [x.casefold() for x in found] or [value.strip().casefold()]
    e = entry.strip().casefold()
    if e.startswith("@"):
        return any(c.endswith(e) for c in cands)
    return e in cands


def _eq_any(entries, values):
    vals = values if isinstance(values, list) else [values]
    vs = {str(v).casefold() for v in vals if v is not None}
    return any(str(e).casefold() in vs for e in entries)


def _dims(kind):
    if kind == "tracker":
        return {
            "labels": lambda r: _get(r, "labels") or [],
            "creators": lambda r: _get(r, "creator", "author"),
        }
    return {
        "subject": lambda r: _get(r, "subject", "title"),
        "senders": lambda r: _get(r, "sender", "author"),
        "folders": lambda r: _get(r, "folder"),
        "channels": lambda r: _get(r, "channel"),
    }


def _match(dim, entry, value):
    if dim == "subject":
        return _subject_match(entry, value)
    if dim in ("senders", "creators"):
        return _person_match(entry, value)
    return _eq_any([entry], value)


def apply_filters(tenant, source_kind, records) -> dict:
    cfg = cfgmod.load_config(tenant)
    srcs = cfg.get("sources") or {}
    if source_kind == "tracker":
        conf, kind = srcs.get("tracker") or {}, "tracker"
    else:
        m = re.match(r"^comms:(\d+)$", source_kind or "")
        comms = srcs.get("comms") or []
        if not m or int(m.group(1)) >= len(comms):
            raise ToolError(f"source_kind must be 'tracker' or 'comms:<index>' within sources.comms: {source_kind!r}")
        conf, kind = comms[int(m.group(1))], "comms"
    if not isinstance(records, list):
        raise ToolError("records must be a list")
    inc = conf.get("include") or {}
    exc = conf.get("exclude") or {}
    dims = _dims(kind)
    kept, kept_ids, dropped = [], [], []
    for i, r in enumerate(records):
        if not isinstance(r, dict) or not isinstance(r.get("native_id"), str):
            raise ToolError(f"records[{i}] must be an object with a string native_id")
        rule = None
        for dim, getter in dims.items():
            for entry in exc.get(dim) or []:
                if _match(dim, entry, getter(r)):
                    rule = f"exclude.{dim}: {entry}"
                    break
            if rule:
                break
        if not rule:
            for dim, getter in dims.items():
                entries = inc.get(dim) or []
                if entries and not any(_match(dim, e, getter(r)) for e in entries):
                    rule = f"include.{dim}: no match"
                    break
        if not rule and kind == "comms":
            hdrs = _get(r, "headers") or {}
            for hk, hv in (inc.get("headers") or {}).items():
                got = {str(k).casefold(): v for k, v in hdrs.items()}.get(str(hk).casefold()) \
                    if isinstance(hdrs, dict) else None
                if not isinstance(got, str) or str(hv).casefold() not in got.casefold():
                    rule = f"include.headers: {hk}"
                    break
        if rule:
            dropped.append({"native_id": r["native_id"], "rule": rule})
        else:
            kept.append(r)
            kept_ids.append(r["native_id"])
    return {"kept_ids": kept_ids, "kept": kept, "dropped": dropped}
