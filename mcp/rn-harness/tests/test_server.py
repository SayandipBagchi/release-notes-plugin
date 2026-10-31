import json
import os
import subprocess
import sys
import unittest

from helpers import HARNESS, TenantCase

import server

EXPECTED = ["validate_tenant", "resolve_window", "completeness_check", "evidence_put", "evidence_get",
            "extract_ticket_keys", "tier_item", "apply_filters", "map_tenant", "injection_scan", "entity_ledger", "entity_diff",
            "citation_resolve", "validate_recipients", "hash_run", "approval_issue", "approval_check",
            "idempotency_check", "prepare_send", "prepare_preview", "record_send", "record_gates", "ledger_append",
            "ledger_carry_over", "run_log_append", "run_start", "run_end", "clean_run_count"]


class Handle(TenantCase):
    def call(self, name, args, mid=1):
        return server.handle({"jsonrpc": "2.0", "id": mid, "method": "tools/call",
                              "params": {"name": name, "arguments": args}})

    def test_initialize(self):
        r = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(r["result"]["serverInfo"], {"name": "rn-harness", "version": "0.1.0"})
        self.assertEqual(r["result"]["capabilities"], {"tools": {}})
        r = server.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")

    def test_notification_ping_unknown(self):
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(server.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"})["result"], {})
        self.assertEqual(server.handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})["error"]["code"], -32601)

    def test_tools_list(self):
        tools = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], EXPECTED)
        for t in tools:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertTrue(t["description"])

    def test_call_ok_and_errors(self):
        r = self.call("hash_run", {"draft_text": "d", "recipients": [], "subject": "s"})
        self.assertFalse(r["result"]["isError"])
        self.assertIn("run_hash", json.loads(r["result"]["content"][0]["text"]))
        r = self.call("validate_tenant", {"tenant": "../x"})
        self.assertTrue(r["result"]["isError"])
        r = self.call("hash_run", {"draft_text": "d"})
        self.assertTrue(r["result"]["isError"])
        r = self.call("hash_run", {"draft_text": "d", "recipients": [], "subject": "s", "evil": 1})
        self.assertTrue(r["result"]["isError"])
        r = self.call("no_such_tool", {})
        self.assertIn("error", r)


class Stdio(TenantCase):
    def test_roundtrip(self):
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "validate_tenant", "arguments": {"tenant": "acme-cards"}}}]
        inp = "\n".join(json.dumps(m) for m in msgs) + "\nnot json\n"
        p = subprocess.run([sys.executable, str(HARNESS / "server.py")], input=inp, capture_output=True, text=True,
                           env=dict(os.environ), timeout=30)
        lines = [json.loads(x) for x in p.stdout.splitlines()]
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0]["id"], 1)
        self.assertEqual(json.loads(lines[1]["result"]["content"][0]["text"])["ok"], True)
        self.assertEqual(lines[2]["error"]["code"], -32700)
        self.assertIn("rn-harness", p.stderr)


if __name__ == "__main__":
    unittest.main()
