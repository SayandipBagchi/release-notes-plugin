"""Citations, recipients, run hash, approval tokens, idempotency and the send gate files."""
import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

from . import ToolError
from . import config as cfgmod
from . import paths
from .evidence import load_store
from .window import parse_dt

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PENDING_TTL = timedelta(minutes=30)


def _now():
    return datetime.now(timezone.utc)


def _utc_iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def citation_resolve(tenant, run_id, lines) -> dict:
    if not isinstance(lines, dict):
        raise ToolError("lines must be an object of line_id -> [evidence_ids]")
    store = load_store(tenant, paths.check_run_id(run_id))
    uncited, unknown, links = [], [], {}
    for line_id, ids in lines.items():
        if not isinstance(ids, list) or not ids:
            uncited.append(line_id)
            continue
        for i in ids:
            if i in store:
                links[i] = (store[i] or {}).get("url")
            elif i not in unknown:
                unknown.append(i)
    return {"ok": not uncited and not unknown, "uncited": uncited, "unknown_ids": unknown, "links": links}


def validate_recipients(tenant, recipients) -> dict:
    cfg = cfgmod.load_config(tenant)
    if not isinstance(recipients, list):
        raise ToolError("recipients must be a list")
    allowed = {cfgmod.norm_recipient(r) for r in cfg.get("recipients") or [] if isinstance(r, str)}
    rejected = [r for r in recipients if not isinstance(r, str) or cfgmod.norm_recipient(r) not in allowed]
    return {"ok": bool(recipients) and not rejected, "rejected": rejected}


def hash_run(draft_text, recipients, subject) -> dict:
    if not isinstance(draft_text, str) or not isinstance(subject, str) or not isinstance(recipients, list):
        raise ToolError("draft_text and subject must be strings, recipients a list")
    canon = {"draft": draft_text,
             "recipients": sorted(str(r).strip().lower() for r in recipients),
             "subject": subject}
    s = json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"run_hash": hashlib.sha256(s.encode("utf-8")).hexdigest()}


def normalise_body(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in t.split("\n")).strip()


def body_sha256(text: str) -> str:
    return hashlib.sha256(normalise_body(text).encode("utf-8")).hexdigest()


def _approval_path(tenant, run_id):
    return paths.run_dir(tenant, run_id) / "approval.json"


def approval_issue(tenant, run_id, run_hash, approver, quote) -> dict:
    from .ledger import clean_run_count
    cfg = cfgmod.load_config(tenant)
    p = _approval_path(tenant, run_id)
    owner = ((cfg.get("owner") or {}).get("email") or "").strip().lower()
    if not isinstance(run_hash, str) or not HASH_RE.match(run_hash):
        return {"ok": False, "token": None, "reason": "run_hash must be a sha256 hex digest"}
    if not owner or not isinstance(approver, str) or approver.strip().lower() != owner:
        return {"ok": False, "token": None, "reason": "approver is not the tenant owner"}
    if not isinstance(quote, str) or len(quote.split()) < 3:
        return {"ok": False, "token": None, "reason": "quote must be the owner's own words (at least 3 words)"}
    if quote.strip().lower().startswith("auto-send"):
        a = cfg.get("autoSend") or {}
        earned = a.get("earnedAfterCleanRuns")
        clean = clean_run_count(tenant)["count"]
        if a.get("enabled") is not True:
            return {"ok": False, "token": None, "reason": "auto-send approval but autoSend.enabled is not true"}
        if not isinstance(earned, int) or clean < earned:
            return {"ok": False, "token": None,
                    "reason": f"auto-send not earned: {clean} clean runs, need {earned}"}
    if p.is_file():
        try:
            prev = paths.read_json(p)
        except (json.JSONDecodeError, OSError):
            prev = {}
        if prev.get("consumed_at"):
            return {"ok": False, "token": None, "reason": "this run was already sent; start a new run"}
    token = uuid.uuid4().hex
    paths.write_json(p, {"token": token, "run_hash": run_hash, "approver": approver.strip(),
                         "quote": quote, "issued_at": _utc_iso(_now())})
    return {"ok": True, "token": token}


