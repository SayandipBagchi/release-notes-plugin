import json
import unittest

from helpers import BASE, PLUGIN_ROOT, TenantCase, cfg
from tools import ToolError, config, ledger


class ValidateTenant(TenantCase):
    def v(self, c, slug="acme-cards", files=True):
        self.make_tenant(slug, c, files)
        return config.validate_tenant(slug)

    def test_valid(self):
        r = config.validate_tenant("acme-cards")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["warnings"], [])

    def test_unknown_top_key(self):
        r = self.v(cfg(extra=1))
        self.assertFalse(r["ok"])
        self.assertTrue(any("unknown top-level key" in e for e in r["errors"]))

    def test_tenant_must_equal_folder(self):
        r = self.v(cfg(tenant="other"))
        self.assertTrue(any("folder name" in e for e in r["errors"]))

    def test_deploy_none_requires_done_in_window(self):
        s = json.loads(json.dumps(BASE["sources"]))
        s["deploy"] = {"kind": "none"}
        r = self.v(cfg(sources=s))
        self.assertTrue(any("'none'" in e for e in r["errors"]))
        r = self.v(cfg(sources=s, releaseDefinition={"primary": "done_in_window", "doneStatuses": ["Done"]}))
        self.assertTrue(r["ok"], r)

    def test_deploy_tag_requires_release_kind(self):
        r = self.v(cfg(releaseDefinition={"primary": "deploy_tag", "doneStatuses": ["Done"]}))
        self.assertTrue(any("deploy_tag" in e for e in r["errors"]))

    def test_bad_tz(self):
        r = self.v(cfg(window={"tz": "Mars/Base", "cadence": "weekly", "anchor": "MON 00:00"}))
        self.assertTrue(any("tz" in e for e in r["errors"]))

    def test_fortnightly_needs_anchor_date(self):
        r = self.v(cfg(window={"tz": "UTC", "cadence": "fortnightly", "anchor": "MON 00:00"}))
        self.assertTrue(any("anchorDate" in e for e in r["errors"]))

    def test_bad_anchor(self):
        r = self.v(cfg(window={"tz": "UTC", "cadence": "weekly", "anchor": "Monday"}))
        self.assertFalse(r["ok"])

    def test_recipients(self):
        r = self.v(cfg(recipients=["not-an-email", "slack:#x", "teams:abc"]))
        self.assertEqual(len([e for e in r["errors"] if "is not an email" in e]), 1)

    def test_email_channel_needs_email_recipient(self):
        r = self.v(cfg(recipients=["slack:#x"]))
        self.assertTrue(any("at least one email" in e for e in r["errors"]))

    def test_preview_to(self):
        self.assertTrue(self.v(cfg(owner={"email": "owner@acme.example", "previewTo": "slack:U123"}))["ok"])
        r = self.v(cfg(owner={"email": "owner@acme.example", "previewTo": "someone"}))
        self.assertTrue(any("previewTo" in e for e in r["errors"]))

    def test_doc_channel_is_v2(self):
        r = self.v(cfg(delivery={"channel": "doc", "connector": "docs", "subjectPattern": "x"}))
        self.assertIn("doc delivery is v2; use email, slack or teams", r["errors"])

    def test_owner_email(self):
        r = self.v(cfg(owner={"name": "x", "email": "nope"}))
        self.assertTrue(any("owner.email" in e for e in r["errors"]))

    def test_comms_chrome_needs_account_hint(self):
        s = json.loads(json.dumps(BASE["sources"]))
        s["comms"] = [{"kind": "gmail", "mode": "chrome"}]
        r = self.v(cfg(sources=s))
        self.assertTrue(any("accountHint" in e for e in r["errors"]))

    def test_empty_projects_and_mapping(self):
        s = json.loads(json.dumps(BASE["sources"]))
        s["tracker"]["projects"] = []
        r = self.v(cfg(sources=s, mappingRules=[]))
        self.assertTrue(any("projects" in e for e in r["errors"]))
        self.assertTrue(any("mappingRules" in e for e in r["errors"]))

    def test_missing_template_file(self):
        r = self.v(BASE, slug="acme-bare", files=False)
        self.assertTrue(any("template file" in e for e in r["errors"]))

    def test_external_warns(self):
        r = self.v(cfg(audience="external"))
        self.assertTrue(r["ok"])
        self.assertTrue(any("disclosure review will run" in w for w in r["warnings"]))

    def test_autosend_needs_clean_runs(self):
        c = cfg(autoSend={"enabled": True, "earnedAfterCleanRuns": 2})
        r = self.v(c)
        self.assertTrue(any("autoSend" in e for e in r["errors"]))
        for i in range(2):
            ledger.run_log_append("acme-cards", {"run_id": f"r{i}", "status": "sent", "model": "m", "edits": 0})
        self.assertTrue(config.validate_tenant("acme-cards")["ok"])

    def test_placeholder_in_real_tenant_is_error(self):
        r = self.v(cfg(classification={"org": "<org>", "product": "cards"}))
        self.assertFalse(r["ok"])

    def test_template_tenant_placeholders_are_warnings(self):
        tpl = json.loads((PLUGIN_ROOT / "tenants" / "_template" / "config.json").read_text())
        self.make_tenant("_template", tpl, files=False)
        r = config.validate_tenant("_template")
        self.assertTrue(r["ok"], r["errors"])
        self.assertTrue(any(w.startswith("placeholder") for w in r["warnings"]))
        self.assertFalse(tpl["autoSend"]["enabled"])
        self.assertEqual(tpl["recipients"], [])
        self.assertEqual(tpl["autoSend"]["earnedAfterCleanRuns"], 3)

    def test_bad_slug_and_traversal(self):
        for s in ("../etc", "Acme", "acme/../x", "", "a_b"):
            with self.assertRaises(ToolError):
                config.validate_tenant(s)

    def test_unknown_tenant(self):
        with self.assertRaises(ToolError):
            config.validate_tenant("nobody")


if __name__ == "__main__":
    unittest.main()
