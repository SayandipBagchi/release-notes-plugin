"""Deterministic tiering of a tracker item (tier_item). Takes no free text.

Release signals count only when they cite evidence stored for the run:
every fix_versions[] / deploy_refs[] entry needs an evidence_id whose stored record
comes from a tracker or deploy source, and status-based T1/T2 needs item.evidence_id
pointing at a tracker record. Anything else is ignored and reported.
"""
import re

from . import ToolError
from . import config as cfgmod
from . import paths
from .evidence import load_store
from .window import parse_dt

COMMS_SOURCES = {"outlook", "gmail", "slack", "teams", "email", "chat", "comms"}
TRACKER_SOURCES = {"jira", "linear", "ado"}
SIGNAL_SOURCES = TRACKER_SOURCES | {"jira_fixversion", "github_release", "gitlab_release"}
DEPLOY_KINDS = {"github_release", "gitlab_release", "jira_fixversion"}
SENSITIVE_RE = re.compile(r"security|cve|vuln", re.I)


def _in(value, tz, start, end, field):
    if value in (None, ""):
        return False
    try:
        dt = parse_dt(value, tz, field)
    except ToolError:
        return False
    return start <= dt < end


def _src(s):
    return str(s).split(":", 1)[0].strip().lower()


def _evidence_source(store, eid):
    rec = store.get(eid) if isinstance(eid, str) else None
    return str((rec or {}).get("source", "")).lower() if rec is not None else None


def tier_item(tenant, run_id, item, window_start, window_end) -> dict:
    if not isinstance(item, dict) or not isinstance(item.get("key"), str):
        raise ToolError("item must be an object with a string key")
    cfg = cfgmod.load_config(tenant)
    paths.check_run_id(run_id)
    store = load_store(tenant, run_id)
    tz = cfgmod.tenant_tz(cfg)
    ws, we = parse_dt(window_start, tz, "window_start"), parse_dt(window_end, tz, "window_end")
    if ws >= we:
        raise ToolError("window_start must be before window_end")
    key = item["key"]
    rd = cfg.get("releaseDefinition") or {}
    primary = rd.get("primary")
    if primary not in ("fixversion_released", "deploy_tag", "done_in_window"):
        raise ToolError(f"tenant releaseDefinition.primary is invalid: {primary!r}")
    done = {str(s).casefold() for s in rd.get("doneStatuses") or []}
    labels = [str(x) for x in item.get("labels") or []]
    excl = {str(x).casefold() for x in ((cfg.get("sources") or {}).get("tracker") or {}).get("exclude", {}).get("labels", [])}
    ignored = []

    def out(tier, section, reason):
        return {"key": key, "tier": tier, "section": section, "reason": reason, "ignored": ignored}

    def check(entry, field, idx):
        eid = entry.get("evidence_id")
        src = _evidence_source(store, eid)
        if not eid:
            why = "no evidence_id"
        elif src is None:
            why = f"evidence_id {eid!r} not in this run's evidence store"
        elif src not in SIGNAL_SOURCES:
            why = f"evidence source {src!r} is not a tracker or deploy source"
        elif field == "deploy_refs" and entry.get("kind") not in DEPLOY_KINDS:
            why = f"deploy kind {entry.get('kind')!r} is not one of {sorted(DEPLOY_KINDS)}"
        else:
            return True
        ignored.append({"field": field, "index": idx,
                        "ref": entry.get("name") if field == "fix_versions" else entry.get("tag"), "reason": why})
        return False

    fvs = [(i, fv) for i, fv in enumerate(item.get("fix_versions") or []) if isinstance(fv, dict)]
    drs = [(i, d) for i, d in enumerate(item.get("deploy_refs") or []) if isinstance(d, dict)]
    fvs = [fv for i, fv in fvs if check(fv, "fix_versions", i)]
    drs = [d for i, d in drs if check(d, "deploy_refs", i)]

    tracker_src = _evidence_source(store, item.get("evidence_id"))
    status_ok = tracker_src in TRACKER_SOURCES
    if not status_ok and (item.get("status") or item.get("status_changed_at")):
        ignored.append({"field": "status", "index": None, "ref": item.get("evidence_id"),
                        "reason": "status needs item.evidence_id pointing at a tracker record in this run"})

    hit = [l for l in labels if l.casefold() in excl]
    if hit:
        return out("none", "excluded", f"label {hit[0]!r} is in tracker.exclude.labels")
    if cfg.get("audience") == "external":
        hit = [l for l in labels if SENSITIVE_RE.search(l)]
        if hit:
            return out("none", "excluded", f"external audience and label {hit[0]!r} is security-sensitive")

    status = str(item.get("status") or "")
    status_done = status_ok and status.casefold() in done
    status_in = status_ok and _in(item.get("status_changed_at"), tz, ws, we, "status_changed_at")

    if primary == "fixversion_released":
        for fv in fvs:
            if fv.get("released") is True and _in(fv.get("release_date"), tz, ws, we, "release_date"):
                return out("T1", "released", f"fix version {fv.get('name')!r} released {fv.get('release_date')} in window")
    elif primary == "deploy_tag":
        for d in drs:
            if _in(d.get("date"), tz, ws, we, "deploy date"):
                return out("T1", "released", f"deploy {d.get('kind')} {d.get('tag')!r} on {d.get('date')} in window")
    elif status_done and status_in:
        return out("T1", "released", f"status {status!r} reached in window")

    if primary != "done_in_window" and status_done and status_in:
        return out("T2", "pending", f"status {status!r} reached in window but no release signal in window")

    comms = sorted({_src(s) for s in item.get("evidence_sources") or [] if _src(s) in COMMS_SOURCES})
    if comms:
        return out("T3", "mentioned", f"no tracker or deploy signal in window; mentioned in {', '.join(comms)}")
    return out("none", "out_of_window", "no tracker, deploy or comms signal in window")
