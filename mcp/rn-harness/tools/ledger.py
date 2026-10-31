"""Release ledger (CSV), carry-over, run log and clean-run counting."""
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from . import ToolError
from . import paths

COLUMNS = ["window_start", "window_end", "run_id", "item_key", "title", "tier", "section",
           "status", "evidence_ids", "message_id", "carried_from"]
SECTIONS = {"released", "pending", "mentioned", "excluded", "out_of_window"}
TIERS = {"T1", "T2", "T3", "none", ""}
STATUSES = {"drafted", "sent", "held", "dropped", "carried"}
RUN_STATUSES = {"drafted", "sent", "held", "sent:unverified"}
FAIL_GATES = {"model", "tenant", "window", "source_unreachable", "draft", "review", "send"}
SECTION_TIER = {"released": "T1", "pending": "T2", "mentioned": "T3"}


def run_status_ok(s) -> bool:
    if s in RUN_STATUSES:
        return True
    return isinstance(s, str) and s.startswith("failed:") and s[len("failed:"):] in FAIL_GATES
_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _ledger_path(tenant):
    return paths.tenant_dir(tenant) / "release-ledger.csv"


def _cell(v):
    s = "" if v is None else str(v)
    return "'" + s if s.startswith(_FORMULA) else s


def _uncell(s):
    return s[1:] if s.startswith("'") and s[1:2] in _FORMULA and s[1:2] != "" else s


def ledger_append(tenant, rows) -> dict:
    if not isinstance(rows, list):
        raise ToolError("rows must be a list")
    out = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise ToolError(f"rows[{i}] must be an object")
        unknown = set(r) - set(COLUMNS)
        if unknown:
            raise ToolError(f"rows[{i}] has unknown columns {sorted(unknown)}")
        for k in ("window_start", "window_end", "run_id", "item_key", "section", "status"):
            if not isinstance(r.get(k), str) or not r[k].strip():
                raise ToolError(f"rows[{i}].{k} is required")
        paths.check_run_id(r["run_id"])
        if r["section"] not in SECTIONS:
            raise ToolError(f"rows[{i}].section must be one of {sorted(SECTIONS)}")
        if r["status"] not in STATUSES:
            raise ToolError(f"rows[{i}].status must be one of {sorted(STATUSES)}")
        if r.get("tier", "") not in TIERS:
            raise ToolError(f"rows[{i}].tier must be one of T1, T2, T3, none")
        need = SECTION_TIER.get(r["section"])
        if need and r.get("tier") != need:
            raise ToolError(f"rows[{i}]: section {r['section']} requires tier {need}, got {r.get('tier')!r}")
        ev = r.get("evidence_ids") or []
        if isinstance(ev, str):
            ev = [x for x in ev.split(";") if x]
        if not isinstance(ev, list) or not all(isinstance(x, str) and ";" not in x for x in ev):
            raise ToolError(f"rows[{i}].evidence_ids must be a list of ids")
        row = {c: _cell(r.get(c)) for c in COLUMNS}
        row["evidence_ids"] = ";".join(ev)
        out.append(row)
    p = _ledger_path(tenant)
    new = not p.is_file() or p.stat().st_size == 0
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    if new:
        w.writeheader()
    w.writerows(out)
    with p.open("a", encoding="utf-8", newline="") as fh:
        fh.write(buf.getvalue())
    return {"appended": len(out)}


def read_ledger(tenant) -> list:
    p = _ledger_path(tenant)
    if not p.is_file():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return [{k: _uncell(v or "") for k, v in row.items()} for row in csv.DictReader(fh)]


def _ts(s):
    try:
        x = s.strip()
        if x.endswith("Z"):
            x = x[:-1] + "+00:00"
        d = datetime.fromisoformat(x)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def ledger_carry_over(tenant) -> dict:
    rows = read_ledger(tenant)
    sent = [(i, r) for i, r in enumerate(rows) if r.get("status") == "sent" and _ts(r.get("window_end", ""))]
    if not sent:
        return {"items": []}
    latest = max(sent, key=lambda x: (_ts(x[1]["window_end"]), x[0]))[1]
    win = (latest["window_start"], latest["window_end"])
    items, seen = [], set()
    for i, r in enumerate(rows):
        if (r["window_start"], r["window_end"]) != win or r["section"] != "pending" or r["status"] != "sent":
            continue
        key = r["item_key"]
        if key in seen:
            continue
        later_released = any(x["item_key"] == key and x["section"] == "released"
                             and x["status"] == "sent" for x in rows[i + 1:])
        if later_released:
            continue
        seen.add(key)
        items.append({"item_key": key, "title": r.get("title", ""), "from_window_start": r["window_start"]})
    return {"items": items}


def run_log_append(tenant, record) -> dict:
    if not isinstance(record, dict):
        raise ToolError("record must be an object")
    for k in ("run_id", "model"):
        if not isinstance(record.get(k), str) or not record[k].strip():
            raise ToolError(f"record.{k} is required")
    paths.check_run_id(record["run_id"])
    if not run_status_ok(record.get("status")):
        raise ToolError("record.status must be drafted, sent, held, sent:unverified or failed:<gate> with gate in "
                        + ", ".join(sorted(FAIL_GATES)))
    for k in ("edits", "held_count", "recipients_count"):
        if k in record and (not isinstance(record[k], int) or isinstance(record[k], bool) or record[k] < 0):
            raise ToolError(f"record.{k} must be a non-negative integer")
    for k in ("approver", "message_id"):
        if k in record and record[k] is not None and not isinstance(record[k], str):
            raise ToolError(f"record.{k} must be a string")
    if "sources" in record:
        src = record["sources"]
        if not isinstance(src, list):
            raise ToolError("record.sources must be a list")
        for j, x in enumerate(src):
            if not isinstance(x, dict) or not isinstance(x.get("source"), str) \
                    or x.get("status") not in ("complete", "partial", "unknown"):
                raise ToolError(f"record.sources[{j}] needs source and status complete|partial|unknown")
            for k in ("fetched", "reported_total"):
                v = x.get(k)
                if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
                    raise ToolError(f"record.sources[{j}].{k} must be a non-negative integer or null")
    rec = dict(record)
    rec["logged_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    paths.append_jsonl(paths.runs_dir(tenant) / "run_log.jsonl", [rec])
    return {"ok": True}


def clean_run_count_at(folder: Path) -> int:
    """Count trailing clean runs. Each run counts once, by its last record; runs whose
    last record is still 'drafted' (in progress) are skipped."""
    recs = paths.read_jsonl(Path(folder) / "runs" / "run_log.jsonl")
    last = {}
    for r in recs:
        if isinstance(r, dict) and r.get("run_id"):
            last.pop(r["run_id"], None)
            last[r["run_id"]] = r
    n = 0
    for r in reversed(list(last.values())):
        if r.get("status") == "drafted":
            continue
        if r.get("status") == "sent" and r.get("edits") == 0 and not isinstance(r.get("edits"), bool):
            n += 1
        else:
            break
    return n


def clean_run_count(tenant) -> dict:
    return {"count": clean_run_count_at(paths.tenant_dir(tenant))}
