"""Tenant config loading and hand-written validation (validate_tenant)."""
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from . import ToolError
from . import paths

TOP_KEYS = {
    "tenant", "classification", "owner", "audience", "releaseDefinition", "window",
    "sources", "mappingRules", "conflictPolicy", "template", "voice", "recipients",
    "delivery", "autoSend", "purity",
}
REQUIRED_TOP = TOP_KEYS - {"purity", "template", "voice", "conflictPolicy"}

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
CHANNEL_RE = re.compile(r"^(slack|teams):\S+$")
PLACEHOLDER_RE = re.compile(r"<[^<>]+>|REPLACE[_ ]?ME|TODO", re.I)
WEEK_ANCHOR_RE = re.compile(r"^(MON|TUE|WED|THU|FRI|SAT|SUN) ([01]\d|2[0-3]):([0-5]\d)$")
MONTH_ANCHOR_RE = re.compile(r"^(0[1-9]|1\d|2[0-8]) ([01]\d|2[0-3]):([0-5]\d)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PRIMARY = {"fixversion_released", "deploy_tag", "done_in_window"}
CADENCE = {"weekly", "fortnightly", "monthly", "on_demand"}
TRACKER_KINDS = {"jira", "linear", "ado"}
DEPLOY_KINDS = {"github_release", "gitlab_release", "jira_fixversion", "none"}
COMMS_KINDS = {"outlook", "gmail", "slack", "teams"}
MODES = {"mcp", "chrome"}
CHANNELS = {"email", "slack", "teams", "doc"}


def is_placeholder(v) -> bool:
    return isinstance(v, str) and bool(PLACEHOLDER_RE.search(v))


def is_email(s) -> bool:
    return isinstance(s, str) and bool(EMAIL_RE.match(s.strip()))


def is_channel(s) -> bool:
    return isinstance(s, str) and bool(CHANNEL_RE.match(s.strip()))


def norm_recipient(r: str) -> str:
    r = r.strip()
    if is_email(r):
        return r.lower()
    if ":" in r:
        pfx, rest = r.split(":", 1)
        return pfx.lower() + ":" + rest
    return r


def load_config(slug: str) -> dict:
    d = paths.tenant_dir(slug)
    f = d / "config.json"
    if not f.is_file():
        raise ToolError(f"tenant {slug} has no config.json")
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ToolError(f"tenant {slug} config.json is not valid JSON: {e}")
    if not isinstance(cfg, dict):
        raise ToolError(f"tenant {slug} config.json must be an object")
    return cfg


def tenant_tz(cfg: dict) -> ZoneInfo:
    try:
        return ZoneInfo(cfg["window"]["tz"])
    except Exception:
        raise ToolError("tenant window.tz is missing or not a valid IANA zone")


class _Issues:
    def __init__(self, template: bool):
        self.template = template
        self.errors, self.warnings = [], []

    def err(self, msg, value=None):
        if self.template and is_placeholder(value):
            self.warnings.append(f"placeholder: {msg}")
        else:
            self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def _str_list(iss, v, where, non_empty=False):
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        iss.err(f"{where} must be a list of strings")
        return False
    if non_empty and not v:
        iss.err(f"{where} must be non-empty")
        return False
    return True


def _obj(iss, v, where):
    if not isinstance(v, dict):
        iss.err(f"{where} must be an object")
        return False
    return True


def _enum(iss, v, allowed, where):
    if v not in allowed:
        iss.err(f"{where} must be one of {sorted(allowed)}, got {v!r}", v)
        return False
    return True


def _filter_obj(iss, v, where, keys):
    if v is None:
        return
    if not _obj(iss, v, where):
        return
    for k, val in v.items():
        if k not in keys:
            iss.err(f"{where}: unknown key {k!r}")
        elif k == "headers":
            if not isinstance(val, dict):
                iss.err(f"{where}.headers must be an object")
        else:
            _str_list(iss, val, f"{where}.{k}")


def _walk_placeholders(v, path, out):
    if isinstance(v, dict):
        for k, x in v.items():
            _walk_placeholders(x, f"{path}.{k}" if path else k, out)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            _walk_placeholders(x, f"{path}[{i}]", out)
    elif is_placeholder(v):
        out.append(path)


def validate_config(cfg, folder: Path, folder_name: str, clean_runs: int = 0) -> dict:
    template = folder_name.startswith("_")
    iss = _Issues(template)
    if not isinstance(cfg, dict):
        return {"ok": False, "errors": ["config must be a JSON object"], "warnings": []}

    for k in cfg:
        if k not in TOP_KEYS:
            iss.err(f"unknown top-level key {k!r}")
    for k in sorted(REQUIRED_TOP):
        if k not in cfg:
            iss.err(f"missing required key {k!r}")

    t = cfg.get("tenant")
    if not isinstance(t, str) or t != folder_name:
        iss.err(f"tenant field {t!r} must equal folder name {folder_name!r}", t)

    c = cfg.get("classification")
    if c is not None and _obj(iss, c, "classification"):
        for k in c:
            if k not in {"org", "client", "product", "bu", "ou"}:
                iss.err(f"classification: unknown key {k!r}")
            elif not isinstance(c[k], str):
                iss.err(f"classification.{k} must be a string")
        for k in ("org", "product"):
            if not isinstance(c.get(k), str) or not c.get(k).strip():
                iss.err(f"classification.{k} is required")

    o = cfg.get("owner")
    if o is not None and _obj(iss, o, "owner"):
        if not is_email(o.get("email")):
            iss.err(f"owner.email is not a valid email: {o.get('email')!r}", o.get("email"))
        if "name" in o and not isinstance(o["name"], str):
            iss.err("owner.name must be a string")
        if o.get("previewTo") is not None and not (is_email(o["previewTo"]) or is_channel(o["previewTo"])):
            iss.err(f"owner.previewTo must be an email or '<slack|teams>:<id>': {o['previewTo']!r}", o["previewTo"])
        for k in o:
            if k not in {"name", "email", "previewTo"}:
                iss.err(f"owner: unknown key {k!r}")

    aud = cfg.get("audience")
    if aud is not None and _enum(iss, aud, {"internal", "external"}, "audience") and aud == "external":
        iss.warn("audience is external: disclosure review will run")

    rd = cfg.get("releaseDefinition")
    primary = None
    if rd is not None and _obj(iss, rd, "releaseDefinition"):
        primary = rd.get("primary")
        _enum(iss, primary, PRIMARY, "releaseDefinition.primary")
        _str_list(iss, rd.get("doneStatuses"), "releaseDefinition.doneStatuses", non_empty=True)
        if "pendingLabel" in rd and not isinstance(rd["pendingLabel"], str):
            iss.err("releaseDefinition.pendingLabel must be a string")
        for k in rd:
            if k not in {"primary", "doneStatuses", "pendingLabel"}:
                iss.err(f"releaseDefinition: unknown key {k!r}")

    w = cfg.get("window")
    if w is not None and _obj(iss, w, "window"):
        try:
            ZoneInfo(w.get("tz"))
        except Exception:
            iss.err(f"window.tz {w.get('tz')!r} is not a loadable IANA zone", w.get("tz"))
        cad = w.get("cadence")
        if _enum(iss, cad, CADENCE, "window.cadence"):
            anchor = w.get("anchor")
            if cad in ("weekly", "fortnightly"):
                if not isinstance(anchor, str) or not WEEK_ANCHOR_RE.match(anchor):
                    iss.err(f"window.anchor must be 'DAY HH:MM' (e.g. 'MON 00:00') for {cad}", anchor)
            elif cad == "monthly":
                if not isinstance(anchor, str) or not MONTH_ANCHOR_RE.match(anchor):
                    iss.err("window.anchor must be 'DD HH:MM' with DD 01-28 for monthly", anchor)
            if cad == "fortnightly":
                ad = w.get("anchorDate")
                if not isinstance(ad, str) or not DATE_RE.match(ad):
                    iss.err("window.anchorDate (YYYY-MM-DD) is required for fortnightly cadence", ad)
        if "anchorDate" in w and w["anchorDate"] is not None:
            ad = w["anchorDate"]
            if not isinstance(ad, str) or not DATE_RE.match(ad):
                iss.err("window.anchorDate must be YYYY-MM-DD", ad)
        br = w.get("backfillRange")
        if br is not None:
            if not isinstance(br, dict) or not all(isinstance(br.get(k), str) for k in ("start", "end")):
                iss.err("window.backfillRange must be null or {start, end}")
            elif br["start"] >= br["end"]:
                iss.err("window.backfillRange.start must be before end")
        for k in w:
            if k not in {"tz", "cadence", "anchor", "anchorDate", "backfillRange"}:
                iss.err(f"window: unknown key {k!r}")

    s = cfg.get("sources")
    deploy_kind = None
    if s is not None and _obj(iss, s, "sources"):
        for k in s:
            if k not in {"tracker", "deploy", "comms"}:
                iss.err(f"sources: unknown key {k!r}")
        tr = s.get("tracker")
        if tr is None:
            iss.err("sources.tracker is required")
        elif _obj(iss, tr, "sources.tracker"):
            _enum(iss, tr.get("kind"), TRACKER_KINDS, "sources.tracker.kind")
            _enum(iss, tr.get("mode"), MODES, "sources.tracker.mode")
            _str_list(iss, tr.get("projects"), "sources.tracker.projects", non_empty=True)
            if "components" in tr:
                _str_list(iss, tr["components"], "sources.tracker.components")
            _filter_obj(iss, tr.get("include"), "sources.tracker.include", {"creators", "labels"})
            _filter_obj(iss, tr.get("exclude"), "sources.tracker.exclude", {"creators", "labels"})
            if "jqlExtra" in tr and not isinstance(tr["jqlExtra"], str):
                iss.err("sources.tracker.jqlExtra must be a string")
        dp = s.get("deploy")
        if dp is None:
            iss.err("sources.deploy is required")
        elif _obj(iss, dp, "sources.deploy"):
            deploy_kind = dp.get("kind")
            _enum(iss, deploy_kind, DEPLOY_KINDS, "sources.deploy.kind")
            if deploy_kind != "none":
                _enum(iss, dp.get("mode"), MODES, "sources.deploy.mode")
            if "repos" in dp:
                _str_list(iss, dp["repos"], "sources.deploy.repos")
            if deploy_kind in ("github_release", "gitlab_release") and not dp.get("repos"):
                iss.warn("sources.deploy.repos is empty; no releases can be fetched")
        cm = s.get("comms", [])
        if not isinstance(cm, list):
            iss.err("sources.comms must be a list")
        else:
            for i, e in enumerate(cm):
                where = f"sources.comms[{i}]"
                if not _obj(iss, e, where):
                    continue
                _enum(iss, e.get("kind"), COMMS_KINDS, f"{where}.kind")
                _enum(iss, e.get("mode"), MODES, f"{where}.mode")
                if e.get("mode") == "chrome" and not (isinstance(e.get("accountHint"), str) and e["accountHint"].strip()):
                    iss.err(f"{where}.accountHint is required when mode is chrome")
                _filter_obj(iss, e.get("include"), f"{where}.include",
                            {"subject", "senders", "folders", "channels", "headers"})
                _filter_obj(iss, e.get("exclude"), f"{where}.exclude", {"subject", "senders"})

    if rd is not None and isinstance(rd, dict) and deploy_kind is not None:
        if deploy_kind == "none" and primary != "done_in_window":
            iss.err("sources.deploy.kind 'none' is only allowed when releaseDefinition.primary is 'done_in_window'")
        if primary == "deploy_tag" and deploy_kind not in ("github_release", "gitlab_release"):
            iss.err("releaseDefinition.primary 'deploy_tag' requires sources.deploy.kind github_release or gitlab_release")

    mr = cfg.get("mappingRules")
    if mr is not None:
        if not isinstance(mr, list) or not mr:
            iss.err("mappingRules must be a non-empty list")
        else:
            for i, r in enumerate(mr):
                m = r.get("match") if isinstance(r, dict) else None
                if not isinstance(m, dict) or not m:
                    iss.err(f"mappingRules[{i}].match must be a non-empty object")
                    continue
                for k, v in m.items():
                    ok = isinstance(v, str) or (isinstance(v, list) and v and all(isinstance(x, str) for x in v))
                    if not ok:
                        iss.err(f"mappingRules[{i}].match[{k!r}] must be a string or non-empty list of strings")

    if "conflictPolicy" in cfg:
        _enum(iss, cfg["conflictPolicy"], {"hold"}, "conflictPolicy")

    for k in ("template", "voice"):
        if k in cfg:
            v = cfg[k]
            if not isinstance(v, str) or not v or "/" in v or "\\" in v or v.startswith("."):
                iss.err(f"{k} must be a plain file name in the tenant folder")
            elif not (folder / v).is_file():
                if template:
                    iss.warn(f"{k} file {v!r} not found in template folder")
                else:
                    iss.err(f"{k} file {v!r} not found in tenant folder")

    rc = cfg.get("recipients")
    n_email = 0
    if rc is not None:
        if not isinstance(rc, list):
            iss.err("recipients must be a list")
        else:
            for r in rc:
                if is_email(r):
                    n_email += 1
                elif not is_channel(r):
                    iss.err(f"recipient {r!r} is not an email or '<slack|teams>:<id>'", r)

    dl = cfg.get("delivery")
    if dl is not None and _obj(iss, dl, "delivery"):
        if dl.get("channel") == "doc":
            iss.err("doc delivery is v2; use email, slack or teams")
        else:
            _enum(iss, dl.get("channel"), CHANNELS - {"doc"}, "delivery.channel")
        for k in ("connector", "subjectPattern"):
            if not isinstance(dl.get(k), str) or not dl.get(k).strip():
                iss.err(f"delivery.{k} is required")
        if dl.get("channel") == "email" and n_email == 0:
            if template:
                iss.warn("placeholder: delivery.channel email needs at least one email recipient")
            else:
                iss.err("delivery.channel email requires at least one email recipient")
        for k in dl:
            if k not in {"channel", "connector", "subjectPattern"}:
                iss.err(f"delivery: unknown key {k!r}")

    a = cfg.get("autoSend")
    if a is not None and _obj(iss, a, "autoSend"):
        en = a.get("enabled")
        earned = a.get("earnedAfterCleanRuns")
        if not isinstance(en, bool):
            iss.err("autoSend.enabled must be a boolean")
        if not isinstance(earned, int) or isinstance(earned, bool) or earned < 1:
            iss.err("autoSend.earnedAfterCleanRuns must be an integer >= 1")
        elif en is True and clean_runs < earned:
            iss.err(f"autoSend.enabled is true but only {clean_runs} clean runs (need {earned})")

    p = cfg.get("purity")
    if p is not None:
        if not isinstance(p, dict) or not _str_list(iss, p.get("terms"), "purity.terms"):
            if not isinstance(p, dict):
                iss.err("purity must be an object with terms[]")

    holders = []
    _walk_placeholders(cfg, "", holders)
    for h in holders:
        if template:
            iss.warn(f"placeholder: {h} must be filled in")
        else:
            iss.err(f"{h} still contains a placeholder value")

    # de-duplicate while keeping order
    errors = list(dict.fromkeys(iss.errors))
    warnings = list(dict.fromkeys(iss.warnings))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def validate_path(folder: Path) -> dict:
    """Validate a tenant folder given by path (used by scripts/validate_tenant.py)."""
    from . import ledger
    folder = Path(folder).resolve()
    f = folder / "config.json"
    if not f.is_file():
        return {"ok": False, "errors": [f"no config.json in {folder}"], "warnings": []}
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"ok": False, "errors": [f"config.json is not valid JSON: {e}"], "warnings": []}
    clean = ledger.clean_run_count_at(folder)
    return validate_config(cfg, folder, folder.name, clean)


def validate_tenant(tenant: str) -> dict:
    d = paths.tenant_dir(tenant)
    return validate_path(d)
