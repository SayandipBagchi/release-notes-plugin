#!/usr/bin/env python3
"""rn-harness: stdio MCP server (newline-delimited JSON-RPC 2.0). Standard library only.

Logs go to stderr only; stdout carries protocol messages.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import ToolError  # noqa: E402
from tools import config, entities, evidence, filters, ledger, mapping, safety, send, tiering, window  # noqa: E402

SERVER_INFO = {"name": "rn-harness", "version": "0.1.0"}
DEFAULT_PROTOCOL = "2025-06-18"

S = {"type": "string"}
SA = {"type": "array", "items": {"type": "string"}}
TENANT = {"type": "string", "description": "Tenant slug (folder name under tenants/)."}
RUN_ID = {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"}
ISO = {"type": "string", "description": "ISO 8601 date or datetime; naive values are read in the tenant tz."}
VERSION = {"type": "string", "pattern": "^v[1-9][0-9]*$", "default": "v1"}
BODY = {"type": "string", "description": "The exact text that will be sent."}


def obj(props, required=()):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


TOOLS = [
    ("validate_tenant", config.validate_tenant, "Validate a tenant config.json and its cross-field rules.",
     obj({"tenant": TENANT}, ["tenant"])),
    ("resolve_window", window.resolve_window,
     "Resolve the reporting window [start, end) in the tenant tz from cadence/anchor, or from explicit start+end; lists overlaps with sent windows.",
     obj({"tenant": TENANT, "now": ISO, "start": ISO, "end": ISO, "version": VERSION}, ["tenant"])),
    ("completeness_check", evidence.completeness_check,
     "Compare fetched count to the source-reported total: complete, partial or unknown.",
     obj({"source": S, "fetched": {"type": "integer", "minimum": 0},
          "reported_total": {"type": ["integer", "null"], "minimum": 0}}, ["source", "fetched", "reported_total"])),
    ("evidence_put", evidence.evidence_put,
     "Store evidence records for a run; returns content-addressed ids. Idempotent.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "records": {"type": "array", "items": {
         "type": "object", "required": ["source", "native_id"], "properties": {
             "source": S, "native_id": S, "url": S, "title": S, "timestamp": S, "author": S,
             "excerpt": S, "fields": {"type": "object"}}}}}, ["tenant", "run_id", "records"])),
    ("evidence_get", evidence.evidence_get, "Fetch evidence records by id for a run.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "ids": SA}, ["tenant", "run_id", "ids"])),
    ("extract_ticket_keys", evidence.extract_ticket_keys,
     "Extract unique ticket keys (e.g. ACME-123) with offsets; optionally only given project prefixes.",
     obj({"text": S, "project_keys": SA}, ["text"])),
    ("tier_item", tiering.tier_item,
     "Assign tier T1/T2/T3/none and section to a tracker item from structured fields only. Release signals and "
     "status count only when they cite evidence_ids stored for the run from tracker/deploy sources; others are "
     "listed in ignored.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "item": {"type": "object", "required": ["key"], "properties": {
         "key": S, "evidence_id": S, "status": S, "status_changed_at": S, "labels": SA,
         "fix_versions": {"type": "array", "items": {"type": "object", "required": ["evidence_id"], "properties": {
             "name": S, "released": {"type": "boolean"}, "release_date": S, "evidence_id": S}}},
         "deploy_refs": {"type": "array", "items": {"type": "object", "required": ["kind", "evidence_id"], "properties": {
             "kind": {"type": "string", "enum": sorted(tiering.DEPLOY_KINDS)}, "tag": S, "date": S, "evidence_id": S}}},
         "evidence_sources": SA}},
         "window_start": ISO, "window_end": ISO}, ["tenant", "run_id", "item", "window_start", "window_end"])),
    ("apply_filters", filters.apply_filters,
     "Apply the tenant include/exclude filters for 'tracker' or 'comms:<index>' to records; excludes win.",
     obj({"tenant": TENANT, "source_kind": {"type": "string", "pattern": "^(tracker|comms:[0-9]+)$"},
          "records": {"type": "array", "items": {"type": "object", "required": ["native_id"]}}},
         ["tenant", "source_kind", "records"])),
    ("map_tenant", mapping.map_tenant,
     "Map flat source fields (e.g. {'jira.project':'ACME'}) to exactly one tenant via mappingRules.",
     obj({"fields": {"type": "object", "additionalProperties": {"type": ["string", "array"]}}}, ["fields"])),
    ("injection_scan", safety.injection_scan,
     "Flag instruction-override, recipient and release manipulation, and email addresses in untrusted text.",
     obj({"text": S}, ["text"])),
    ("entity_ledger", entities.entity_ledger,
     "Extract ticket keys, versions, dates, numbers and urls from text (sorted, unique).",
     obj({"text": S, "project_keys": SA}, ["text"])),
    ("entity_diff", entities.entity_diff,
     "Diff the entity ledgers of two texts; equal is true when no entity was added or removed.",
     obj({"before": S, "after": S, "project_keys": SA}, ["before", "after"])),
    ("citation_resolve", send.citation_resolve,
     "Check every draft line cites known evidence ids; returns links for cited ids.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "lines": {"type": "object", "additionalProperties": SA}},
         ["tenant", "run_id", "lines"])),
    ("validate_recipients", send.validate_recipients,
     "Check recipients are all in the tenant config recipients list.",
     obj({"tenant": TENANT, "recipients": SA}, ["tenant", "recipients"])),
    ("hash_run", send.hash_run, "sha256 over the canonical draft, sorted recipients and subject.",
     obj({"draft_text": S, "recipients": SA, "subject": S}, ["draft_text", "recipients", "subject"])),
    ("approval_issue", send.approval_issue,
     "Record the owner's approval of an exact run hash with the owner's quoted words.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "run_hash": S, "approver": S, "quote": S},
         ["tenant", "run_id", "run_hash", "approver", "quote"])),
    ("approval_check", send.approval_check, "Check an approval exists, matches the run hash and is unconsumed.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "run_hash": S}, ["tenant", "run_id", "run_hash"])),
    ("idempotency_check", send.idempotency_check, "Check whether a window+version was already sent.",
     obj({"tenant": TENANT, "window_start": ISO, "window_end": ISO, "version": VERSION},
         ["tenant", "window_start", "window_end"])),
    ("prepare_send", send.prepare_send,
     "Gate a send: approval, hash_run(body, recipients, subject) == run_hash, recipients, channel, gates G0-G8 "
     "and preview, idempotency (v2+ needs the previous version sent); writes runs/pending-send.json (30 min).",
     obj({"tenant": TENANT, "run_id": RUN_ID, "run_hash": S, "recipients": SA, "subject": S,
          "channel": {"type": "string", "enum": ["email", "slack", "teams"]}, "body": BODY, "version": VERSION,
          "window_start": ISO, "window_end": ISO},
         ["tenant", "run_id", "run_hash", "recipients", "subject", "channel", "body", "window_start", "window_end"])),
    ("prepare_preview", send.prepare_preview,
     "Allow a draft preview to owner.previewTo (default owner.email) only, no approval needed; "
     "writes runs/pending-send.json mode preview (30 min).",
     obj({"tenant": TENANT, "run_id": RUN_ID, "subject": S, "body": BODY,
          "channel": {"type": "string", "enum": ["email", "slack", "teams"], "default": "email"}},
         ["tenant", "run_id", "subject", "body"])),
    ("record_send", send.record_send,
     "Record a completed send with read-back verification (subject only for email); consumes the approval and "
     "clears the pending send. window_start/window_end are required except for previews, which are only "
     "verified and cleared.",
     obj({"tenant": TENANT, "run_id": RUN_ID, "message_id": S, "recipients_read_back": SA,
          "subject_read_back": S, "window_start": ISO, "window_end": ISO, "version": VERSION},
         ["tenant", "run_id", "message_id", "recipients_read_back", "subject_read_back"])),
    ("record_gates", send.record_gates,
     "Record gate results G0-G8 (PASS|FAIL|NOT CHECKED, G6 may be REVERTED) and whether the preview was "
     "delivered; prepare_send requires all to pass.",
     obj({"tenant": TENANT, "run_id": RUN_ID,
          "gates": {"type": "object", "required": send.GATES, "additionalProperties": False,
                    "properties": {g: {"type": "string", "enum": ["PASS", "FAIL", "NOT CHECKED"] +
                                       (["REVERTED"] if g == "G6" else [])} for g in send.GATES}},
          "preview_delivered": {"type": "boolean"}}, ["tenant", "run_id", "gates", "preview_delivered"])),
    ("ledger_append", ledger.ledger_append,
     "Append rows to the tenant release ledger CSV (released=T1, pending=T2, mentioned=T3).",
     obj({"tenant": TENANT, "rows": {"type": "array", "items": {"type": "object", "properties": {
         "window_start": S, "window_end": S, "run_id": S, "item_key": S, "title": S,
         "tier": {"type": "string", "enum": ["T1", "T2", "T3", "none"]},
         "section": {"type": "string", "enum": sorted(ledger.SECTIONS)},
         "status": {"type": "string", "enum": sorted(ledger.STATUSES)},
         "evidence_ids": SA, "message_id": S, "carried_from": S},
         "required": ["window_start", "window_end", "run_id", "item_key", "section", "status"],
         "additionalProperties": False}}}, ["tenant", "rows"])),
    ("ledger_carry_over", ledger.ledger_carry_over,
     "Items sent as pending in the latest sent window with no later released row whose status is sent.",
     obj({"tenant": TENANT}, ["tenant"])),
    ("run_log_append", ledger.run_log_append, "Append a run record (run_id, status, model, ...) to the run log.",
     obj({"tenant": TENANT, "record": {"type": "object", "required": ["run_id", "status", "model"], "properties": {
         "run_id": S, "model": S,
         "status": {"type": "string", "pattern": "^(drafted|sent|held|sent:unverified|failed:(" +
                    "|".join(sorted(ledger.FAIL_GATES)) + "))$"},
         "sources": {"type": "array", "items": {"type": "object", "required": ["source", "status"], "properties": {
             "source": S, "status": {"type": "string", "enum": ["complete", "partial", "unknown"]},
             "fetched": {"type": ["integer", "null"]}, "reported_total": {"type": ["integer", "null"]}}}},
         "held_count": {"type": "integer", "minimum": 0}, "recipients_count": {"type": "integer", "minimum": 0},
         "edits": {"type": "integer", "minimum": 0}, "approver": S, "message_id": S}}}, ["tenant", "record"])),
    ("run_start", send.run_start,
     "Mark a release-notes run as active for this tenant (12 h TTL). While any run is active or a send is pending, the PreToolUse send gate enforces on outbound tools.",
     obj({"tenant": TENANT, "run_id": S}, ["tenant", "run_id"])),
    ("run_end", send.run_end, "Clear the tenant's active-run marker at the end of a run.",
     obj({"tenant": TENANT, "run_id": S}, ["tenant", "run_id"])),
    ("clean_run_count", ledger.clean_run_count,
     "Count consecutive most-recent runs sent with zero edits.", obj({"tenant": TENANT}, ["tenant"])),
]
REGISTRY = {name: (fn, schema) for name, fn, _, schema in TOOLS}


def log(*a):
    print("[rn-harness]", *a, file=sys.stderr, flush=True)


def tools_list():
    return {"tools": [{"name": n, "description": d, "inputSchema": s} for n, _, d, s in TOOLS]}


def call_tool(name, args):
    fn, schema = REGISTRY[name]
    if not isinstance(args, dict):
        raise ToolError("arguments must be an object")
    missing = [k for k in schema["required"] if k not in args]
    if missing:
        raise ToolError(f"missing required arguments: {missing}")
    unknown = [k for k in args if k not in schema["properties"]]
    if unknown:
        raise ToolError(f"unknown arguments: {unknown}")
    return fn(**args)


def handle(msg):
    """Return a response dict, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request"}}
    method, mid, is_note = msg["method"], msg.get("id"), "id" not in msg
    params = msg.get("params") or {}

    def ok(result):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        pv = params.get("protocolVersion") if isinstance(params, dict) else None
        return ok({"protocolVersion": pv or DEFAULT_PROTOCOL, "capabilities": {"tools": {}},
                   "serverInfo": SERVER_INFO})
    if method.startswith("notifications/"):
        return None
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok(tools_list())
    if method == "tools/call":
        name = params.get("name") if isinstance(params, dict) else None
        if name not in REGISTRY:
            return err(-32602, f"Unknown tool: {name}")
        try:
            result = call_tool(name, params.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                       "isError": False})
        except (ToolError, TypeError, ValueError, KeyError, OSError) as e:
            log(f"tool {name} error: {e}")
            return ok({"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "isError": True})
        except Exception as e:  # pragma: no cover
            log(traceback.format_exc())
            return ok({"content": [{"type": "text", "text": json.dumps({"error": f"internal error: {e}"})}],
                       "isError": True})
    return err(-32601, f"Method not found: {method}")


def main():
    log("started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if isinstance(msg, list):
                resps = [r for r in (handle(m) for m in msg) if r is not None]
                resp = resps or None
            else:
                resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    log("stdin closed; exiting")


if __name__ == "__main__":
    main()
