"""Evidence store, completeness checks and ticket-key extraction."""
import hashlib
import json
import re

from . import ToolError
from . import paths

RECORD_KEYS = ("source", "native_id", "url", "title", "timestamp", "author", "excerpt", "fields")
NOT_TICKET_PREFIXES = {
    "UTF", "ISO", "SHA", "MD", "CVE", "CWE", "GHSA", "RFC", "IEC", "IEEE", "AES", "RSA",
    "TLS", "SSL", "HTTP", "ECMA", "IPV", "PCI", "WCAG", "FIPS", "ECDSA", "HMAC", "CRC",
}
GENERIC_KEY_RE = re.compile(r"(?<![A-Za-z0-9_-])([A-Z][A-Z0-9]{1,9})-(\d+)\b")
PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")


def completeness_check(source, fetched, reported_total=None) -> dict:
    if not isinstance(fetched, int) or isinstance(fetched, bool) or fetched < 0:
        raise ToolError("fetched must be a non-negative integer")
    out = {"source": source, "fetched": fetched, "reported_total": reported_total}
    if reported_total is None:
        out["status"] = "unknown"
        out["note"] = "source did not report a total; completeness cannot be proven"
        return out
    if not isinstance(reported_total, int) or isinstance(reported_total, bool) or reported_total < 0:
        raise ToolError("reported_total must be a non-negative integer or null")
    if fetched == reported_total:
        out["status"] = "complete"
    elif fetched < reported_total:
        out["status"] = "partial"
        out["note"] = f"{reported_total - fetched} records not fetched"
    else:
        out["status"] = "partial"
        out["note"] = "fetched exceeds reported total; duplicates or a moving result set"
    return out


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def evidence_id(record: dict) -> str:
    h = hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()[:8]
    return f"{record['source']}:{record['native_id']}:{h}"


def _store(tenant, run_id):
    return paths.run_dir(tenant, run_id) / "evidence.jsonl"


def load_store(tenant, run_id) -> dict:
    paths.tenant_dir(tenant)
    out = {}
    for row in paths.read_jsonl(_store(tenant, run_id)):
        if isinstance(row, dict) and "id" in row:
            out[row["id"]] = row.get("record")
    return out


def evidence_put(tenant, run_id, records) -> dict:
    paths.tenant_dir(tenant)
    paths.check_run_id(run_id)
    if not isinstance(records, list):
        raise ToolError("records must be a list")
    prepared = []
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            raise ToolError(f"records[{i}] must be an object")
        for k in ("source", "native_id"):
            if not isinstance(r.get(k), str) or not r[k].strip():
                raise ToolError(f"records[{i}].{k} must be a non-empty string")
        if ":" in r["source"]:
            raise ToolError(f"records[{i}].source must not contain ':'")
        if "fields" in r and r["fields"] is not None and not isinstance(r["fields"], dict):
            raise ToolError(f"records[{i}].fields must be an object")
        prepared.append(r)
    existing = load_store(tenant, run_id)
    ids, new = [], []
    for r in prepared:
        rid = evidence_id(r)
        ids.append(rid)
        if rid not in existing:
            existing[rid] = r
            new.append({"id": rid, "record": r})
    if new:
        paths.append_jsonl(_store(tenant, run_id), new)
    return {"ids": ids}


def evidence_get(tenant, run_id, ids) -> dict:
    if not isinstance(ids, list):
        raise ToolError("ids must be a list")
    store = load_store(tenant, run_id)
    recs, missing = {}, []
    for i in ids:
        if i in store:
            recs[i] = store[i]
        elif i not in missing:
            missing.append(i)
    return {"records": recs, "missing": missing}


def extract_ticket_keys(text, project_keys=None) -> dict:
    if not isinstance(text, str):
        raise ToolError("text must be a string")
    if project_keys:
        for k in project_keys:
            if not isinstance(k, str) or not PROJECT_KEY_RE.match(k):
                raise ToolError(f"invalid project key {k!r}")
        alt = "|".join(re.escape(k) for k in sorted(project_keys, key=len, reverse=True))
        rx = re.compile(r"(?<![A-Za-z0-9_-])(" + alt + r")-(\d+)\b")
        allowed = None
    else:
        rx = GENERIC_KEY_RE
        allowed = NOT_TICKET_PREFIXES
    seen, out = set(), []
    for m in rx.finditer(text):
        prefix = m.group(1)
        if allowed is not None and prefix in allowed:
            continue
        # A trailing "-<digit>" means an identifier like XYZ-2026-1234, not a ticket key.
        if re.match(r"-\d", text[m.end():m.end() + 2]):
            continue
        key = m.group(0)
        if key in seen:
            continue
        seen.add(key)
        out.append({"key": key, "start": m.start(), "end": m.end()})
    return {"keys": out}
