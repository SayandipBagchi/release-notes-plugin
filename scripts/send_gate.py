#!/usr/bin/env python3
"""PreToolUse hook: block any outbound send that the harness has not prepared.

Only enforces while a release-notes run is active (tenants/*/runs/active-run.json, written by
run_start) or a send is pending; otherwise it allows, so unrelated messages are never blocked.

Reads the hook JSON from stdin. Tool names are matched case-insensitively (re.search)
against the send patterns; non-matching tools, and this plugin's own harness tools,
pass silently. A matching tool is allowed only when exactly one unexpired, unused
tenants/*/runs/pending-send.json covers every extracted recipient, the body in the
call has the prepared body_sha256, the subject matches (email), and:
  mode "send":    its approval is valid and its idempotency key is unused;
  mode "preview": recipients are only the tenant preview target.
On allow, used_at is written so the pending send cannot be used twice.
Anything else, including any exception, is denied (exit 2).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parents[1])
sys.path.insert(0, str(PLUGIN_ROOT / "mcp" / "rn-harness"))

DEFAULT_PATTERNS = ["send", "reply", "forward", "post_?message", "chat_?message", "channel_?message", "publish"]
# Own harness tools (prepare_send, record_send, ...) and the agent-to-agent message tool are not outbound sends.
EXEMPT_RE = re.compile(r"(^|__)(plugin_[^_]*release-notes[^_]*_)?rn[-_]harness__|^SendMessage$")
BODY_KEYS = ["body", "text", "content", "message", "html", "markdown"]
SUBJECT_KEYS = ("subject", "title")
RECIPIENT_KEYS = {"to", "cc", "bcc", "recipients", "torecipients", "ccrecipients"}
CHANNEL_KEYS = {"channel", "channel_id", "chat_id"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def load_patterns():
    try:
        s = json.loads((PLUGIN_ROOT / "settings.json").read_text(encoding="utf-8"))
        pats = s["release-notes"]["sendGate"]["toolPatterns"]
        if isinstance(pats, list) and pats and all(isinstance(p, str) for p in pats):
            return pats
    except Exception:
        pass
    return DEFAULT_PATTERNS


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)


def extract_recipients(tool_name, tool_input):
    lname = tool_name.lower()
    prefix = "slack:" if "slack" in lname else "teams:" if "teams" in lname else "channel:"
    out = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                lk = str(k).lower()
                if lk in RECIPIENT_KEYS:
                    for s in _strings(v):
                        out.update(e.lower() for e in EMAIL_RE.findall(s))
                elif lk in CHANNEL_KEYS:
                    for s in _strings(v):
                        s = s.strip()
                        if s:
                            out.add(s if re.match(r"^(slack|teams):", s, re.I) else prefix + s)
                else:
                    walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(tool_input)
    return out


def extract_body(node, depth=0):
    if depth > 6:
        return None
    if isinstance(node, str):
        return node if node.strip() else None
    if isinstance(node, dict):
        for k in ["content", "text"] + BODY_KEYS:
            if k in node:
                b = extract_body(node[k], depth + 1)
                if b:
                    return b
    return None


def extract_subject(node, depth=0):
    if depth > 6 or not isinstance(node, dict):
        return None
    for k in SUBJECT_KEYS:
        if isinstance(node.get(k), str):
            return node[k]
    for v in node.values():
        if isinstance(v, dict):
            r = extract_subject(v, depth + 1)
            if r is not None:
                return r
    return None


def _norm(r):
    r = r.strip()
    if "@" in r and ":" not in r:
        return r.lower()
    if ":" in r:
        p, rest = r.split(":", 1)
        return p.lower() + ":" + rest
    return r


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    print(f"release-notes send gate: {reason}", file=sys.stderr)
    sys.exit(2)


def decide(tool_name, tool_input):
    """Return None to allow, or a deny reason."""
    from tools import paths, send
    from tools import config as cfgmod

    root = paths.tenants_dir()
    now = datetime.now(timezone.utc)
    live, used = [], 0
    for pf in sorted(root.glob("*/runs/pending-send.json")):
        try:
            p = json.loads(pf.read_text(encoding="utf-8"))
            exp = datetime.fromisoformat(str(p["expires_at"]).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if exp <= now:
            continue
        if p.get("used_at"):
            used += 1
            continue
        live.append((pf, p))
    if not live and not used and not send.any_run_active(root):
        return None  # no release-notes run in progress: not this plugin's send, do not interfere
    if not live:
        if used:
            return "approved send already used; call record_send"
        return "no approved send is pending (prepare_send or prepare_preview first, or the pending send expired)"
    extracted = extract_recipients(tool_name, tool_input)
    if not extracted:
        return "could not read any recipient from the send call"
    covering = [(f, p) for f, p in live if extracted <= {_norm(r) for r in p.get("recipients") or []}]
    if not covering:
        return f"recipients {sorted(extracted)} are not all in a pending send"
    if len(covering) > 1:
        return "more than one pending send covers these recipients; refusing an ambiguous send"
    pf, p = covering[0]
    tenant = pf.parents[1].name
    if p.get("tenant") not in (None, tenant):
        return "pending send names a different tenant than its folder"

    body = None
    if isinstance(tool_input, dict):
        for k in BODY_KEYS:
            body = extract_body(tool_input.get(k))
            if body:
                break
    if not body:
        return "could not read the message body from the send call"
    if not p.get("body_sha256") or send.body_sha256(body) != p["body_sha256"]:
        return "message body differs from the approved draft"
    if p.get("channel") == "email":
        subj = extract_subject(tool_input)
        if subj is not None and subj.strip() != str(p.get("subject") or "").strip():
            return "subject differs from the prepared send"

    mode = p.get("mode", "send")
    if mode == "preview":
        target = send.preview_target(cfgmod.load_config(tenant))
        if not target or extracted != {_norm(target)}:
            return "a preview may only go to the tenant preview target"
    elif mode == "send":
        ac = send.approval_check(tenant, p.get("run_id"), p.get("run_hash"))
        if not ac["valid"]:
            return f"approval invalid: {ac['reason']}"
        if send.key_used(tenant, p.get("idempotency_key"))[0]:
            return "this window was already sent"
    else:
        return f"unknown pending mode {mode!r}"

    p["used_at"] = now.isoformat().replace("+00:00", "Z")
    paths.write_json(pf, p)
    return None


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
        tool_name = str(data.get("tool_name") or "")
    except Exception as e:
        deny(f"unreadable hook input ({e}); failing closed")
        return
    try:
        if EXEMPT_RE.search(tool_name):
            sys.exit(0)
        if not any(re.search(p, tool_name, re.IGNORECASE) for p in load_patterns()):
            sys.exit(0)
    except re.error as e:
        deny(f"bad sendGate pattern ({e}); failing closed")
    try:
        reason = decide(tool_name, data.get("tool_input") or {})
    except SystemExit:
        raise
    except Exception as e:
        reason = f"gate error ({type(e).__name__}: {e}); failing closed"
    if reason:
        deny(reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