def approval_check(tenant, run_id, run_hash) -> dict:
    cfg = cfgmod.load_config(tenant)
    p = _approval_path(tenant, run_id)
    if not p.is_file():
        return {"valid": False, "reason": "no approval for this run"}
    try:
        a = paths.read_json(p)
    except (json.JSONDecodeError, OSError):
        return {"valid": False, "reason": "approval file is unreadable"}
    if a.get("consumed_at"):
        return {"valid": False, "reason": "approval already consumed"}
    if a.get("run_hash") != run_hash:
        return {"valid": False, "reason": "run hash does not match the approved draft"}
    owner = ((cfg.get("owner") or {}).get("email") or "").strip().lower()
    if str(a.get("approver", "")).strip().lower() != owner:
        return {"valid": False, "reason": "approver is no longer the tenant owner"}
    return {"valid": True, "reason": "ok"}


VERSION_RE = re.compile(r"^v([1-9]\d*)$")


def version_number(version) -> int:
    m = VERSION_RE.match(version) if isinstance(version, str) else None
    if not m:
        raise ToolError(f"version must look like v1, v2, ...: {version!r}")
    return int(m.group(1))


def window_norm(tenant, window_start, window_end):
    cfg = cfgmod.load_config(tenant)
    tz = cfgmod.tenant_tz(cfg)
    return (parse_dt(window_start, tz, "window_start").isoformat(),
            parse_dt(window_end, tz, "window_end").isoformat())


def idempotency_key(tenant, window_start, window_end, version="v1") -> str:
    version_number(version)
    s, e = window_norm(tenant, window_start, window_end)
    return f"{tenant}|{s}|{e}|{version}"


def key_used(tenant, key):
    """Return (used, run_id)."""
    for rec in paths.read_jsonl(paths.runs_dir(tenant) / "sent.jsonl"):
        if rec.get("key") == key:
            return True, rec.get("run_id")
    return False, None


def idempotency_check(tenant, window_start, window_end, version="v1") -> dict:
    key = idempotency_key(tenant, window_start, window_end, version)
    used, by = key_used(tenant, key)
    return {"used": used, "by_run": by, "key": key}


def _pending_path(tenant):
    return paths.runs_dir(tenant) / "pending-send.json"


GATES = [f"G{i}" for i in range(9)]
GATE_VALUES = {"PASS", "FAIL", "NOT CHECKED", "REVERTED"}


def record_gates(tenant, run_id, gates, preview_delivered) -> dict:
    paths.tenant_dir(tenant)
    paths.check_run_id(run_id)
    if not isinstance(gates, dict):
        raise ToolError("gates must be an object of G0..G8 -> status")
    unknown = sorted(set(gates) - set(GATES))
    if unknown:
        raise ToolError(f"unknown gates: {unknown}")
    missing = [g for g in GATES if g not in gates]
    if missing:
        raise ToolError(f"missing gates: {missing}")
    for g, v in gates.items():
        if v not in GATE_VALUES:
            raise ToolError(f"gate {g} must be one of {sorted(GATE_VALUES)}")
        if v == "REVERTED" and g != "G6":
            raise ToolError(f"REVERTED is only valid for G6, not {g}")
    if not isinstance(preview_delivered, bool):
        raise ToolError("preview_delivered must be a boolean")
    paths.write_json(paths.run_dir(tenant, run_id) / "gates.json",
                     {"gates": {g: gates[g] for g in GATES}, "preview_delivered": preview_delivered,
                      "recorded_at": _utc_iso(_now())})
    passed = all(gates[g] == "PASS" or (g == "G6" and gates[g] == "REVERTED") for g in GATES)
    return {"ok": True, "all_pass": passed and preview_delivered}


def _gate_reasons(tenant, run_id):
    p = paths.run_dir(tenant, run_id) / "gates.json"
    if not p.is_file():
        return ["gates: not recorded (call record_gates)"]
    try:
        g = paths.read_json(p)
    except (json.JSONDecodeError, OSError):
        return ["gates: gates.json is unreadable"]
    out = []
    gates = g.get("gates") or {}
    for k in GATES:
        v = gates.get(k, "NOT CHECKED")
        if not (v == "PASS" or (k == "G6" and v == "REVERTED")):
            out.append(f"gate {k} is {v}")
    if g.get("preview_delivered") is not True:
        out.append("preview not delivered to the owner")
    return out


