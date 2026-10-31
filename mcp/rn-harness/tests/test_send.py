import json
import unittest
from datetime import datetime, timedelta, timezone

from helpers import ALL_PASS, TenantCase, cfg, ready_send
from tools import evidence, send

WS, WE = "2026-10-19T00:00:00+01:00", "2026-10-26T00:00:00+00:00"
RCPT = ["team@acme.example", "owner@acme.example"]
SUBJ = "Release notes 19 Oct"


class Citations(TenantCase):
    def test_resolve(self):
        ids = evidence.evidence_put("acme-cards", "r1", [{"source": "jira", "native_id": "ACME-1",
                                                           "url": "https://acme.example/browse/ACME-1"}])["ids"]
        r = send.citation_resolve("acme-cards", "r1", {"l1": ids, "l2": [], "l3": ["jira:X-1:deadbeef"]})
        self.assertFalse(r["ok"])
        self.assertEqual(r["uncited"], ["l2"])
        self.assertEqual(r["unknown_ids"], ["jira:X-1:deadbeef"])
        self.assertEqual(r["links"], {ids[0]: "https://acme.example/browse/ACME-1"})
        self.assertTrue(send.citation_resolve("acme-cards", "r1", {"l1": ids})["ok"])


class Recipients(TenantCase):
    def test_validate(self):
        self.assertEqual(send.validate_recipients("acme-cards", ["TEAM@acme.example", "slack:#cards-releases"]),
                         {"ok": True, "rejected": []})
        r = send.validate_recipients("acme-cards", ["team@acme.example", "eve@example.com", "slack:#other"])
        self.assertEqual(r["rejected"], ["eve@example.com", "slack:#other"])
        self.assertFalse(send.validate_recipients("acme-cards", [])["ok"])


class Hash(unittest.TestCase):
    def test_stable_and_sensitive(self):
        a = send.hash_run("d", ["B@example.com", "a@example.com"], "s")["run_hash"]
        self.assertEqual(a, send.hash_run("d", ["a@example.com", "b@example.com"], "s")["run_hash"])
        self.assertNotEqual(a, send.hash_run("d!", ["a@example.com", "b@example.com"], "s")["run_hash"])
        self.assertNotEqual(a, send.hash_run("d", ["a@example.com"], "s")["run_hash"])
        self.assertRegex(a, "^[0-9a-f]{64}$")


BODY = "Released\r\n- Card freeze (ACME-1)   \n"


