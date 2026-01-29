"""JSON reporter with confidence scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sherlockml.enum.orchestrator import SearchResult, SearchResults


@dataclass
class ConfidenceWeights:
    """Weights for confidence calculation."""
    platform_reliability: float = 0.4
    pattern_matches: float = 0.3
    cross_platform_correlation: float = 0.3


class JSONReporter:
    """JSON output with confidence scoring.
    
    Generates structured JSON reports with calculated confidence
    scores based on platform reliability, pattern matches, and
    cross-platform correlation.
    
    Confidence = platform_reliability × pattern_matches × cross_platform_correlation
    
    Example:
        >>> reporter = JSONReporter()
        >>> report = reporter.generate_report(search_results)
        >>> reporter.save(report, Path("results.json"))
    """
    
    # Platform reliability scores (based on API quality, false positive rates)
    PLATFORM_RELIABILITY = {
        "github": 0.95,
        "gitlab": 0.92,
        "keybase": 0.90,
        "hackernews": 0.88,
        "reddit": 0.85,
        "linkedin": 0.80,
        "twitter": 0.75,
        "instagram": 0.70,
        "mastodon": 0.85,
        "pastebin": 0.65,
    }
    
    DEFAULT_RELIABILITY = 0.60
    
    def __init__(
        self,
        weights: ConfidenceWeights | None = None,
        include_raw: bool = False,
        pretty_print: bool = True,
    ):
        """Initialize the reporter.
        
        Args:
            weights: Custom confidence weights
            include_raw: Include raw response data
            pretty_print: Format JSON with indentation
        """
        self.weights = weights or ConfidenceWeights()
        self.include_raw = include_raw
        self.pretty_print = pretty_print
    
    def calculate_confidence(
        self,
        result: "SearchResult",
        all_results: list["SearchResult"] | None = None,
    ) -> float:
        """Calculate confidence score for a single result.
        
        Confidence = platform_reliability × pattern_matches × cross_platform_correlation
        
        Args:
            result: Single search result
            all_results: All results for correlation analysis
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Platform reliability
        platform_score = self.PLATFORM_RELIABILITY.get(
            result.platform.lower(),
            self.DEFAULT_RELIABILITY
        )
        
        # Pattern matches (based on metadata richness)
        metadata_score = self._score_metadata(result.metadata)
        
        # Cross-platform correlation
        correlation_score = 1.0
        if all_results:
            correlation_score = self._score_correlation(result, all_results)
        
        # Weighted combination
        confidence = (
            platform_score * self.weights.platform_reliability +
            metadata_score * self.weights.pattern_matches +
            correlation_score * self.weights.cross_platform_correlation
        )
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))
    
    def _score_metadata(self, metadata: dict[str, Any]) -> float:
        """Score metadata richness.
        
        Higher score for more detailed metadata with useful fields.
        """
        if not metadata:
            return 0.3
        
        valuable_fields = ['bio', 'email', 'location', 'name', 'created_at', 'followers']
        filled_fields = sum(1 for f in valuable_fields if metadata.get(f))
        
        return min(1.0, 0.3 + (filled_fields / len(valuable_fields)) * 0.7)
    
    def _score_correlation(
        self,
        result: "SearchResult",
        all_results: list["SearchResult"],
    ) -> float:
        """Score cross-platform correlation.
        
        Higher score if same username found on multiple platforms.
        """
        username = result.username.lower()
        
        # Count platforms with matching username
        matching_platforms = sum(
            1 for r in all_results
            if r.exists and r.username.lower() == username
        )
        
        if matching_platforms <= 1:
            return 0.5
        elif matching_platforms <= 3:
            return 0.7
        elif matching_platforms <= 5:
            return 0.85
        else:
            return 1.0
    
    def generate_report(
        self,
        results: "SearchResults",
        include_negative: bool = False,
    ) -> dict[str, Any]:
        """Generate structured JSON report.
        
        Args:
            results: Search results to report
            include_negative: Include platforms where username wasn't found
            
        Returns:
            Dictionary ready for JSON serialization
        """
        # Filter results
        filtered = [r for r in results.results if r.exists or include_negative]
        
        # Calculate confidence for each
        result_entries = []
        for result in filtered:
            confidence = self.calculate_confidence(result, results.results)
            
            entry = {
                "platform": result.platform,
                "username": result.username,
                "exists": result.exists,
                "url": result.url,
                "confidence_score": round(confidence, 3),
                "response_time_ms": round(result.response_time * 1000, 2),
            }
            
            if result.metadata:
                entry["metadata"] = result.metadata
            
            if result.error:
                entry["error"] = result.error
            
            result_entries.append(entry)
        
        # Sort by confidence
        result_entries.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        report = {
            "sherlockml_version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "query": {
                "target_username": results.query_username,
                "variants_searched": results.variants_searched,
            },
            "summary": {
                "total_platforms_checked": results.total_platforms,
                "successful_checks": results.successful_checks,
                "profiles_found": results.found_count,
                "flags_found": len(results.flags_found),
                "elapsed_time_seconds": round(results.elapsed_time, 2),
            },
            "results": result_entries,
        }
        
        if results.flags_found:
            report["flags"] = results.flags_found
        
        if results.errors:
            report["errors"] = results.errors[:20]  # Limit error list
        
        return report
    
    def save(
        self,
        report: dict[str, Any],
        output_path: Path | str,
    ) -> None:
        """Save report to JSON file.
        
        Args:
            report: Report dictionary
            output_path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        indent = 2 if self.pretty_print else None
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=indent, ensure_ascii=False)
    
    def to_json_string(self, report: dict[str, Any]) -> str:
        """Convert report to JSON string.
        
        Args:
            report: Report dictionary
            
        Returns:
            JSON string
        """
        indent = 2 if self.pretty_print else None
        return json.dump(report, indent=indent, ensure_ascii=False)
