import json
import unittest

from helpers import TenantCase, cfg
from tools import window


class ResolveWindow(TenantCase):
    def test_weekly_basic(self):
        r = window.resolve_window("acme-cards", now="2026-10-28T12:00:00+00:00")
        self.assertTrue(r["ok"])
        self.assertEqual(r["start"], "2026-10-19T00:00:00+01:00")
        self.assertEqual(r["end"], "2026-10-26T00:00:00+00:00")
        self.assertEqual(r["tz"], "Europe/London")
        self.assertEqual(r["cadence"], "weekly")
        self.assertEqual(r["overlaps"], [])

    def test_weekly_dst_week_is_169_hours(self):
        r = window.resolve_window("acme-cards", now="2026-10-26T09:00:00")
        from datetime import datetime
        s, e = datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"])
        self.assertEqual((e - s).total_seconds(), 169 * 3600)  # clocks went back 25 Oct 2026

    def test_anchor_edges(self):
        r = window.resolve_window("acme-cards", now="2026-10-26T00:00:00")
        self.assertEqual(r["end"], "2026-10-26T00:00:00+00:00")
        r = window.resolve_window("acme-cards", now="2026-10-25T23:59:59")
        self.assertEqual(r["end"], "2026-10-19T00:00:00+01:00")
        self.assertEqual(r["start"], "2026-10-12T00:00:00+01:00")

    def test_now_utc_is_converted_to_tenant_tz(self):
        # 23:30 UTC on Sunday 18 Oct = 00:30 BST Monday 19 Oct, so the week ending 19 Oct is complete
        r = window.resolve_window("acme-cards", now="2026-10-18T23:30:00Z")
        self.assertEqual(r["end"], "2026-10-19T00:00:00+01:00")

    def test_fortnightly(self):
        self.make_tenant("acme-cards", cfg(window={"tz": "UTC", "cadence": "fortnightly", "anchor": "MON 09:00",
                                                    "anchorDate": "2026-01-05"}))
        r = window.resolve_window("acme-cards", now="2026-10-28T00:00:00")
        # periods start 2026-01-05 + 14n; 2026-10-26 is n=21
        self.assertEqual(r["end"], "2026-10-26T09:00:00+00:00")
        self.assertEqual(r["start"], "2026-10-12T09:00:00+00:00")
        r = window.resolve_window("acme-cards", now="2026-10-26T08:59:59")
        self.assertEqual(r["end"], "2026-10-12T09:00:00+00:00")

    def test_monthly(self):
        self.make_tenant("acme-cards", cfg(window={"tz": "Europe/London", "cadence": "monthly", "anchor": "01 00:00"}))
        r = window.resolve_window("acme-cards", now="2026-11-15T10:00:00")
        self.assertEqual(r["start"], "2026-10-01T00:00:00+01:00")
        self.assertEqual(r["end"], "2026-11-01T00:00:00+00:00")
        r = window.resolve_window("acme-cards", now="2026-01-10T00:00:00")
        self.assertEqual(r["start"], "2025-12-01T00:00:00+00:00")

    def test_on_demand_needs_explicit(self):
        self.make_tenant("acme-cards", cfg(window={"tz": "UTC", "cadence": "on_demand"}))
        r = window.resolve_window("acme-cards")
        self.assertFalse(r["ok"])
        self.assertIn("reason", r)
        r = window.resolve_window("acme-cards", start="2026-10-01", end="2026-10-15")
        self.assertTrue(r["ok"])
        self.assertEqual(r["start"], "2026-10-01T00:00:00+00:00")

    def test_explicit_partial_and_inverted(self):
        self.assertFalse(window.resolve_window("acme-cards", start="2026-10-01")["ok"])
        self.assertFalse(window.resolve_window("acme-cards", start="2026-10-10", end="2026-10-01")["ok"])

    def test_overlaps(self):
        runs = self.tmp / "acme-cards" / "runs"
        runs.mkdir()
        (runs / "sent.jsonl").write_text(json.dumps({"key": "k", "run_id": "r1", "start": "2026-10-22T00:00:00+01:00",
                                                     "end": "2026-10-29T00:00:00+00:00"}) + "\n" +
                                         json.dumps({"key": "k2", "run_id": "r0", "start": "2026-10-12T00:00:00+01:00",
                                                     "end": "2026-10-19T00:00:00+01:00"}) + "\n")
        r = window.resolve_window("acme-cards", now="2026-10-28T12:00:00")
        self.assertEqual([o["run_id"] for o in r["overlaps"]], ["r1"])  # touching end is not an overlap

    def test_correction_ignores_same_window(self):
        runs = self.tmp / "acme-cards" / "runs"
        runs.mkdir()
        (runs / "sent.jsonl").write_text(json.dumps({"key": "k", "run_id": "r1", "start": "2026-10-19T00:00:00+01:00",
                                                     "end": "2026-10-26T00:00:00+00:00"}) + "\n")
        r = window.resolve_window("acme-cards", now="2026-10-28T12:00:00")
        self.assertEqual(len(r["overlaps"]), 1)
        r = window.resolve_window("acme-cards", now="2026-10-28T12:00:00", version="v2")
        self.assertEqual(r["overlaps"], [])
        from tools import ToolError
        with self.assertRaises(ToolError):
            window.resolve_window("acme-cards", version="2")


if __name__ == "__main__":
    unittest.main()
