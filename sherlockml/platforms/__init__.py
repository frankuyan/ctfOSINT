"""Built-in platform modules for SherlockML."""

# --- Original 10 ---
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

# --- Social ---
from sherlockml.platforms.snapchat import SnapchatPlatform
from sherlockml.platforms.telegram import TelegramPlatform
from sherlockml.platforms.discord import DiscordPlatform
from sherlockml.platforms.tumblr import TumblrPlatform
from sherlockml.platforms.threads import ThreadsPlatform
from sherlockml.platforms.bluesky import BlueskyPlatform
from sherlockml.platforms.askfm import AskFmPlatform
from sherlockml.platforms.imgur import ImgurPlatform

# --- Video ---
from sherlockml.platforms.youtube import YouTubePlatform
from sherlockml.platforms.tiktok import TikTokPlatform
from sherlockml.platforms.twitch import TwitchPlatform
from sherlockml.platforms.vimeo import VimeoPlatform
from sherlockml.platforms.dailymotion import DailymotionPlatform

# --- Code / Dev ---
from sherlockml.platforms.bitbucket import BitbucketPlatform
from sherlockml.platforms.stackoverflow import StackOverflowPlatform
from sherlockml.platforms.devto import DevToPlatform
from sherlockml.platforms.codepen import CodePenPlatform
from sherlockml.platforms.replit import ReplitPlatform
from sherlockml.platforms.npm import NpmPlatform
from sherlockml.platforms.pypi import PyPIPlatform
from sherlockml.platforms.dockerhub import DockerHubPlatform
from sherlockml.platforms.rubygems import RubyGemsPlatform
from sherlockml.platforms.cratesio import CratesIOPlatform
from sherlockml.platforms.kaggle import KagglePlatform
from sherlockml.platforms.leetcode import LeetCodePlatform
from sherlockml.platforms.codeforces import CodeforcesPlatform
from sherlockml.platforms.hashnode import HashnodePlatform
from sherlockml.platforms.gitea import GiteaPlatform
from sherlockml.platforms.gist import GistPlatform
from sherlockml.platforms.hackerone import HackerOnePlatform

# --- CTF / Security ---
from sherlockml.platforms.tryhackme import TryHackMePlatform
from sherlockml.platforms.hackthebox import HackTheBoxPlatform

# --- Creative ---
from sherlockml.platforms.pinterest import PinterestPlatform
from sherlockml.platforms.medium import MediumPlatform
from sherlockml.platforms.dribbble import DribbblePlatform
from sherlockml.platforms.behance import BehancePlatform
from sherlockml.platforms.deviantart import DeviantArtPlatform
from sherlockml.platforms.wordpress import WordPressPlatform
from sherlockml.platforms.wattpad import WattpadPlatform
from sherlockml.platforms.newgrounds import NewgroundsPlatform
from sherlockml.platforms.substack import SubstackPlatform
from sherlockml.platforms.buymeacoffee import BuyMeACoffeePlatform
from sherlockml.platforms.patreon import PatreonPlatform

# --- Music ---
from sherlockml.platforms.soundcloud import SoundCloudPlatform
from sherlockml.platforms.spotify import SpotifyPlatform
from sherlockml.platforms.mixcloud import MixcloudPlatform

# --- Gaming ---
from sherlockml.platforms.steam import SteamPlatform
from sherlockml.platforms.roblox import RobloxPlatform
from sherlockml.platforms.xboxgamertag import XboxGamertagPlatform
from sherlockml.platforms.chess import ChessComPlatform
from sherlockml.platforms.lichess import LichessPlatform

# --- Professional ---
from sherlockml.platforms.aboutme import AboutMePlatform
from sherlockml.platforms.slideshare import SlideSharePlatform
from sherlockml.platforms.trello import TrelloPlatform
from sherlockml.platforms.producthunt import ProductHuntPlatform

# --- Forum / News ---
from sherlockml.platforms.quora import QuoraPlatform
from sherlockml.platforms.lobsters import LobstersPlatform

# --- Other ---
from sherlockml.platforms.gravatar import GravatarPlatform
from sherlockml.platforms.linktree import LinktreePlatform

__all__ = [
    # Original 10
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
    # Social
    "SnapchatPlatform",
    "TelegramPlatform",
    "DiscordPlatform",
    "TumblrPlatform",
    "ThreadsPlatform",
    "BlueskyPlatform",
    "AskFmPlatform",
    "ImgurPlatform",
    # Video
    "YouTubePlatform",
    "TikTokPlatform",
    "TwitchPlatform",
    "VimeoPlatform",
    "DailymotionPlatform",
    # Code / Dev
    "BitbucketPlatform",
    "StackOverflowPlatform",
    "DevToPlatform",
    "CodePenPlatform",
    "ReplitPlatform",
    "NpmPlatform",
    "PyPIPlatform",
    "DockerHubPlatform",
    "RubyGemsPlatform",
    "CratesIOPlatform",
    "KagglePlatform",
    "LeetCodePlatform",
    "CodeforcesPlatform",
    "HashnodePlatform",
    "GiteaPlatform",
    "GistPlatform",
    "HackerOnePlatform",
    # CTF / Security
    "TryHackMePlatform",
    "HackTheBoxPlatform",
    # Creative
    "PinterestPlatform",
    "MediumPlatform",
    "DribbblePlatform",
    "BehancePlatform",
    "DeviantArtPlatform",
    "WordPressPlatform",
    "WattpadPlatform",
    "NewgroundsPlatform",
    "SubstackPlatform",
    "BuyMeACoffeePlatform",
    "PatreonPlatform",
    # Music
    "SoundCloudPlatform",
    "SpotifyPlatform",
    "MixcloudPlatform",
    # Gaming
    "SteamPlatform",
    "RobloxPlatform",
    "XboxGamertagPlatform",
    "ChessComPlatform",
    "LichessPlatform",
    # Professional
    "AboutMePlatform",
    "SlideSharePlatform",
    "TrelloPlatform",
    "ProductHuntPlatform",
    # Forum / News
    "QuoraPlatform",
    "LobstersPlatform",
    # Other
    "GravatarPlatform",
    "LinktreePlatform",
]