def _active_other(tenant, run_id):
    pp = _pending_path(tenant)
    if not pp.is_file():
        return None
    try:
        prev = paths.read_json(pp)
        exp = parse_dt(prev.get("expires_at"), timezone.utc)
    except (json.JSONDecodeError, OSError, ToolError):
        return None
    if prev.get("run_id") != run_id and exp > _now():
        return prev.get("run_id")
    return None


def prepare_send(tenant, run_id, run_hash, recipients, subject, channel, body,
                 window_start, window_end, version="v1") -> dict:
    cfg = cfgmod.load_config(tenant)
    paths.check_run_id(run_id)
    vn = version_number(version)
    reasons = []
    ac = approval_check(tenant, run_id, run_hash)
    if not ac["valid"]:
        reasons.append(f"approval: {ac['reason']}")
    rl = recipients if isinstance(recipients, list) else []
    vr = validate_recipients(tenant, rl)
    if not vr["ok"]:
        reasons.append("recipients: " + (f"not in tenant config: {vr['rejected']}" if vr["rejected"] else "empty"))
    if not isinstance(subject, str) or not subject.strip():
        reasons.append("subject is empty")
    if not isinstance(body, str) or not body.strip():
        reasons.append("body is empty")
    elif isinstance(subject, str) and hash_run(body, rl, subject)["run_hash"] != run_hash:
        reasons.append("body: hash_run(body, recipients, subject) does not match the approved run_hash")
    want = (cfg.get("delivery") or {}).get("channel")
    if channel != want:
        reasons.append(f"channel {channel!r} does not match delivery.channel {want!r}")
    reasons.extend(_gate_reasons(tenant, run_id))
    ic = idempotency_check(tenant, window_start, window_end, version)
    if ic["used"]:
        reasons.append(f"window already sent as {version} by run {ic['by_run']}")
    if vn > 1:
        prev = idempotency_check(tenant, window_start, window_end, f"v{vn - 1}")
        if not prev["used"]:
            reasons.append(f"correction {version} needs v{vn - 1} of this window in sent.jsonl")
    other = _active_other(tenant, run_id)
    if other:
        reasons.append(f"another send is pending for run {other}")
    if reasons:
        return {"ready": False, "reasons": reasons}
    now = _now()
    paths.write_json(_pending_path(tenant), {
        "tenant": tenant, "run_id": run_id, "run_hash": run_hash,
        "mode": "send", "recipients": list(rl), "subject": subject, "channel": channel,
        "body_sha256": body_sha256(body), "version": version,
        "idempotency_key": ic["key"], "created_at": _utc_iso(now),
        "expires_at": _utc_iso(now + PENDING_TTL),
    })
    return {"ready": True, "reasons": []}


def preview_target(cfg) -> str:
    o = cfg.get("owner") or {}
    t = o.get("previewTo") or o.get("email") or ""
    return cfgmod.norm_recipient(t) if isinstance(t, str) else ""


def _channel_of(recipient: str) -> str:
    if cfgmod.is_email(recipient):
        return "email"
    return recipient.split(":", 1)[0] if ":" in recipient else ""


def prepare_preview(tenant, run_id, subject, body, channel="email") -> dict:
    """Pending file for a draft preview to owner.previewTo (default owner.email). No approval needed."""
    cfg = cfgmod.load_config(tenant)
    paths.check_run_id(run_id)
    target = preview_target(cfg)
    reasons = []
    if not (cfgmod.is_email(target) or cfgmod.is_channel(target)):
        reasons.append("tenant owner.previewTo / owner.email is not a valid email or channel id")
    elif _channel_of(target) != channel:
        reasons.append(f"channel {channel!r} does not match preview target {target!r}")
    if not isinstance(subject, str) or not subject.strip():
        reasons.append("subject is empty")
    if not isinstance(body, str) or not body.strip():
        reasons.append("body is empty")
    if channel not in ("email", "slack", "teams"):
        reasons.append("channel must be email, slack or teams")
    other = _active_other(tenant, run_id)
    if other:
        reasons.append(f"another send is pending for run {other}")
    if reasons:
        return {"ready": False, "reasons": reasons}
    now = _now()
    paths.write_json(_pending_path(tenant), {
        "mode": "preview", "tenant": tenant, "run_id": run_id, "recipients": [target],
        "subject": subject, "channel": channel, "body_sha256": body_sha256(body),
        "created_at": _utc_iso(now), "expires_at": _utc_iso(now + PENDING_TTL),
    })
    return {"ready": True}


