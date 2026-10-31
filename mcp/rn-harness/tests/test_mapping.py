import unittest

from helpers import TenantCase, cfg
from tools import mapping


class MapTenant(TenantCase):
    def test_mapped(self):
        r = mapping.map_tenant({"jira.project": "ACME", "jira.component": "Cards"})
        self.assertEqual(r, {"status": "mapped", "tenant": "acme-cards", "matches": ["acme-cards"]})

    def test_partial_fields_unmapped(self):
        self.assertEqual(mapping.map_tenant({"jira.project": "ACME"})["status"], "unmapped")
        self.assertEqual(mapping.map_tenant({"jira.project": "acme", "jira.component": "Cards"})["status"], "unmapped")

    def test_list_any_of_and_conflict(self):
        self.make_tenant("acme-pay", cfg(mappingRules=[{"match": {"jira.project": ["ACME", "PAY"]}}]))
        r = mapping.map_tenant({"jira.project": "PAY"})
        self.assertEqual(r["tenant"], "acme-pay")
        r = mapping.map_tenant({"jira.project": "ACME", "jira.component": ["Cards", "Web"]})
        self.assertEqual(r["status"], "conflict")
        self.assertIsNone(r["tenant"])
        self.assertEqual(r["matches"], ["acme-cards", "acme-pay"])

    def test_template_skipped(self):
        self.make_tenant("_template", cfg(tenant="_template", mappingRules=[{"match": {"jira.project": "ZZZ"}}]))
        self.assertEqual(mapping.map_tenant({"jira.project": "ZZZ"})["status"], "unmapped")


if __name__ == "__main__":
    unittest.main()
