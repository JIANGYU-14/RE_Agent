from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_BJT = ZoneInfo("Asia/Shanghai")


def now_bjt_naive() -> datetime:
    return datetime.now(_BJT).replace(tzinfo=None)


def iso_bjt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_BJT)
    else:
        dt = dt.astimezone(_BJT)
    return dt.isoformat()
