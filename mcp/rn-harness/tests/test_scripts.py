import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from helpers import PLUGIN_ROOT, TenantCase, cfg, ready_send
from tools import send

GATE = PLUGIN_ROOT / "scripts" / "send_gate.py"
WS, WE = "2026-10-19T00:00:00+01:00", "2026-10-26T00:00:00+00:00"
RCPT = ["team@acme.example", "owner@acme.example"]


BODY = "Released\n- Card freeze (ACME-1)"
SUBJ = "Release notes 19 Oct"


class SendGate(TenantCase):
    def setUp(self):
        super().setUp()
        send.run_start("acme-cards", "r1")  # the gate enforces only while a run is active

    def gate(self, tool_name, tool_input):
        p = subprocess.run([sys.executable, str(GATE)], input=json.dumps(
            {"tool_name": tool_name, "tool_input": tool_input, "hook_event_name": "PreToolUse"}),
            capture_output=True, text=True, env=dict(os.environ), timeout=30)
        return p.returncode, p.stdout, p.stderr

    def pending(self):
        return self.tmp / "acme-cards" / "runs" / "pending-send.json"

    def ready(self):
        _, r = ready_send("acme-cards", "r1", BODY, RCPT, SUBJ, WS, WE)
        self.assertTrue(r["ready"], r)

    def mail(self, to="team@acme.example", body=BODY, subject=SUBJ):
        return {"to": to, "subject": subject, "body": body}

    def assertDenied(self, res, why=None):
        code, out, err = res
        self.assertEqual(code, 2, (out, err))
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertTrue(err.strip())
        if why:
            self.assertIn(why, reason)

    def test_no_active_run_does_not_interfere(self):
        send.run_end("acme-cards", "r1")
        self.assertEqual(self.gate("mcp__mail__send_email", self.mail()), (0, "", ""))

    def test_run_end_then_pending_still_enforced(self):
        self.ready()
        send.run_end("acme-cards", "r1")
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail(to="eve@other.example")))

    def test_expired_active_marker_does_not_interfere(self):
        p = self.tmp / "acme-cards" / "runs" / "active-run.json"
        rec = json.loads(p.read_text())
        rec["expires_at"] = "2020-01-01T00:00:00Z"
        p.write_text(json.dumps(rec))
        self.assertEqual(self.gate("mcp__mail__send_email", self.mail())[0], 0)

    def test_non_send_tool_passes(self):
        self.assertEqual(self.gate("mcp__tracker__search_issues", {"to": "eve@example.com"}), (0, "", ""))

    def test_own_harness_tools_pass(self):
        for n in ("mcp__plugin_release-notes_rn-harness__prepare_send", "mcp__rn-harness__record_send", "SendMessage"):
            self.assertEqual(self.gate(n, {})[0], 0, n)

    def test_patterns_case_insensitive(self):
        for n in ("mcp__mail__SendMail", "mcp__mail__reply_all", "mcp__chat__PostMessage", "mcp__x__chatMessage",
                  "mcp__x__create_channel_message", "mcp__docs__publish_page", "mcp__mail__Forward"):
            self.assertDenied(self.gate(n, self.mail()))

    def test_no_pending_denies(self):
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail()), "no approved send")

    def test_valid_passes_once(self):
        self.ready()
        call = {"message": {"subject": SUBJ, "body": {"contentType": "Text", "content": BODY + "  \r\n"},
                            "toRecipients": [{"emailAddress": {"address": "Team@acme.example"}}],
                            "ccRecipients": [{"emailAddress": {"address": "owner@acme.example"}}]}}
        code, out, _ = self.gate("mcp__mail__send_email", call)
        self.assertEqual((code, out), (0, ""))
        self.assertTrue(json.loads(self.pending().read_text())["used_at"])
        self.assertDenied(self.gate("mcp__mail__send_email", call), "already used; call record_send")

    def test_body_mismatch_denies(self):
        self.ready()
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail(body=BODY + "\nP.S. extra")), "body differs")
        self.assertDenied(self.gate("mcp__mail__send_email", {"to": "team@acme.example", "subject": SUBJ}),
                          "could not read the message body")

    def test_subject_mismatch_denies(self):
        self.ready()
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail(subject="Other")), "subject differs")

    def test_extra_recipient_denies(self):
        self.ready()
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail(to="team@acme.example, eve@example.com")))

    def test_no_recipients_denies(self):
        self.ready()
        self.assertDenied(self.gate("mcp__mail__send_email", {"body": BODY}))

    def test_expired_denies(self):
        self.ready()
        p = json.loads(self.pending().read_text())
        p["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.pending().write_text(json.dumps(p))
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail()))

    def test_already_sent_denies(self):
        self.ready()
        p = json.loads(self.pending().read_text())
        (self.tmp / "acme-cards" / "runs" / "sent.jsonl").write_text(json.dumps({"key": p["idempotency_key"], "run_id": "r0"}) + "\n")
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail()))

    def test_slack_channel_prefix(self):
        self.make_tenant("acme-cards", cfg(delivery={"channel": "slack", "connector": "chat", "subjectPattern": "x"}))
        _, r = ready_send("acme-cards", "r1", BODY, ["slack:#cards-releases"], "s", WS, WE, channel="slack")
        self.assertTrue(r["ready"], r)
        self.assertDenied(self.gate("mcp__slack__chat_postMessage", {"channel": "#general", "text": BODY}))
        self.assertEqual(self.gate("mcp__slack__chat_postMessage", {"channel": "#cards-releases", "text": BODY})[0], 0)

    def test_preview_owner_only(self):
        self.assertTrue(send.prepare_preview("acme-cards", "r1", "Draft", BODY)["ready"])
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail(["owner@acme.example", "team@acme.example"], subject="Draft")))
        self.assertDenied(self.gate("mcp__mail__send_email", self.mail("owner@acme.example", body="other", subject="Draft")))
        self.assertEqual(self.gate("mcp__mail__send_email", self.mail("OWNER@acme.example", subject="Draft"))[0], 0)

    def test_bad_input_fails_closed(self):
        p = subprocess.run([sys.executable, str(GATE)], input="{not json", capture_output=True, text=True,
                           env=dict(os.environ), timeout=30)
        self.assertEqual(p.returncode, 2)


