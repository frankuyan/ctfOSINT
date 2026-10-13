"""Shared CTF flag pattern helpers.

Flag patterns are user-configurable regexes, and the defaults contain a
capture group (``(flag|ctf|...)\\{...\\}``).  ``re.findall`` returns the
*group* when one exists, so scanning with it yields ``"flag"`` instead of
``"flag{...}"``.  Every scanner goes through :func:`find_flags`, which
always returns the full match.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

DEFAULT_FLAG_PATTERNS: tuple[str, ...] = (
    r'(flag|ctf|glug|hxp|picoCTF|HTB)\{[^}]+\}',
    r'FLAG\{[^}]+\}',
)


def compile_flag_patterns(
    patterns: Iterable[str] | None = None,
) -> list[re.Pattern[str]]:
    """Compile flag patterns case-insensitively, falling back to defaults."""
    patterns = list(patterns) if patterns else list(DEFAULT_FLAG_PATTERNS)
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def find_flags(text: str, patterns: Iterable[re.Pattern[str]]) -> list[str]:
    """Return every full flag match in ``text``, deduplicated in order."""
    found: dict[str, None] = {}
    for pattern in patterns:
        for m in pattern.finditer(text):
            found.setdefault(m.group(0), None)
    return list(found)
