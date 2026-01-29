"""Data extraction modules for SherlockML."""

from sherlockml.extract.github_scanner import GitHubScanner
from sherlockml.extract.wayback import WaybackIntegration
from sherlockml.extract.social_parser import SocialMediaParser

__all__ = [
    "GitHubScanner",
    "WaybackIntegration",
    "SocialMediaParser",
]
