"""统一 UTC 时间载体（04 基线 6.1：时间统一 timestamptz UTC）。"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)