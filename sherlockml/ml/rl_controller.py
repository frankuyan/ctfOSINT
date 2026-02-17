"""Reinforcement Learning controller for platform prioritization."""

from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class PlatformStats:
    """Statistics for a platform's performance."""
    name: str
    successes: int
    failures: int
    total_searches: int
    avg_response_time: float
    last_updated: str
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_searches == 0:
            return 0.5  # Prior
        return self.successes / self.total_searches
    
    @property
    def thompson_sample(self) -> float:
        """Sample from Beta distribution for Thompson Sampling."""
        # Beta distribution with success/failure as shape parameters
        # Add 1 to both for prior smoothing
        return np.random.beta(self.successes + 1, self.failures + 1)


class RLController:
    """Multi-armed bandit for platform priority learning.
    
    Uses Thompson Sampling to balance exploration vs exploitation
    when selecting which platforms to prioritize. Updates based on
    whether a flag was found on each platform.
    
    Example:
        >>> rl = RLController(db_path=Path("~/.sherlockml/rl_weights.db"))
        >>> top_platforms = rl.select_platforms(available_platforms, n=10)
        >>> # After search...
        >>> rl.update("github", flag_found=True)
        >>> rl.update("twitter", flag_found=False)
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS platform_stats (
        name TEXT PRIMARY KEY,
        successes INTEGER DEFAULT 0,
        failures INTEGER DEFAULT 0,
        total_searches INTEGER DEFAULT 0,
        total_response_time REAL DEFAULT 0.0,
        last_updated TEXT
    );
    
    CREATE TABLE IF NOT EXISTS training_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        platform TEXT,
        flag_found INTEGER,
        response_time REAL,
        context TEXT
    );
    """
    
    def __init__(
        self,
        db_path: Path | str,
        learning_rate: float = 0.1,
    ):
        """Initialize the RL controller.
        
        Args:
            db_path: Path to SQLite database
            learning_rate: Learning rate for updates (0.0-1.0)
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.learning_rate = learning_rate
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()
    
    def get_stats(self, platform: str) -> PlatformStats:
        """Get statistics for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            PlatformStats object
        """
        cursor = self.conn.execute(
            """
            SELECT name, successes, failures, total_searches, 
                   total_response_time, last_updated
            FROM platform_stats WHERE name = ?
            """,
            (platform,),
        )
        row = cursor.fetchone()
        
        if row is None:
            return PlatformStats(
                name=platform,
                successes=0,
                failures=0,
                total_searches=0,
                avg_response_time=0.0,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
        
        total_time = row[4] or 0.0
        total_searches = row[3] or 0
        avg_time = total_time / total_searches if total_searches > 0 else 0.0
        
        return PlatformStats(
            name=row[0],
            successes=row[1],
            failures=row[2],
            total_searches=total_searches,
            avg_response_time=avg_time,
            last_updated=row[5] or datetime.now(timezone.utc).isoformat(),
        )
    
    def get_all_stats(self) -> list[PlatformStats]:
        """Get statistics for all platforms.
        
        Returns:
            List of PlatformStats objects
        """
        cursor = self.conn.execute(
            """
            SELECT name, successes, failures, total_searches,
                   total_response_time, last_updated
            FROM platform_stats
            ORDER BY successes DESC
            """
        )
        
        stats = []
        for row in cursor.fetchall():
            total_time = row[4] or 0.0
            total_searches = row[3] or 0
            avg_time = total_time / total_searches if total_searches > 0 else 0.0
            
            stats.append(PlatformStats(
                name=row[0],
                successes=row[1],
                failures=row[2],
                total_searches=total_searches,
                avg_response_time=avg_time,
                last_updated=row[5] or "",
            ))
        
        return stats
    
    def select_platforms(
        self,
        available: list[str],
        n: int = 10,
        use_thompson: bool = True,
    ) -> list[str]:
        """Select top platforms using Thompson Sampling.
        
        Args:
            available: List of available platform names
            n: Number of platforms to select
            use_thompson: Use Thompson Sampling (else just top performers)
            
        Returns:
            List of selected platform names, ordered by priority
        """
        if not available:
            return []
        
        if len(available) <= n:
            return available
        
        # Get stats for all available platforms
        platform_scores: list[tuple[str, float]] = []
        
        for platform in available:
            stats = self.get_stats(platform)
            
            if use_thompson:
                score = stats.thompson_sample
            else:
                score = stats.success_rate
            
            platform_scores.append((platform, score))
        
        # Sort by score descending
        platform_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [p[0] for p in platform_scores[:n]]
    
    def update(
        self,
        platform: str,
        flag_found: bool,
        response_time: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Update platform statistics after a search.
        
        Args:
            platform: Platform name
            flag_found: Whether a flag was found
            response_time: Request response time
            context: Optional context for training history
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Upsert platform stats with learning rate weighting
        # When learning_rate < 1.0, recent observations are weighted more
        # by scaling down historical counts before adding new observation
        lr = self.learning_rate
        decay = 1.0 - lr  # decay factor for historical counts
        success_val = 1 if flag_found else 0
        failure_val = 0 if flag_found else 1

        self.conn.execute(
            """
            INSERT INTO platform_stats (name, successes, failures, total_searches,
                                         total_response_time, last_updated)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                successes = CAST(successes * ? AS INTEGER) + ?,
                failures = CAST(failures * ? AS INTEGER) + ?,
                total_searches = total_searches + 1,
                total_response_time = total_response_time + ?,
                last_updated = ?
            """,
            (
                platform,
                success_val,
                failure_val,
                response_time,
                now,
                decay,
                success_val,
                decay,
                failure_val,
                response_time,
                now,
            ),
        )
        
        # Record in training history
        self.conn.execute(
            """
            INSERT INTO training_history (timestamp, platform, flag_found,
                                          response_time, context)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                now,
                platform,
                1 if flag_found else 0,
                response_time,
                json.dumps(context) if context else None,
            ),
        )
        
        self.conn.commit()
    
    def train(
        self,
        dataset_path: Path | str,
        epochs: int = 50,
    ) -> dict[str, Any]:
        """Batch training on historical CTF data.
        
        The dataset should be a JSON file with format:
        [
            {
                "platforms": {"github": true, "twitter": false, ...},
                "context": {...}
            },
            ...
        ]
        
        Args:
            dataset_path: Path to JSON dataset
            epochs: Number of training epochs
            
        Returns:
            Training statistics
        """
        dataset_path = Path(dataset_path).expanduser()
        
        with open(dataset_path) as f:
            data = json.load(f)
        
        total_updates = 0
        
        for epoch in range(epochs):
            # Shuffle data each epoch
            random.shuffle(data)
            
            for entry in data:
                platforms = entry.get("platforms", {})
                context = entry.get("context", {})
                
                for platform, flag_found in platforms.items():
                    self.update(
                        platform=platform,
                        flag_found=flag_found,
                        context=context,
                    )
                    total_updates += 1
        
        return {
            "epochs": epochs,
            "entries": len(data),
            "total_updates": total_updates,
        }
    
    def export_weights(self) -> dict[str, float]:
        """Export current platform weights.
        
        Returns:
            Dictionary of platform -> success_rate
        """
        stats = self.get_all_stats()
        return {s.name: s.success_rate for s in stats}
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.conn.execute("DELETE FROM platform_stats")
        self.conn.execute("DELETE FROM training_history")
        self.conn.commit()
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self) -> "RLController":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
