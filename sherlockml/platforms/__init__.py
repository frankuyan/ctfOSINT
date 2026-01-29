"""Built-in platform modules for SherlockML."""

from sherlockml.platforms.github import GitHubPlatform
from sherlockml.platforms.twitter import TwitterPlatform
from sherlockml.platforms.reddit import RedditPlatform
from sherlockml.platforms.linkedin import LinkedInPlatform
from sherlockml.platforms.instagram import InstagramPlatform
from sherlockml.platforms.mastodon import MastodonPlatform
from sherlockml.platforms.hackernews import HackerNewsPlatform
from sherlockml.platforms.gitlab import GitLabPlatform
from sherlockml.platforms.keybase import KeybasePlatform
from sherlockml.platforms.pastebin import PastebinPlatform

__all__ = [
    "GitHubPlatform",
    "TwitterPlatform",
    "RedditPlatform",
    "LinkedInPlatform",
    "InstagramPlatform",
    "MastodonPlatform",
    "HackerNewsPlatform",
    "GitLabPlatform",
    "KeybasePlatform",
    "PastebinPlatform",
]
