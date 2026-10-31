import unittest

from tools import entities


class Ledger(unittest.TestCase):
    def test_categories(self):
        t = ("ACME-12 shipped in v2.4.1 and release 3.1 on 2026-10-22 (also 12 Oct 2026, Oct 12, 2026, 12/10/2026). "
             "Approval rate up 4.5% across 1,200 accounts; 3 fixes. See https://acme.example/r/ACME-12?x=1).")
        r = entities.entity_ledger(t)
        self.assertEqual(r["ticket_keys"], ["ACME-12"])
        self.assertEqual(r["versions"], ["3.1", "v2.4.1"])
        self.assertEqual(r["dates"], ["12 Oct 2026", "12/10/2026", "2026-10-22", "Oct 12, 2026"])
        self.assertEqual(r["urls"], ["https://acme.example/r/ACME-12?x=1"])
        self.assertEqual(r["numbers"], ["1,200", "3", "4.5%"])

    def test_no_double_count(self):
        r = entities.entity_ledger("UTF-8 and SHA-256 at 10:30")
        self.assertEqual(r["ticket_keys"], [])
        self.assertNotIn("10", r["numbers"])

    def test_project_keys(self):
        r = entities.entity_ledger("ACME-1 PAY-2", ["ACME"])
        self.assertEqual(r["ticket_keys"], ["ACME-1"])

    def test_diff(self):
        a = "ACME-1 released v1.2.0 on 2026-10-22 for 40% of users."
        b = "On 2026-10-22, v1.2.0 went live (ACME-1) for 40% of users."
        self.assertEqual(entities.entity_diff(a, b), {"equal": True, "added": {}, "removed": {}})
        c = "On 2026-10-23, v1.2.0 went live (ACME-1) for 45% of users."
        d = entities.entity_diff(a, c)
        self.assertFalse(d["equal"])
        self.assertEqual(d["added"], {"dates": ["2026-10-23"], "numbers": ["45%"]})
        self.assertEqual(d["removed"], {"dates": ["2026-10-22"], "numbers": ["40%"]})


if __name__ == "__main__":
    unittest.main()
