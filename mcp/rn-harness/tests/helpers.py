import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = HARNESS.parents[1]
sys.path.insert(0, str(HARNESS))

BASE = {
    "tenant": "acme-cards",
    "classification": {"org": "acme", "product": "cards", "bu": "consumer"},
    "owner": {"name": "Ana Owner", "email": "owner@acme.example"},
    "audience": "internal",
    "releaseDefinition": {"primary": "fixversion_released", "doneStatuses": ["Done", "Closed"],
                          "pendingLabel": "Completed, pending release"},
    "window": {"tz": "Europe/London", "cadence": "weekly", "anchor": "MON 00:00", "backfillRange": None},
    "sources": {
        "tracker": {"kind": "jira", "mode": "mcp", "projects": ["ACME"], "components": ["Cards"],
                    "include": {"creators": [], "labels": []},
                    "exclude": {"labels": ["internal-only"], "creators": []}, "jqlExtra": ""},
        "deploy": {"kind": "jira_fixversion", "mode": "mcp", "repos": []},
        "comms": [{"kind": "outlook", "mode": "mcp", "include": {"subject": ["release"]}}],
    },
    "mappingRules": [{"match": {"jira.project": "ACME", "jira.component": "Cards"}}],
    "conflictPolicy": "hold",
    "template": "template.md",
    "voice": "voice.md",
    "recipients": ["team@acme.example", "Owner@acme.example", "slack:#cards-releases"],
    "delivery": {"channel": "email", "connector": "mail", "subjectPattern": "Release notes {window_start}"},
    "autoSend": {"enabled": False, "earnedAfterCleanRuns": 3},
    "purity": {"terms": []},
}


def cfg(**over):
    c = copy.deepcopy(BASE)
    for k, v in over.items():
        c[k] = v
    return c


class TenantCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rn-test-"))
        self._old = os.environ.get("RN_TENANTS_DIR")
        os.environ["RN_TENANTS_DIR"] = str(self.tmp)
        self.make_tenant("acme-cards", BASE)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("RN_TENANTS_DIR", None)
        else:
            os.environ["RN_TENANTS_DIR"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_tenant(self, slug, config, files=True):
        d = self.tmp / slug
        d.mkdir(parents=True, exist_ok=True)
        c = copy.deepcopy(config)
        if isinstance(c, dict) and "tenant" in c and c["tenant"] == "acme-cards" and slug != "acme-cards":
            c["tenant"] = slug
        (d / "config.json").write_text(json.dumps(c), encoding="utf-8")
        if files:
            (d / "template.md").write_text("# {product}\n", encoding="utf-8")
            (d / "voice.md").write_text("Plain.\n", encoding="utf-8")
        return d


ALL_PASS = {f"G{i}": "PASS" for i in range(9)}


def ready_send(tenant, run_id, body, recipients, subject, ws, we, version="v1", channel="email"):
    """Approve, record gates and prepare a send. Returns (run_hash, prepare_send result)."""
    from tools import send
    h = send.hash_run(body, recipients, subject)["run_hash"]
    send.approval_issue(tenant, run_id, h, "owner@acme.example", "yes send it")
    send.record_gates(tenant, run_id, ALL_PASS, True)
    return h, send.prepare_send(tenant, run_id, h, recipients, subject, channel, body, ws, we, version)
