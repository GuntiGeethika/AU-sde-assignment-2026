"""Sim time helpers. D0 00:00 = 2027-01-04T00:00:00+05:30; times are minutes since D0 (negative = history)."""
import datetime as dt

D0 = dt.datetime(2027, 1, 4)


def ts_to_minute(ts: str) -> int:
    t = dt.datetime.strptime(ts[:16], "%Y-%m-%dT%H:%M")
    return int((t - D0).total_seconds() // 60)


def label(minute: int) -> str:
    d, m = divmod(minute, 1440)
    return f"D{d} {m // 60:02d}:{m % 60:02d}"
