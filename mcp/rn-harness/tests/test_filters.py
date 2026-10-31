import json
import unittest

from helpers import BASE, TenantCase, cfg
from tools import ToolError, filters


class ApplyFilters(TenantCase):
    def setUp(self):
        super().setUp()
        s = json.loads(json.dumps(BASE["sources"]))
        s["tracker"]["include"] = {"creators": [], "labels": ["cards", "web"]}
        s["tracker"]["exclude"] = {"labels": ["internal-only"], "creators": ["bot@acme.example"]}
        s["comms"] = [{"kind": "outlook", "mode": "mcp",
                       "include": {"subject": [r"release\s+v?\d", "deployed"], "senders": ["@acme.example"],
                                   "folders": [], "channels": [], "headers": {"X-Env": "prod"}},
                       "exclude": {"subject": ["[draft"], "senders": ["noisy@acme.example"]}}]
        self.make_tenant("acme-cards", cfg(sources=s))

    def test_tracker_exclude_wins(self):
        recs = [
            {"native_id": "ACME-1", "fields": {"labels": ["Cards"], "creator": "dev@acme.example"}},
            {"native_id": "ACME-2", "fields": {"labels": ["cards", "internal-only"]}},
            {"native_id": "ACME-3", "fields": {"labels": ["web"]}, "author": "Build Bot <bot@acme.example>"},
            {"native_id": "ACME-4", "fields": {"labels": ["ops"]}},
        ]
        r = filters.apply_filters("acme-cards", "tracker", recs)
        self.assertEqual(r["kept_ids"], ["ACME-1"])
        self.assertEqual(r["kept"][0]["native_id"], "ACME-1")
        self.assertEqual(r["dropped"], [
            {"native_id": "ACME-2", "rule": "exclude.labels: internal-only"},
            {"native_id": "ACME-3", "rule": "exclude.creators: bot@acme.example"},
            {"native_id": "ACME-4", "rule": "include.labels: no match"}])

    def test_comms(self):
        h = {"X-Env": "prod"}
        recs = [
            {"native_id": "m1", "title": "Release v2 notes", "author": "a@acme.example", "fields": {"headers": h}},
            {"native_id": "m2", "title": "[DRAFT] release 3", "author": "a@acme.example", "fields": {"headers": h}},
            {"native_id": "m3", "title": "deployed", "author": "noisy@acme.example", "fields": {"headers": h}},
            {"native_id": "m4", "title": "deployed", "author": "x@example.com", "fields": {"headers": h}},
            {"native_id": "m5", "title": "lunch", "author": "a@acme.example", "fields": {"headers": h}},
            {"native_id": "m6", "title": "deployed", "author": "a@acme.example", "fields": {"headers": {"x-env": "uat"}}},
        ]
        r = filters.apply_filters("acme-cards", "comms:0", recs)
        self.assertEqual(r["kept_ids"], ["m1"])
        rules = {d["native_id"]: d["rule"] for d in r["dropped"]}
        self.assertEqual(rules["m2"], "exclude.subject: [draft")  # invalid regex falls back to substring
        self.assertEqual(rules["m3"], "exclude.senders: noisy@acme.example")
        self.assertEqual(rules["m4"], "include.senders: no match")
        self.assertEqual(rules["m5"], "include.subject: no match")
        self.assertEqual(rules["m6"], "include.headers: X-Env")

    def test_bad_source_kind(self):
        for k in ("comms:1", "deploy", "comms:x"):
            with self.assertRaises(ToolError):
                filters.apply_filters("acme-cards", k, [])
        with self.assertRaises(ToolError):
            filters.apply_filters("acme-cards", "tracker", [{"title": "no id"}])


if __name__ == "__main__":
    unittest.main()
