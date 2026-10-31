#!/usr/bin/env python3
"""L3 backtest: score agent output against human answer keys.

python3 scripts/backtest.py --fixtures evals/fixtures [--case NAME] [--json]

Each fixture dir holds answer-key.json and agent-output.json. A metric that cannot
be computed is NOT RUN, never PASS. Exit 1 if any metric FAILs.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp" / "rn-harness"))

from tools.entities import entity_diff  # noqa: E402

BARS = {"recall": 0.90, "precision": 0.95}
ORDER = ["recall", "precision", "false_released", "uncited_lines", "duplicates", "entity_preserved"]


def raw_counts(ak, out):
    ak_items = {i["key"]: i.get("section") for i in ak.get("items", [])}
    items = out.get("items", [])
    keys = [i.get("key") for i in items]
    uniq = list(dict.fromkeys(keys))
    c = {
        "ak_total": len(ak_items),
        "found": sum(1 for k in ak_items if k in set(keys)),
        "agent_total": len(uniq),
        "agent_in_key": sum(1 for k in uniq if k in ak_items),
        "false_released": sum(1 for i in items if i.get("section") == "released"
                              and ak_items.get(i.get("key")) != "released"),
        "uncited_lines": sum(1 for i in items if not i.get("evidence_ids")) + int(out.get("lines_uncited") or 0),
        "duplicates": len(keys) - len(uniq),
        "entity_runs": 0, "entity_fail": 0, "entity_detail": None,
        "misses": [k for k in ak_items if k not in set(keys)],
        "false_items": [k for k in uniq if k not in ak_items],
    }
    h = out.get("humanise")
    if isinstance(h, dict) and isinstance(h.get("before"), str) and isinstance(h.get("after"), str):
        d = entity_diff(h["before"], h["after"])
        c["entity_runs"] = 1
        c["entity_fail"] = 0 if d["equal"] else 1
        if not d["equal"]:
            c["entity_detail"] = {"added": d["added"], "removed": d["removed"]}
    return c


def metrics(c):
    m = {}
    m["recall"] = (c["found"] / c["ak_total"]) if c["ak_total"] else None
    m["precision"] = (c["agent_in_key"] / c["agent_total"]) if c["agent_total"] else None
    m["false_released"] = c["false_released"]
    m["uncited_lines"] = c["uncited_lines"]
    m["duplicates"] = c["duplicates"]
    m["entity_preserved"] = None if not c["entity_runs"] else c["entity_fail"] == 0
    verdict = {}
    for k in ORDER:
        v = m[k]
        if v is None:
            verdict[k] = "NOT RUN"
        elif k in BARS:
            verdict[k] = "PASS" if v >= BARS[k] else "FAIL"
        elif k == "entity_preserved":
            verdict[k] = "PASS" if v is True else "FAIL"
        else:
            verdict[k] = "PASS" if v == 0 else "FAIL"
    return m, verdict


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description="release-notes L3 backtest")
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--case")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.fixtures)
    cases = sorted(d for d in root.iterdir() if d.is_dir() and (d / "answer-key.json").is_file()) if root.is_dir() else []
    if a.case:
        cases = [d for d in cases if d.name == a.case]
    if not cases:
        print(f"no fixtures found under {root}" + (f" for case {a.case}" if a.case else ""), file=sys.stderr)
        return 1
    results, total = {}, None
    for d in cases:
        ak = json.loads((d / "answer-key.json").read_text(encoding="utf-8"))
        op = d / "agent-output.json"
        if not op.is_file():
            results[d.name] = {"error": "agent-output.json missing", "verdict": {k: "NOT RUN" for k in ORDER}}
            continue
        c = raw_counts(ak, json.loads(op.read_text(encoding="utf-8")))
        m, v = metrics(c)
        results[d.name] = {"metrics": m, "verdict": v, "misses": c["misses"], "false_items": c["false_items"],
                           "entity_diff": c["entity_detail"]}
        if total is None:
            total = {k: 0 for k in c if isinstance(c[k], int)}
        for k in total:
            total[k] += c[k]
    if total is not None:
        tm, tv = metrics(total)
        results["TOTAL"] = {"metrics": tm, "verdict": tv}
    any_fail = any(r["verdict"][k] == "FAIL" for r in results.values() for k in ORDER)
    if a.json:
        print(json.dumps({"results": results, "pass": not any_fail}, indent=2))
    else:
        w = max(len(n) for n in results) + 2
        print("case".ljust(w) + "".join(k.ljust(22) for k in ORDER))
        for name, r in results.items():
            cells = []
            for k in ORDER:
                val = fmt(r.get("metrics", {}).get(k))
                cells.append(f"{r['verdict'][k]} ({val})".ljust(22) if r["verdict"][k] != "NOT RUN" else "NOT RUN".ljust(22))
            print(name.ljust(w) + "".join(cells))
            if r.get("misses"):
                print(" " * w + f"missed: {', '.join(r['misses'])}")
            if r.get("false_items"):
                print(" " * w + f"not in answer key: {', '.join(r['false_items'])}")
            if r.get("error"):
                print(" " * w + r["error"])
        print(f"bars: recall>={BARS['recall']}, precision>={BARS['precision']}, false_released=0, "
              f"uncited_lines=0, duplicates=0, entity_preserved=true")
        print("RESULT: " + ("FAIL" if any_fail else "PASS"))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
