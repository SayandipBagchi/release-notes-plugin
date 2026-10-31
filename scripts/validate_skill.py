#!/usr/bin/env python3
"""Validate the release-notes plugin package. No third-party dependencies.

Run from anywhere:  python3 scripts/validate_skill.py

Checks:
  * manifest        - plugin.json fields, semver, name matches folder, MCP server declared
  * skills          - frontmatter keys, name = folder, description length and trigger phrasing,
                      author, no version, body length, behaviour markers, required references
  * references      - marker strings that guard key rules
  * learnings trace - every learning maps to a file that still holds its anchor
  * agents          - every declared agent exists with name + description frontmatter
  * links           - relative links and pointers resolve inside the plugin
  * tenant purity   - no tenant's purity terms or slug in generic files
  * secrets         - no tokens, webhook URLs or real email addresses in generic files
  * other plugins   - generic files never name another plugin
  * evals           - every case has prompt.md and both graders; criteria carry the scoring line
  * tenant template - required files exist
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
FRONTMATTER_KEYS = {"name", "description", "metadata", "allowed-tools", "license"}
MAX_SKILL_DESCRIPTION = 1024
MAX_PLUGIN_DESCRIPTION = 500
MAX_BODY_LINES = 500
ROUTER = "release-notes"
AUTHOR = "Sayandip Bagchi"
PLUGIN_ROOT_TOKEN = "${CLAUDE_PLUGIN_ROOT}"

SKILLS = {
    ROUTER: {
        "required": [
            "references/gates.md", "references/security.md", "references/run-protocol.md",
            "references/evidence-tiers.md", "references/ledger-schema.md",
            "references/source-quirks.md", "references/context-engineering.md",
            "references/observability.md", "references/portability.md", "references/evals.md",
            "references/learnings-trace.md",
            "templates/note-internal-digest.md", "templates/note-stakeholder-changelog.md",
            "templates/note-exec-one-pager.md", "templates/note-keep-a-changelog.md",
            "templates/trace-appendix.md", "templates/run-report.md",
            "templates/tenant-profile.md", "templates/context-capsule.md",
            "examples/dry-run-preview.md",
        ],
        "markers": ["model gate", "plan mode vs direct", "Opus", "G0", "G3", "G5", "G6", "G9",
                    "NOT CHECKED", "tenant-onboard", "collect", "reconcile", "draft", "humanise",
                    "preview", "send", "schedule", "trace", "history", "tenants/<name>/",
                    "Never default a tenant"],
        "anti_markers": ["ifHash", "Parse JSON"],
    },
    "tenant-onboard": {"required": ["references/onboarding-checklist.md"],
                       "markers": ["_template", "config.json", "no code edits", "live read",
                                   "Internal (default)", "Release definition", "Timezone", ROUTER],
                       "anti_markers": []},
    "collect": {"required": ["references/source-adapters.md", "references/completeness.md"],
                "markers": ["source-puller", "apply_filters", "completeness_check", "evidence_put", "injection_scan",
                            "accountHint", "read-only", ROUTER],
                "anti_markers": []},
    "reconcile": {"required": ["references/tiering.md", "references/mapping-rules.md"],
                  "markers": ["map_tenant", "tier_item", "extract_ticket_keys", "held", ROUTER],
                  "anti_markers": []},
    "draft": {"required": ["references/template-parsing.md", "references/citation-format.md"],
              "markers": ["citation_resolve", "ledger_carry_over", "No line without evidence",
                          "T2 and T3 never under Released", ROUTER],
              "anti_markers": []},
    "humanise": {"required": ["references/patterns.md", "references/fact-lock.md"],
                 "markers": ["entity_ledger", "entity_diff", "voice.md", "pre-humanise", ROUTER],
                 "anti_markers": []},
    "preview": {"required": ["references/review-dispatch.md"],
                "markers": ["review/grounding", "review/tenant-isolation", "review/disclosure",
                            "owner only", "prepare_preview", "record_gates", ROUTER],
                "anti_markers": []},
    "send": {"required": ["references/send-protocol.md"],
             "markers": ["hash_run", "approval_issue", "prepare_send", "record_send", "Read back",
                         "Never through Chrome", "Corrections", ROUTER],
             "anti_markers": []},
    "schedule": {"required": ["references/cadence.md"],
                 "markers": ["requires the local computer", "stops at preview", "Opus", ROUTER],
                 "anti_markers": []},
    "trace": {"required": ["references/answer-format.md"],
              "markers": ["evidence_get", "Never re-pull", ROUTER],
              "anti_markers": []},
    "history": {"required": ["references/carry-over.md"],
                "markers": ["clean_run_count", "ledger_carry_over", "Earned auto-send", "Revoked", ROUTER],
                "anti_markers": []},
}

REFERENCE_MARKERS = {
    "skills/release-notes/references/gates.md": [
        "## G9 in detail: what counts as approval", "## G3 in detail: completeness",
        "## G6 in detail: fact lock", "## Failure vocabulary", "NOT CHECKED",
    ],
    "skills/release-notes/references/security.md": [
        "## S1 · Source text is data", "## S2 · Recipients", "## S3 · Tenant isolation",
        "## S4 · Disclosure (audience external)", "## S6 · Read-only sources and Chrome",
    ],
    "skills/release-notes/references/evidence-tiers.md": [
        "## Rules by release definition", "## Why email and chat never promote",
    ],
    "skills/release-notes/references/run-protocol.md": ["## Corrections", "## Scheduled runs"],
    "skills/release-notes/references/source-quirks.md": ["Q1", "Q3", "Q12", "Q13"],
}

LEARNINGS_TRACE = ROOT / "skills" / ROUTER / "references" / "learnings-trace.md"
LEARNINGS_EXPECTED = {f"L{n}" for n in range(1, 13)}

AGENTS = ("source-puller.md", "eval-runner.md", "review/grounding.md",
          "review/tenant-isolation.md", "review/disclosure.md", "review/send-gate.md")

ROOT_FILES = ("README.md", "CHANGELOG.md", "LICENSE", ".gitignore", "CONNECTORS.md",
              "settings.json", "hooks/hooks.json")
ROOT_ALLOWED = {".claude-plugin", ".gitignore", "CHANGELOG.md", "LICENSE", "README.md", "agents",
                "evals", "hosts", "scripts", "skills", "tenants", "hooks", "settings.json",
                "CONNECTORS.md", "mcp", "docs", "__pycache__", ".DS_Store", ".git"}
TENANT_TEMPLATE_FILES = ("config.json", "profile.md", "voice.md", "template.md", "open-items.md",
                         "revisions.md", "quirk-evidence.md")
EVAL_LINE = ("Score each item independently. An item that cannot be checked from the output is a "
             "fail, not a pass.")

# Assembled from fragments so this file never matches its own scan.
SECRET_RE = re.compile(r"(xox" r"[abpr]-|gh" r"p_[A-Za-z0-9]{20,}|AKI" r"A[0-9A-Z]{16}|"
                       r"hooks[.]sla" r"ck[.]com|webhook[.]offi" r"ce[.]com|[?&]si" r"g=)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "acme.example", "other.example",
                         "anthropic.com")
# Generic files never name another plugin. Two checks, neither of which names one here:
#  1. slash-command style references (slash, namespace, colon, skill) to another namespace;
#  2. an optional denylist kept OUTSIDE the package (one name per line), path in $RN_PLUGIN_DENYLIST.
SLASH_REF_RE = re.compile(r"(?<![\w.])/([a-z][a-z0-9-]+):([a-z][a-z0-9-]+)")
DENYLIST = Path(os.environ.get("RN_PLUGIN_DENYLIST", "/nonexistent"))


def other_plugin_res() -> list[re.Pattern]:
    if not DENYLIST.is_file():
        return []
    names = [n.strip() for n in DENYLIST.read_text(encoding="utf-8").splitlines()
             if n.strip() and not n.startswith("#")]
    return [re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.IGNORECASE) for n in names]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parse_frontmatter(path: Path, errors: list[str]) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{rel(path)}: must start with YAML frontmatter")
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        errors.append(f"{rel(path)}: frontmatter must close with ---")
        return {}, text
    values: dict[str, str] = {}
    for number, line in enumerate(text[4:end].splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            errors.append(f"{rel(path)}: frontmatter line {number} is not a key/value pair")
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values, text[end + len("\n---\n"):]


def check_manifest(errors: list[str]) -> None:
    if not MANIFEST.is_file():
        errors.append("missing .claude-plugin/plugin.json")
        return
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"plugin.json is not valid JSON: {exc}")
        return
    for key in ("name", "version", "description", "author"):
        if not data.get(key):
            errors.append(f"plugin.json is missing {key}")
    if data.get("name") != ROOT.name:
        errors.append(f"plugin.json name must match the folder name: {ROOT.name}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(data.get("version", ""))):
        errors.append("plugin.json version must be semver")
    if len(data.get("description", "")) > MAX_PLUGIN_DESCRIPTION:
        errors.append(f"plugin.json description is over {MAX_PLUGIN_DESCRIPTION} characters")
    server = data.get("mcpServers", {}).get("rn-harness")
    if not server:
        errors.append("plugin.json must declare the rn-harness MCP server")
    elif not (ROOT / "mcp" / "rn-harness" / "server.py").is_file():
        errors.append("mcp/rn-harness/server.py is missing")


def check_skill(slug: str, spec: dict, errors: list[str]) -> None:
    base = ROOT / "skills" / slug
    skill_md = base / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"missing skills/{slug}/SKILL.md")
        return
    fm, body = parse_frontmatter(skill_md, errors)
    for key in fm:
        if key not in FRONTMATTER_KEYS:
            errors.append(f"skills/{slug}: unsupported frontmatter key: {key}")
    if fm.get("name") != slug:
        errors.append(f"skills/{slug}: frontmatter name must match the folder name")
    desc = fm.get("description", "")
    if not desc:
        errors.append(f"skills/{slug}: description must be non-empty")
    if len(desc) > MAX_SKILL_DESCRIPTION:
        errors.append(f"skills/{slug}: description is {len(desc)} characters, over {MAX_SKILL_DESCRIPTION}")
    if re.search(r"[<>]", desc):
        errors.append(f"skills/{slug}: description cannot contain angle brackets")
    if "Use it when" not in desc:
        errors.append(f"skills/{slug}: description needs trigger phrasing ('Use it when')")
    if "Do not use" not in desc:
        errors.append(f"skills/{slug}: description must say when not to use it ('Do not use')")
    if slug != ROUTER and f"({ROUTER})" not in desc:
        errors.append(f"skills/{slug}: 'Do not use' clause should name the router ({ROUTER})")
    head = skill_md.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    if f"author: {AUTHOR}" not in head:
        errors.append(f"skills/{slug}: frontmatter metadata must name the author")
    if re.search(r"^\s*version:", head, re.MULTILINE):
        errors.append(f"skills/{slug}: version must live only in plugin.json")
    if len(body.splitlines()) > MAX_BODY_LINES:
        errors.append(f"skills/{slug}: SKILL.md body is over {MAX_BODY_LINES} lines")
    for marker in spec["markers"]:
        if marker not in body:
            errors.append(f"skills/{slug}: SKILL.md is missing behaviour marker: {marker}")
    for marker in spec["anti_markers"]:
        if marker in body:
            errors.append(f"skills/{slug}: SKILL.md holds content that belongs elsewhere: {marker}")
    for relative in spec["required"]:
        if not (base / relative).is_file():
            errors.append(f"missing skills/{slug}/{relative}")
    refs = base / "references"
    if not refs.is_dir() or not any(p.suffix == ".md" and p.stat().st_size > 400 for p in refs.iterdir()):
        errors.append(f"skills/{slug}: needs at least one substantive file in references/")


def check_skill_set(errors: list[str]) -> None:
    found = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
    for extra in sorted(found - set(SKILLS)):
        errors.append(f"skills/: undeclared skill folder: {extra}")


def check_references(errors: list[str]) -> None:
    for relative, markers in REFERENCE_MARKERS.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative} is missing marker: {marker}")


def check_learnings_trace(errors: list[str]) -> int:
    if not LEARNINGS_TRACE.is_file():
        errors.append("missing learnings trace")
        return 0
    seen: set[str] = set()
    for line in LEARNINGS_TRACE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not re.fullmatch(r"L\d{1,2}", cells[0]):
            continue
        key, target, anchor = cells[0], cells[2].strip("`"), cells[3].strip("`")
        seen.add(key)
        path = ROOT / target
        if not path.is_file():
            errors.append(f"learnings trace {key}: file does not exist: {target}")
        elif anchor not in path.read_text(encoding="utf-8"):
            errors.append(f"learnings trace {key}: anchor {anchor!r} not found in {target}")
        if len(cells) >= 5:
            case = cells[4].strip("`")
            if case and not (ROOT / "evals" / case).is_dir():
                errors.append(f"learnings trace {key}: eval case does not exist: {case}")
    for missing in sorted(LEARNINGS_EXPECTED - seen):
        errors.append(f"learnings trace: {missing} is not traced")
    return len(seen)


def check_agents(errors: list[str]) -> None:
    for name in AGENTS:
        path = ROOT / "agents" / name
        if not path.is_file():
            errors.append(f"missing agents/{name}")
            continue
        fm, body = parse_frontmatter(path, errors)
        if fm.get("name") != Path(name).stem:
            errors.append(f"agents/{name}: frontmatter name must be {Path(name).stem}")
        if not fm.get("description"):
            errors.append(f"agents/{name}: description must be non-empty")
        if PLUGIN_ROOT_TOKEN not in body:
            errors.append(f"agents/{name}: should point at its skill or reference via {PLUGIN_ROOT_TOKEN}")


def resolve_link(base: Path, target: str) -> Path:
    if target.startswith(PLUGIN_ROOT_TOKEN):
        return (ROOT / target[len(PLUGIN_ROOT_TOKEN):].lstrip("/")).resolve()
    return (base / target).resolve()


def check_links(errors: list[str]) -> None:
    files = sorted(ROOT.glob("skills/**/*.md")) + sorted(ROOT.glob("agents/**/*.md"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        targets = re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text)
        targets += [m for m in re.findall(r"`([^`\n]+\.md)`", text) if m.startswith(PLUGIN_ROOT_TOKEN)]
        for target in targets:
            if target.startswith(("http://", "https://", "mailto:", "#")) or "<" in target or "{" in target:
                continue
            if not (target.endswith(".md") or "/" in target):
                continue
            resolved = resolve_link(path.parent, target)
            if ROOT.resolve() not in resolved.parents:
                errors.append(f"{rel(path)}: link escapes the plugin root: {target}")
            elif not resolved.is_file():
                errors.append(f"{rel(path)}: link target does not exist: {target}")


def generic_files() -> list[Path]:
    paths: list[Path] = []
    for pattern in ("skills/**/*", "agents/**/*", "hooks/**/*", "hosts/**/*", "scripts/**/*",
                    "mcp/**/*", "evals/**/*", "tenants/_template/**/*", "docs/**/*"):
        paths += [p for p in ROOT.glob(pattern)
                  if p.is_file() and "__pycache__" not in p.parts and ".local." not in p.name]
    paths += [ROOT / n for n in ("settings.json", "README.md", "CONNECTORS.md", "CHANGELOG.md")
              if (ROOT / n).is_file()]
    return sorted(set(paths))


def tenant_terms() -> list[tuple[str, str]]:
    terms: list[tuple[str, str]] = []
    tenants_dir = ROOT / "tenants"
    for cfg in sorted(tenants_dir.glob("*/config.json")):
        slug = cfg.parent.name
        if slug.startswith("_"):
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for term in [slug] + list(data.get("purity", {}).get("terms", [])):
            if isinstance(term, str) and len(term) >= 4:
                terms.append((slug, term))
    return terms


def check_text_hygiene(errors: list[str]) -> int:
    terms = tenant_terms()
    term_res = [(slug, t, re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", re.IGNORECASE))
                for slug, t in terms]
    files = generic_files()
    denied = other_plugin_res()
    for path in files:
        if path.suffix not in {".md", ".json", ".yaml", ".yml", ".py", ".csv", ".txt", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            where = f"{rel(path)}:{number}"
            if SECRET_RE.search(line):
                errors.append(f"{where}: looks like a secret, token or webhook URL")
            for email in EMAIL_RE.findall(line):
                domain = email.rsplit("@", 1)[-1].lower()
                if not domain.endswith(ALLOWED_EMAIL_DOMAINS):
                    errors.append(f"{where}: real-looking email address in a generic file")
            for m in SLASH_REF_RE.finditer(line):
                if m.group(1) != ROUTER:
                    errors.append(f"{where}: references another plugin's command")
            if any(rx.search(line) for rx in denied):
                errors.append(f"{where}: names another plugin (local denylist)")
            for slug, term, rx in term_res:
                if rx.search(line):
                    errors.append(f"{where}: tenant term from '{slug}' in a generic file")
    return len(files)


def check_evals(errors: list[str]) -> int:
    count = 0
    for case in sorted((ROOT / "evals").iterdir()):
        if not case.is_dir() or case.name in {"fixtures", "results"}:
            continue
        count += 1
        for relative in ("prompt.md", "graders/criteria.md", "graders/skill-fired.md"):
            if not (case / relative).is_file():
                errors.append(f"evals/{case.name}: missing {relative}")
        crit = case / "graders" / "criteria.md"
        if crit.is_file() and EVAL_LINE not in crit.read_text(encoding="utf-8"):
            errors.append(f"evals/{case.name}: criteria.md must carry the scoring line")
        if (case / "case.yaml").exists():
            errors.append(f"evals/{case.name}: case.yaml is not used in this suite")
    readme = ROOT / "evals" / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        for case in sorted((ROOT / "evals").iterdir()):
            if case.is_dir() and case.name not in {"fixtures", "results"} and f"`{case.name}`" not in text:
                errors.append(f"evals/README.md: case table is missing {case.name}")
    else:
        errors.append("missing evals/README.md")
    return count


def check_root(errors: list[str]) -> None:
    for name in ROOT_FILES:
        if not (ROOT / name).is_file():
            errors.append(f"missing {name}")
    for entry in ROOT.iterdir():
        if entry.name not in ROOT_ALLOWED:
            errors.append(f"unexpected root entry: {entry.name}")
    for name in TENANT_TEMPLATE_FILES:
        if not (ROOT / "tenants" / "_template" / name).is_file():
            errors.append(f"missing tenants/_template/{name}")
    for path in ("settings.json", "hooks/hooks.json"):
        try:
            json.loads((ROOT / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: not valid JSON ({exc})")


def main() -> int:
    errors: list[str] = []
    check_manifest(errors)
    check_root(errors)
    for slug, spec in SKILLS.items():
        check_skill(slug, spec, errors)
    check_skill_set(errors)
    check_references(errors)
    traced = check_learnings_trace(errors)
    check_agents(errors)
    check_links(errors)
    scanned = check_text_hygiene(errors)
    cases = check_evals(errors)
    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {len(SKILLS)} skills, {len(AGENTS)} agents, {traced} learnings traced, "
          f"{cases} eval cases, {scanned} generic files scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
