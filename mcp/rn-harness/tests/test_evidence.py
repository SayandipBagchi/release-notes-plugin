import unittest

from helpers import TenantCase
from tools import ToolError, evidence

REC = {"source": "jira", "native_id": "ACME-1", "url": "https://acme.example/browse/ACME-1", "title": "t",
       "timestamp": "2026-10-20T10:00:00Z", "author": "dev@acme.example", "excerpt": "x", "fields": {"status": "Done"}}


class Completeness(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(evidence.completeness_check("jira", 5, 5)["status"], "complete")
        self.assertEqual(evidence.completeness_check("jira", 4, 5)["status"], "partial")
        r = evidence.completeness_check("jira", 6, 5)
        self.assertEqual(r["status"], "partial")
        self.assertIn("note", r)
        r = evidence.completeness_check("outlook", 3, None)
        self.assertEqual(r["status"], "unknown")
        self.assertEqual(r["reported_total"], None)

    def test_bad_input(self):
        with self.assertRaises(ToolError):
            evidence.completeness_check("jira", -1, 2)


class Store(TenantCase):
    def test_put_get_idempotent(self):
        ids = evidence.evidence_put("acme-cards", "run-1", [REC])["ids"]
        self.assertRegex(ids[0], r"^jira:ACME-1:[0-9a-f]{8}$")
        again = evidence.evidence_put("acme-cards", "run-1", [REC, REC])["ids"]
        self.assertEqual(again, [ids[0], ids[0]])
        lines = (self.tmp / "acme-cards" / "runs" / "run-1" / "evidence.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        changed = dict(REC, title="other")
        self.assertNotEqual(evidence.evidence_put("acme-cards", "run-1", [changed])["ids"][0], ids[0])
        g = evidence.evidence_get("acme-cards", "run-1", [ids[0], "jira:NOPE-1:00000000"])
        self.assertEqual(g["records"][ids[0]]["url"], REC["url"])
        self.assertEqual(g["missing"], ["jira:NOPE-1:00000000"])

    def test_bad_run_id_and_record(self):
        for rid in ("../x", "a/b", "", "x" * 65):
            with self.assertRaises(ToolError):
                evidence.evidence_put("acme-cards", rid, [REC])
        with self.assertRaises(ToolError):
            evidence.evidence_put("acme-cards", "r", [{"source": "jira"}])


class TicketKeys(unittest.TestCase):
    def test_generic(self):
        t = "Fixed ACME-12 and PAY-7; see ACME-12 again. UTF-8, ISO-8601, SHA-256, CVE-2026-1234 are not keys."
        r = evidence.extract_ticket_keys(t)["keys"]
        self.assertEqual([k["key"] for k in r], ["ACME-12", "PAY-7"])
        self.assertEqual(t[r[0]["start"]:r[0]["end"]], "ACME-12")

    def test_project_filter(self):
        r = evidence.extract_ticket_keys("ACME-1 PAY-2 ACME-3", ["ACME"])["keys"]
        self.assertEqual([k["key"] for k in r], ["ACME-1", "ACME-3"])

    def test_bad_project_key(self):
        with self.assertRaises(ToolError):
            evidence.extract_ticket_keys("x", ["acme"])


if __name__ == "__main__":
    unittest.main()
