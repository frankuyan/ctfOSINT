"""Shared CTF flag pattern handling.

A single source of truth for the default flag formats and for extracting
flags from text.  Historically each subsystem (orchestrator, wayback,
github_scanner) carried its own copy of the default patterns *and* its own
extraction loop, and every copy used ``re.findall``.  With the default
pattern's alternation written as a *capturing* group —
``(flag|ctf|...)\\{...\\}`` — ``findall`` returns only the captured prefix
(``"flag"``) instead of the whole flag (``"flag{...}"``), silently
throwing away the payload the tool exists to find.

``extract_flags`` uses ``finditer`` + ``group(0)`` so it always yields the
full match, regardless of whether a (possibly user-supplied) pattern
contains capturing groups.
"""

from __future__ import annotations

import re

# Default CTF flag formats.  The alternation is a *non-capturing* group so
# that even a bare ``re.findall`` returns full matches; ``extract_flags``
# does not rely on this, but keeping it non-capturing avoids surprising any
# other caller.
DEFAULT_FLAG_PATTERNS: list[str] = [
    r"(?:flag|ctf|glug|hxp|picoCTF|HTB)\{[^}]+\}",
    r"FLAG\{[^}]+\}",
]


def compile_flag_patterns(
    patterns: list[str] | None = None,
) -> list[re.Pattern[str]]:
    """Compile flag regexes, falling back to the defaults.

    Args:
        patterns: Explicit regex strings.  When falsy, the built-in
            :data:`DEFAULT_FLAG_PATTERNS` are used.

    Returns:
        A list of case-insensitive compiled patterns.
    """
    source = patterns if patterns else DEFAULT_FLAG_PATTERNS
    return [re.compile(p, re.IGNORECASE) for p in source]


def extract_flags(
    text: str,
    compiled_patterns: list[re.Pattern[str]],
) -> list[str]:
    """Return every full flag match found in ``text``.

    Uses ``group(0)`` so the entire match is returned even when a pattern
    wraps its alternation in a capturing group (the reason the previous
    ``findall`` approach only returned the flag prefix).

    Args:
        text: Text to scan.
        compiled_patterns: Patterns from :func:`compile_flag_patterns`.

    Returns:
        Full flag strings in the order encountered (duplicates preserved;
        callers dedupe as needed).
    """
    if not text:
        return []
    found: list[str] = []
    for pattern in compiled_patterns:
        found.extend(m.group(0) for m in pattern.finditer(text))
    return found
