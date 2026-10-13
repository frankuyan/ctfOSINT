"""Evidence capture with integrity manifest for found profiles.

Each run writes into its own timestamped case folder so earlier captures
are never overwritten:

    <evidence_dir>/<target>_<YYYYmmddTHHMMSSZ>/
        001_github_alice.json     # API response (platforms with JSON APIs)
        002_gitlab_alice.html     # captured profile page
        manifest.json             # who/what/when + sha256 per artifact
        SHA256SUMS                # `sha256sum -c SHA256SUMS` verifies all

Hashes cover the saved artifact, so any later modification of a file is
detectable.  Page bodies are the decoded text the scanner received (not
the raw wire bytes).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sherlockml import __version__
from sherlockml.timeutil import utc_timestamp

if TYPE_CHECKING:
    from sherlockml.enum.orchestrator import SearchResult, SearchResults
    from sherlockml.enum.verify import VerificationResult

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(value: str, max_len: int = 60) -> str:
    """Make ``value`` safe to use as a single path component."""
    cleaned = _UNSAFE_CHARS.sub("_", value).strip("._") or "unknown"
    return cleaned[:max_len]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceWriter:
    """Persist found profiles plus a hash manifest for chain of custody.

    Example:
        >>> writer = EvidenceWriter(Path("cases/alice"))
        >>> case_dir = writer.write(results)
        >>> # later: cd case_dir && sha256sum -c SHA256SUMS
    """

    def __init__(self, evidence_dir: Path | str):
        self.evidence_dir = Path(evidence_dir)

    def _artifact(self, result: SearchResult) -> tuple[bytes, str, str]:
        """Return (content, extension, content type) for a found result."""
        raw = result.metadata.get("_raw_response")
        if raw:
            return raw.encode("utf-8"), ".html", "text/html"
        # API-backed platforms return structured data rather than a page;
        # preserve exactly what the check observed.
        observed = {
            "platform": result.platform,
            "username": result.username,
            "url": result.url,
            "metadata": {
                k: v for k, v in result.metadata.items() if not k.startswith("_")
            },
        }
        content = json.dumps(observed, indent=2, ensure_ascii=False, default=str)
        return content.encode("utf-8"), ".json", "application/json"

    def write(
        self,
        results: SearchResults,
        verification: list[VerificationResult] | None = None,
        proxy_used: bool = False,
    ) -> Path:
        """Write artifacts, manifest.json and SHA256SUMS; return the case folder."""
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        case_dir = self.evidence_dir / f"{_safe_name(results.query_username)}_{stamp}"
        suffix = 1
        while case_dir.exists():
            suffix += 1
            case_dir = self.evidence_dir / (
                f"{_safe_name(results.query_username)}_{stamp}_{suffix}"
            )
        case_dir.mkdir(parents=True)

        verdicts = {v.url: v for v in verification or []}
        items: list[dict[str, Any]] = []
        sums: list[str] = []

        for index, result in enumerate(results.found_results, 1):
            content, ext, content_type = self._artifact(result)
            filename = (
                f"{index:03d}_{_safe_name(result.platform)}_"
                f"{_safe_name(result.username)}{ext}"
            )
            (case_dir / filename).write_bytes(content)
            digest = sha256_bytes(content)
            sums.append(f"{digest}  {filename}")

            item: dict[str, Any] = {
                "file": filename,
                "sha256": digest,
                "size_bytes": len(content),
                "content_type": content_type,
                "platform": result.platform,
                "username": result.username,
                "url": result.url,
                "captured_at": result.checked_at,
                "confidence": round(result.confidence, 3),
                "hop": result.hop,
                "discovered_from": result.discovered_from,
            }
            verdict = verdicts.get(result.url)
            if verdict:
                item["llm_verdict"] = verdict.verdict
                item["llm_confidence"] = verdict.confidence
            items.append(item)

        manifest = {
            "tool": "sherlockml",
            "version": __version__,
            "generated_at": utc_timestamp(),
            "target": results.query_username,
            "variants_searched": results.variants_searched,
            "discoveries": results.discoveries,
            "proxy_used": proxy_used,
            "hash_algorithm": "sha256",
            "flags_found": results.flags_found,
            "contacts": results.contacts,
            "items": items,
        }
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        (case_dir / "manifest.json").write_bytes(manifest_bytes)
        sums.append(f"{sha256_bytes(manifest_bytes)}  manifest.json")

        (case_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        return case_dir