class Body(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(send.normalise_body(" \nA  \r\nB\t\r\n\n"), "A\nB")
        self.assertEqual(send.body_sha256("A\r\nB  "), send.body_sha256("A\nB\n\n"))


class Flow(TenantCase):
    def setUp(self):
        super().setUp()
        self.h = send.hash_run(BODY, RCPT, SUBJ)["run_hash"]

    def pending(self):
        return self.tmp / "acme-cards" / "runs" / "pending-send.json"

    def approve(self, run="r1", quote="yes send it now"):
        return send.approval_issue("acme-cards", run, self.h, "Owner@Acme.example", quote)

    def prep(self, run="r1", body=BODY, rcpt=RCPT, channel="email", version="v1"):
        return send.prepare_send("acme-cards", run, self.h, rcpt, SUBJ, channel, body, WS, WE, version)

    def test_approval_rules(self):
        self.assertFalse(send.approval_issue("acme-cards", "r1", self.h, "eve@example.com", "yes send it")["ok"])
        self.assertFalse(send.approval_issue("acme-cards", "r1", self.h, "owner@acme.example", "ok")["ok"])
        self.assertFalse(send.approval_issue("acme-cards", "r1", "abc", "owner@acme.example", "yes send it")["ok"])
        self.assertEqual(send.approval_check("acme-cards", "r1", self.h)["valid"], False)
        r = self.approve()
        self.assertTrue(r["ok"])
        self.assertRegex(r["token"], "^[0-9a-f]{32}$")
        self.assertTrue(send.approval_check("acme-cards", "r1", self.h)["valid"])
        bad = send.approval_check("acme-cards", "r1", "0" * 64)
        self.assertFalse(bad["valid"])
        self.assertIn("hash", bad["reason"])

    def test_auto_send_quote(self):
        r = self.approve(quote="Auto-send: clean streak")
        self.assertFalse(r["ok"])
        self.assertIn("autoSend.enabled", r["reason"])
        self.make_tenant("acme-cards", cfg(autoSend={"enabled": True, "earnedAfterCleanRuns": 2}))
        from tools import ledger
        ledger.run_log_append("acme-cards", {"run_id": "a1", "status": "sent", "model": "m", "edits": 0})
        r = self.approve(quote="auto-send clean streak")
        self.assertFalse(r["ok"])
        self.assertIn("not earned", r["reason"])
        ledger.run_log_append("acme-cards", {"run_id": "a2", "status": "sent", "model": "m", "edits": 0})
        self.assertTrue(self.approve(quote="auto-send clean streak")["ok"])

    def test_record_gates(self):
        from tools import ToolError
        g = dict(ALL_PASS, G6="REVERTED")
        self.assertEqual(send.record_gates("acme-cards", "r1", g, True), {"ok": True, "all_pass": True})
        for bad in (dict(ALL_PASS, G2="REVERTED"), {"G0": "PASS"}, dict(ALL_PASS, G9="PASS"), dict(ALL_PASS, G1="ok")):
            with self.assertRaises(ToolError):
                send.record_gates("acme-cards", "r1", bad, True)
        self.assertFalse(send.record_gates("acme-cards", "r1", dict(ALL_PASS, G3="FAIL"), True)["all_pass"])

    def test_prepare_requires_gates_and_preview(self):
        self.approve()
        r = self.prep()
        self.assertIn("gates: not recorded (call record_gates)", r["reasons"])
        send.record_gates("acme-cards", "r1", dict(ALL_PASS, G2="FAIL", G5="NOT CHECKED"), False)
        r = self.prep()
        self.assertFalse(r["ready"])
        for want in ("gate G2 is FAIL", "gate G5 is NOT CHECKED", "preview not delivered to the owner"):
            self.assertIn(want, r["reasons"])
        send.record_gates("acme-cards", "r1", dict(ALL_PASS, G6="REVERTED"), True)
        self.assertTrue(self.prep()["ready"])

    def test_prepare_not_ready_writes_nothing(self):
        send.record_gates("acme-cards", "r1", ALL_PASS, True)
        r = self.prep()
        self.assertFalse(r["ready"])
        self.assertTrue(any("approval" in x for x in r["reasons"]))
        self.assertFalse(self.pending().exists())
        self.approve()
        self.assertFalse(self.prep(rcpt=RCPT + ["eve@example.com"])["ready"])
        self.assertFalse(self.prep(channel="slack")["ready"])
        r = self.prep(body=BODY + " plus an unapproved line")
        self.assertTrue(any(x.startswith("body:") for x in r["reasons"]))
        self.assertFalse(self.pending().exists())

    def test_full_send_then_idempotent(self):
        h, r = ready_send("acme-cards", "r1", BODY, RCPT, SUBJ, WS, WE)
        self.assertEqual(r, {"ready": True, "reasons": []})
        p = json.loads(self.pending().read_text())
        self.assertEqual(p["mode"], "send")
        self.assertEqual(p["body_sha256"], send.body_sha256(BODY))
        self.assertEqual(p["idempotency_key"], f"acme-cards|{WS}|{WE}|v1")
        exp = datetime.fromisoformat(p["expires_at"].replace("Z", "+00:00"))
        self.assertLess(exp - datetime.now(timezone.utc), timedelta(minutes=31))
        p["used_at"] = "2026-10-26T09:00:00Z"  # the hook marks it used; record_send still accepts it
        self.pending().write_text(json.dumps(p))
        r = send.record_send("acme-cards", "r1", "msg-1", ["OWNER@acme.example", "team@acme.example"], SUBJ, WS, WE)
        self.assertEqual(r, {"ok": True, "verified": True, "mismatches": []})
        self.assertFalse(self.pending().exists())
        self.assertEqual(send.approval_check("acme-cards", "r1", h)["reason"], "approval already consumed")
        ic = send.idempotency_check("acme-cards", "2026-10-18T23:00:00Z", WE)  # same instant, other notation
        self.assertTrue(ic["used"])
        self.assertEqual(ic["by_run"], "r1")
        self.assertFalse(send.idempotency_check("acme-cards", WS, WE, "v2")["used"])
        self.assertFalse(self.approve()["ok"])
        _, r = ready_send("acme-cards", "r2", BODY, RCPT, SUBJ, WS, WE)
        self.assertTrue(any("already sent" in x for x in r["reasons"]))
        # a correction v2 is allowed once v1 is sent; v3 needs v2
        _, r = ready_send("acme-cards", "r3", BODY, RCPT, SUBJ, WS, WE, version="v3")
        self.assertTrue(any("needs v2" in x for x in r["reasons"]))
        _, r = ready_send("acme-cards", "r2", BODY, RCPT, SUBJ, WS, WE, version="v2")
        self.assertTrue(r["ready"], r)

    def test_correction_without_v1_refused(self):
        _, r = ready_send("acme-cards", "r1", BODY, RCPT, SUBJ, WS, WE, version="v2")
        self.assertFalse(r["ready"])
        self.assertTrue(any("needs v1" in x for x in r["reasons"]))

    def test_record_mismatch_still_recorded(self):
        ready_send("acme-cards", "r1", BODY, RCPT, SUBJ, WS, WE)
        r = send.record_send("acme-cards", "r1", "m", ["team@acme.example"], SUBJ + "x", WS, WE)
        self.assertTrue(r["ok"])
        self.assertFalse(r["verified"])
        self.assertEqual(len(r["mismatches"]), 2)
        line = json.loads((self.tmp / "acme-cards" / "runs" / "sent.jsonl").read_text().splitlines()[0])
        self.assertFalse(line["verified"])
        self.assertEqual(set(line), {"key", "run_id", "message_id", "start", "end", "sent_at", "verified"})

    def test_chat_readback_ignores_subject(self):
        self.make_tenant("acme-cards", cfg(delivery={"channel": "slack", "connector": "chat", "subjectPattern": "x"}))
        _, r = ready_send("acme-cards", "r1", BODY, ["slack:#cards-releases"], SUBJ, WS, WE, channel="slack")
        self.assertTrue(r["ready"], r)
        r = send.record_send("acme-cards", "r1", "ts-1", ["slack:#cards-releases"], "", WS, WE)
        self.assertEqual((r["verified"], r["mismatches"]), (True, []))

    def test_record_without_pending(self):
        self.assertFalse(send.record_send("acme-cards", "r1", "m", RCPT, SUBJ, WS, WE)["ok"])

    def test_preview(self):
        r = send.prepare_preview("acme-cards", "r1", "Draft: " + SUBJ, BODY)
        self.assertEqual(r, {"ready": True})
        p = json.loads(self.pending().read_text())
        self.assertEqual((p["mode"], p["recipients"], p["channel"]), ("preview", ["owner@acme.example"], "email"))
        self.assertEqual(p["body_sha256"], send.body_sha256(BODY))
        r = send.record_send("acme-cards", "r1", "m0", ["owner@acme.example"], "Draft: " + SUBJ)  # no window
        self.assertEqual((r["ok"], r["verified"]), (True, True))
        self.assertFalse((self.tmp / "acme-cards" / "runs" / "sent.jsonl").exists())
        self.assertFalse(self.pending().exists())
        self.approve()
        send.prepare_preview("acme-cards", "r1", "Draft", BODY)
        send.record_send("acme-cards", "r1", "m1", ["owner@acme.example"], "Draft")
        self.assertTrue(send.approval_check("acme-cards", "r1", self.h)["valid"])
        self.assertFalse(send.prepare_preview("acme-cards", "r1", "Draft", "  ")["ready"])

    def test_preview_to(self):
        self.make_tenant("acme-cards", cfg(owner={"email": "owner@acme.example", "previewTo": "slack:U0OWNER"}))
        self.assertFalse(send.prepare_preview("acme-cards", "r1", "Draft", BODY)["ready"])  # email vs slack target
        self.assertTrue(send.prepare_preview("acme-cards", "r1", "Draft", BODY, "slack")["ready"])
        p = json.loads(self.pending().read_text())
        self.assertEqual(p["recipients"], ["slack:U0OWNER"])

    def test_preview_blocked_by_other_pending_send(self):
        ready_send("acme-cards", "r1", BODY, RCPT, SUBJ, WS, WE)
        self.assertFalse(send.prepare_preview("acme-cards", "r9", "Draft", BODY)["ready"])


if __name__ == "__main__":
    unittest.main()
