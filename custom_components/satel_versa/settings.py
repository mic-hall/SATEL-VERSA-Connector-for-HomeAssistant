"""Validation shared by config and options flows; no network access."""

from .const import (
    CONF_DLOADX_ID,
    CONF_ETHM_KEY,
    CONF_INPUTS,
    CONF_PANEL_ID,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
)
from .protocol.session import identifier_bytes


def parse_inputs(value: str) -> list[int]:
    """Parse explicit input numbers and inclusive ranges, such as 1-8,10."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid_inputs")
    result: set[int] = set()
    for part in value.split(","):
        bounds = part.strip().split("-")
        if len(bounds) not in (1, 2) or any(
            not b.strip().isascii() or not b.strip().isdigit() for b in bounds
        ):
            raise ValueError("invalid_inputs")
        start, end = int(bounds[0]), int(bounds[-1])
        if not 1 <= start <= end <= 30:
            raise ValueError("invalid_inputs")
        result.update(range(start, end + 1))
    return sorted(result)


def validate_settings(data: dict) -> dict:
    """Normalize UI settings without silently truncating credentials."""
    result = dict(data)
    for key in (CONF_DLOADX_ID, CONF_PANEL_ID):
        try:
            identifier_bytes(data[key])
        except (KeyError, ValueError, TypeError) as err:
            raise ValueError("invalid_identifier") from err
        result[key] = data[key].upper()
    secret = data.get(CONF_ETHM_KEY, "")
    # ANSI ambiguity is deliberately excluded from this first release.
    if (
        not isinstance(secret, str)
        or not 1 <= len(secret) <= 12
        or any(not 32 <= ord(c) <= 126 for c in secret)
    ):
        raise ValueError("invalid_key")
    result[CONF_INPUTS] = parse_inputs(data[CONF_INPUTS])
    interval = data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    if (
        isinstance(interval, bool)
        or not isinstance(interval, (int, float))
        or not 1 <= interval <= 60
    ):
        raise ValueError("invalid_interval")
    result[CONF_POLL_INTERVAL] = interval
    return result
