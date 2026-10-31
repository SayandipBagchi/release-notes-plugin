"""Path resolution. Every write path is resolved inside the tenants directory."""
import json
import os
import re
from pathlib import Path

from . import ToolError

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TEMPLATE_SLUG_RE = re.compile(r"^_template([a-z0-9-]*)$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    # tools/ -> rn-harness/ -> mcp/ -> plugin root
    return Path(__file__).resolve().parents[3]


def tenants_dir() -> Path:
    env = os.environ.get("RN_TENANTS_DIR")
    if env:
        return Path(env).resolve()
    return plugin_root() / "tenants"


def is_template_slug(slug: str) -> bool:
    return isinstance(slug, str) and slug.startswith("_")


def check_slug(slug) -> str:
    if not isinstance(slug, str) or not (SLUG_RE.match(slug) or TEMPLATE_SLUG_RE.match(slug)):
        raise ToolError(f"invalid tenant slug: {slug!r}")
    return slug


def check_run_id(run_id) -> str:
    if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
        raise ToolError(f"invalid run_id: {run_id!r}")
    return run_id


def _inside(base: Path, p: Path) -> Path:
    base_r = base.resolve()
    p_r = p.resolve()
    if p_r != base_r and base_r not in p_r.parents:
        raise ToolError("path escapes the tenants directory")
    return p_r


def tenant_dir(slug: str, must_exist: bool = True) -> Path:
    check_slug(slug)
    root = tenants_dir()
    d = _inside(root, root / slug)
    if must_exist and not d.is_dir():
        raise ToolError(f"unknown tenant: {slug}")
    return d


def runs_dir(slug: str) -> Path:
    return _inside(tenants_dir(), tenant_dir(slug) / "runs")


def run_dir(slug: str, run_id: str) -> Path:
    check_run_id(run_id)
    return _inside(tenants_dir(), runs_dir(slug) / run_id)


def ensure_dir(p: Path) -> Path:
    _inside(tenants_dir(), p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_jsonl(path: Path, records: list) -> None:
    ensure_dir(path.parent)
    _inside(tenants_dir(), path)
    with path.open("a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, obj) -> None:
    ensure_dir(path.parent)
    _inside(tenants_dir(), path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