def record_send(tenant, run_id, message_id, recipients_read_back, subject_read_back,
                window_start=None, window_end=None, version="v1") -> dict:
    paths.tenant_dir(tenant)
    paths.check_run_id(run_id)
    pp = _pending_path(tenant)
    if not pp.is_file():
        return {"ok": False, "verified": False, "mismatches": ["no pending send for this tenant"]}
    pending = paths.read_json(pp)
    if pending.get("run_id") != run_id:
        return {"ok": False, "verified": False,
                "mismatches": [f"pending send belongs to run {pending.get('run_id')}"]}
    preview = pending.get("mode") == "preview"
    mismatches = []
    key = None
    if not preview:
        if window_start is None or window_end is None:
            raise ToolError("window_start and window_end are required to record a send")
        key = idempotency_key(tenant, window_start, window_end, version)
        if key != pending.get("idempotency_key"):
            mismatches.append("window or version differs from the prepared send")
    rb = {cfgmod.norm_recipient(r) for r in recipients_read_back or [] if isinstance(r, str)}
    pr = {cfgmod.norm_recipient(r) for r in pending.get("recipients") or []}
    if rb != pr:
        extra, miss = sorted(rb - pr), sorted(pr - rb)
        mismatches.append(f"recipients differ: extra={extra} missing={miss}")
    if pending.get("channel") == "email" and \
            (subject_read_back or "").strip() != (pending.get("subject") or "").strip():
        mismatches.append("subject differs from the prepared send")
    if preview:
        pp.unlink()
        return {"ok": True, "verified": not mismatches, "mismatches": mismatches, "mode": "preview"}
    s, e = window_norm(tenant, window_start, window_end)
    now = _now()
    paths.append_jsonl(paths.runs_dir(tenant) / "sent.jsonl", [{
        "key": key, "run_id": run_id, "message_id": message_id, "start": s, "end": e,
        "sent_at": _utc_iso(now), "verified": not mismatches,
    }])
    ap = _approval_path(tenant, run_id)
    if ap.is_file():
        a = paths.read_json(ap)
        a["consumed_at"] = _utc_iso(now)
        paths.write_json(ap, a)
    pp.unlink()
    return {"ok": True, "verified": not mismatches, "mismatches": mismatches}


# --- Active-run marker -------------------------------------------------------------------------
# The PreToolUse send gate only enforces while a release-notes run is active (or a send is
# pending), so the plugin never blocks a user's unrelated messages in other work.

ACTIVE_TTL_HOURS = 12


def _active_path(tenant):
    return paths.tenant_dir(tenant) / "runs" / "active-run.json"


def run_start(tenant, run_id) -> dict:
    paths.check_run_id(run_id)
    cfgmod.load_config(tenant)
    now = _now()
    rec = {"tenant": tenant, "run_id": run_id, "started_at": _utc_iso(now),
           "expires_at": _utc_iso(now + timedelta(hours=ACTIVE_TTL_HOURS))}
    paths.write_json(_active_path(tenant), rec)
    return {"ok": True, **rec}


def run_end(tenant, run_id) -> dict:
    paths.check_run_id(run_id)
    p = _active_path(tenant)
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("run_id") not in (None, run_id):
            return {"ok": False, "reason": f"active run is {cur.get('run_id')}, not {run_id}"}
        p.unlink()
    return {"ok": True}


def any_run_active(root=None) -> bool:
    root = root or paths.tenants_dir()
    now = _now()
    for f in root.glob("*/runs/active-run.json"):
        try:
            exp = parse_dt(json.loads(f.read_text(encoding="utf-8"))["expires_at"], timezone.utc)
            if exp > now:
                return True
        except Exception:
            return True  # unreadable marker: fail closed
    return False