class Scripts(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=60,
                              cwd=str(PLUGIN_ROOT))

    def test_validate_template(self):
        p = self.run_script(PLUGIN_ROOT / "scripts" / "validate_tenant.py", PLUGIN_ROOT / "tenants" / "_template")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("WARNING placeholder", p.stdout)

    def test_validate_bad_exits_1(self):
        d = Path(tempfile.mkdtemp()) / "acme-bad"
        d.mkdir()
        (d / "config.json").write_text(json.dumps({"tenant": "acme-bad"}))
        try:
            p = self.run_script(PLUGIN_ROOT / "scripts" / "validate_tenant.py", d)
            self.assertEqual(p.returncode, 1)
            self.assertIn("ERROR", p.stdout)
        finally:
            shutil.rmtree(d.parent)

    def test_backtest_sample(self):
        p = self.run_script(PLUGIN_ROOT / "scripts" / "backtest.py", "--fixtures", PLUGIN_ROOT / "evals" / "fixtures",
                            "--case", "acme-sample", "--json")
        self.assertEqual(p.returncode, 1)
        r = json.loads(p.stdout)["results"]["acme-sample"]
        self.assertAlmostEqual(r["metrics"]["recall"], 0.8)
        self.assertAlmostEqual(r["metrics"]["precision"], 0.8)
        self.assertEqual(r["verdict"]["false_released"], "PASS")
        self.assertEqual(r["verdict"]["entity_preserved"], "PASS")
        self.assertEqual(r["misses"], ["ACME-103"])
        self.assertEqual(r["false_items"], ["ACME-106"])

    def test_backtest_not_run_and_failures(self):
        root = Path(tempfile.mkdtemp())
        try:
            c = root / "c1"
            c.mkdir()
            (c / "answer-key.json").write_text(json.dumps({"window": {}, "items": [{"key": "A-1", "section": "pending"}]}))
            (c / "agent-output.json").write_text(json.dumps({"items": [
                {"key": "A-1", "section": "released", "evidence_ids": []},
                {"key": "A-1", "section": "released", "evidence_ids": ["x"]}]}))
            p = self.run_script(PLUGIN_ROOT / "scripts" / "backtest.py", "--fixtures", root, "--json")
            v = json.loads(p.stdout)["results"]["c1"]["verdict"]
            self.assertEqual(v["entity_preserved"], "NOT RUN")
            self.assertEqual(v["recall"], "PASS")
            for k in ("false_released", "uncited_lines", "duplicates"):
                self.assertEqual(v[k], "FAIL")
            self.assertEqual(p.returncode, 1)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
