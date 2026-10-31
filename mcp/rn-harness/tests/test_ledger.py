import json
import unittest

from helpers import TenantCase
from tools import ToolError, ledger

W1 = ("2026-10-12T00:00:00+01:00", "2026-10-19T00:00:00+01:00")
W2 = ("2026-10-19T00:00:00+01:00", "2026-10-26T00:00:00+00:00")


def row(w, key, section, status, run="r1", **kw):
    r = {"window_start": w[0], "window_end": w[1], "run_id": run, "item_key": key, "title": f"title {key}",
         "tier": {"released": "T1", "pending": "T2"}.get(section, "T3"), "section": section, "status": status,
         "evidence_ids": [f"jira:{key}:00000000"], "message_id": "m", "carried_from": ""}
    r.update(kw)
    return r


class Ledger(TenantCase):
    def test_append_header_and_validation(self):
        self.assertEqual(ledger.ledger_append("acme-cards", [row(W1, "ACME-1", "released", "sent")]), {"appended": 1})
        ledger.ledger_append("acme-cards", [row(W1, "ACME-2", "pending", "sent", evidence_ids=["a", "b"])])
        text = (self.tmp / "acme-cards" / "release-ledger.csv").read_text()
        self.assertEqual(text.splitlines()[0], ",".join(ledger.COLUMNS))
        self.assertEqual(text.count("window_start"), 1)
        self.assertIn("a;b", text)
        for bad in (row(W1, "X", "shipped", "sent"), row(W1, "X", "released", "posted"), {"item_key": "X"}):
            with self.assertRaises(ToolError):
                ledger.ledger_append("acme-cards", [bad])
        self.assertEqual(len(ledger.read_ledger("acme-cards")), 2)

    def test_formula_cells_neutralised(self):
        ledger.ledger_append("acme-cards", [row(W1, "ACME-9", "released", "sent", title="=HYPERLINK(1)")])
        raw = (self.tmp / "acme-cards" / "release-ledger.csv").read_text()
        self.assertIn("'=HYPERLINK", raw)
        self.assertEqual(ledger.read_ledger("acme-cards")[0]["title"], "=HYPERLINK(1)")

    def test_carry_over(self):
        self.assertEqual(ledger.ledger_carry_over("acme-cards"), {"items": []})
        ledger.ledger_append("acme-cards", [
            row(W1, "ACME-1", "pending", "sent"),
            row(W2, "ACME-2", "pending", "sent", run="r2"),
            row(W2, "ACME-3", "pending", "sent", run="r2"),
            row(W2, "ACME-4", "pending", "held", run="r2"),
            row(W2, "ACME-5", "released", "sent", run="r2"),
        ])
        ledger.ledger_append("acme-cards", [row(W2, "ACME-3", "released", "drafted", run="r3")])
        r = ledger.ledger_carry_over("acme-cards")
        self.assertEqual([i["item_key"] for i in r["items"]], ["ACME-2", "ACME-3"])  # drafted release does not count
        ledger.ledger_append("acme-cards", [row(W2, "ACME-3", "released", "sent", run="r4")])
        r = ledger.ledger_carry_over("acme-cards")
        self.assertEqual(r["items"], [{"item_key": "ACME-2", "title": "title ACME-2", "from_window_start": W2[0]}])

    def test_section_tier_pairs(self):
        for section, tier in (("released", "T2"), ("pending", "T1"), ("mentioned", "none"), ("released", "")):
            with self.assertRaises(ToolError):
                ledger.ledger_append("acme-cards", [row(W1, "ACME-1", section, "sent", tier=tier)])
        self.assertEqual(ledger.ledger_append("acme-cards", [row(W1, "ACME-1", "excluded", "dropped", tier="none")]),
                         {"appended": 1})


class RunLog(TenantCase):
    def test_append_and_count(self):
        self.assertEqual(ledger.clean_run_count("acme-cards"), {"count": 0})
        with self.assertRaises(ToolError):
            ledger.run_log_append("acme-cards", {"run_id": "r", "status": "done", "model": "m"})
        with self.assertRaises(ToolError):
            ledger.run_log_append("acme-cards", {"run_id": "r", "status": "sent"})
        for bad in ("failed", "failed:other", "failed:"):
            with self.assertRaises(ToolError):
                ledger.run_log_append("acme-cards", {"run_id": "r", "status": bad, "model": "m"})
        with self.assertRaises(ToolError):
            ledger.run_log_append("acme-cards", {"run_id": "r", "status": "held", "model": "m",
                                                 "sources": [{"source": "jira", "status": "done"}]})
        seq = [("r1", "sent", 0), ("r2", "sent", 2), ("r3", "drafted", None), ("r3", "sent", 0), ("r4", "sent", 0)]
        for rid, st, ed in seq:
            rec = {"run_id": rid, "status": st, "model": "m"}
            if ed is not None:
                rec["edits"] = ed
            self.assertEqual(ledger.run_log_append("acme-cards", rec), {"ok": True})
        last = json.loads((self.tmp / "acme-cards" / "runs" / "run_log.jsonl").read_text().splitlines()[-1])
        self.assertIn("logged_at", last)
        self.assertEqual(ledger.clean_run_count("acme-cards"), {"count": 2})
        ledger.run_log_append("acme-cards", {"run_id": "r5", "status": "drafted", "model": "m"})
        self.assertEqual(ledger.clean_run_count("acme-cards"), {"count": 2})  # in-progress run is skipped
        ledger.run_log_append("acme-cards", {"run_id": "r5", "status": "held", "model": "m"})
        self.assertEqual(ledger.clean_run_count("acme-cards"), {"count": 0})

    def test_new_statuses_and_fields(self):
        for st in ("failed:source_unreachable", "failed:review", "sent:unverified", "held"):
            self.assertTrue(ledger.run_log_append("acme-cards", {
                "run_id": "r1", "status": st, "model": "m", "held_count": 1, "recipients_count": 2,
                "approver": "owner@acme.example", "message_id": "m-1",
                "sources": [{"source": "jira", "status": "complete", "fetched": 3, "reported_total": 3},
                            {"source": "outlook", "status": "unknown", "fetched": 2, "reported_total": None}]})["ok"])
        ledger.run_log_append("acme-cards", {"run_id": "r2", "status": "sent", "model": "m", "edits": 0})
        ledger.run_log_append("acme-cards", {"run_id": "r3", "status": "sent:unverified", "model": "m", "edits": 0})
        self.assertEqual(ledger.clean_run_count("acme-cards"), {"count": 0})


if __name__ == "__main__":
    unittest.main()
