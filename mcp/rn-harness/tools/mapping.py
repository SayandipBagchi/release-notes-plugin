"""Map source fields to a tenant (map_tenant)."""
import json
import sys

from . import ToolError
from . import paths


def _vals(v):
    if isinstance(v, str):
        return {v}
    if isinstance(v, list):
        return {x for x in v if isinstance(x, str)}
    return set()


def rule_matches(match: dict, fields: dict) -> bool:
    if not isinstance(match, dict) or not match:
        return False
    for k, rv in match.items():
        if k not in fields:
            return False
        if not (_vals(rv) & _vals(fields[k])):
            return False
    return True


def map_tenant(fields) -> dict:
    if not isinstance(fields, dict):
        raise ToolError("fields must be an object")
    root = paths.tenants_dir()
    matches = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
                continue
            if not paths.SLUG_RE.match(d.name):
                continue
            f = d / "config.json"
            if not f.is_file():
                continue
            try:
                cfg = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"map_tenant: skipping {d.name}: {e}", file=sys.stderr)
                continue
            rules = cfg.get("mappingRules") if isinstance(cfg, dict) else None
            if any(isinstance(r, dict) and rule_matches(r.get("match"), fields) for r in rules or []):
                matches.append(d.name)
    if not matches:
        return {"status": "unmapped", "tenant": None, "matches": []}
    if len(matches) > 1:
        return {"status": "conflict", "tenant": None, "matches": matches}
    return {"status": "mapped", "tenant": matches[0], "matches": matches}
