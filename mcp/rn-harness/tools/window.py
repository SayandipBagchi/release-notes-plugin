"""Reporting-window resolution (resolve_window) and datetime helpers."""
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ToolError
from . import config as cfgmod
from . import paths

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def parse_dt(value, tz: ZoneInfo, field: str = "datetime") -> datetime:
    """Parse ISO date or datetime. Naive values are read in tz; result is in tz."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        s = value.strip()
        if s.endswith("Z") or s.endswith("z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            raise ToolError(f"{field} is not an ISO date/datetime: {value!r}")
    else:
        raise ToolError(f"{field} is required")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def _local(d: date, t: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, t).replace(tzinfo=tz)


def _hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _weekly(now: datetime, anchor: str, tz: ZoneInfo, days: int):
    dname, hm = anchor.split()
    t = _hhmm(hm)
    wd = DAYS.index(dname)
    d = now.date() - timedelta(days=(now.weekday() - wd) % 7)
    end = _local(d, t, tz)
    if end > now:
        end = _local(d - timedelta(days=7), t, tz)
    return _local(end.date() - timedelta(days=days), t, tz), end


def _fortnightly(now: datetime, anchor: str, anchor_date: str, tz: ZoneInfo):
    t = _hhmm(anchor.split()[1])
    base = date.fromisoformat(anchor_date)
    n = (now.date() - base).days // 14
    end = _local(base + timedelta(days=14 * n), t, tz)
    while end > now:
        n -= 1
        end = _local(base + timedelta(days=14 * n), t, tz)
    return _local(end.date() - timedelta(days=14), t, tz), end


def _prev_month(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)


def _monthly(now: datetime, anchor: str, tz: ZoneInfo):
    dd, hm = anchor.split()
    day, t = int(dd), _hhmm(hm)
    y, m = now.year, now.month
    end = _local(date(y, m, day), t, tz)
    if end > now:
        y, m = _prev_month(y, m)
        end = _local(date(y, m, day), t, tz)
    py, pm = _prev_month(y, m)
    return _local(date(py, pm, day), t, tz), end


def overlaps_for(slug: str, start: datetime, end: datetime, tz: ZoneInfo, skip_same: bool = False) -> list:
    out = []
    for rec in paths.read_jsonl(paths.runs_dir(slug) / "sent.jsonl"):
        try:
            s = parse_dt(rec.get("start"), tz)
            e = parse_dt(rec.get("end"), tz)
        except ToolError:
            continue
        if skip_same and s == start and e == end:
            continue
        if s < end and e > start:
            out.append({"run_id": rec.get("run_id"), "start": iso(s), "end": iso(e)})
    return out


def resolve_window(tenant, now=None, start=None, end=None, version="v1") -> dict:
    if not isinstance(version, str) or not re.match(r"^v[1-9]\d*$", version):
        raise ToolError(f"version must look like v1, v2, ...: {version!r}")
    correction = version != "v1"
    cfg = cfgmod.load_config(tenant)
    tz = cfgmod.tenant_tz(cfg)
    w = cfg.get("window") or {}
    cadence = w.get("cadence")
    base = {"tz": str(tz.key), "cadence": cadence, "overlaps": []}
    if (start is None) != (end is None):
        return {**base, "start": None, "end": None, "ok": False,
                "reason": "explicit windows need both start and end"}
    if start is not None:
        s, e = parse_dt(start, tz, "start"), parse_dt(end, tz, "end")
    else:
        now_dt = parse_dt(now, tz, "now") if now is not None else datetime.now(timezone.utc).astimezone(tz)
        try:
            if cadence == "weekly":
                s, e = _weekly(now_dt, w["anchor"], tz, 7)
            elif cadence == "fortnightly":
                s, e = _fortnightly(now_dt, w["anchor"], w["anchorDate"], tz)
            elif cadence == "monthly":
                s, e = _monthly(now_dt, w["anchor"], tz)
            elif cadence == "on_demand":
                return {**base, "start": None, "end": None, "ok": False,
                        "reason": "cadence on_demand needs explicit start and end"}
            else:
                return {**base, "start": None, "end": None, "ok": False,
                        "reason": f"unknown cadence {cadence!r}"}
        except (KeyError, ValueError, AttributeError) as ex:
            return {**base, "start": None, "end": None, "ok": False,
                    "reason": f"window config is invalid: {ex}"}
    if s >= e:
        return {**base, "start": iso(s), "end": iso(e), "ok": False, "reason": "start must be before end"}
    return {**base, "start": iso(s), "end": iso(e), "overlaps": overlaps_for(tenant, s, e, tz, correction),
            "ok": True}
