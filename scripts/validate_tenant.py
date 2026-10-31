#!/usr/bin/env python3
"""Validate a tenant: python3 scripts/validate_tenant.py <tenant|path>. Exit 1 on any error."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "rn-harness"))

from tools import ToolError, config, paths  # noqa: E402


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    arg = argv[1]
    p = Path(arg)
    try:
        if p.is_dir() or (p.is_file() and p.name == "config.json"):
            folder = p if p.is_dir() else p.parent
            res = config.validate_path(folder)
            name = folder.resolve().name
        else:
            res = config.validate_tenant(arg)
            name = arg
    except ToolError as e:
        print(f"ERROR {e}")
        return 1
    for e in res["errors"]:
        print(f"ERROR   {e}")
    for w in res["warnings"]:
        print(f"WARNING {w}")
    print(f"{name}: {'OK' if res['ok'] else 'INVALID'} ({len(res['errors'])} errors, {len(res['warnings'])} warnings)")
    if "--json" in argv:
        print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
