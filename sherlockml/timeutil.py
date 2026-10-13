"""Timestamp helpers shared by results, reports and evidence manifests."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_timestamp() -> str:
    """Current UTC time as ISO 8601 with a ``Z`` suffix."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
