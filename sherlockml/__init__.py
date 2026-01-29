"""SherlockML - Production-ready OSINT framework for CTF competitions."""

__version__ = "1.0.0"
__author__ = "SherlockML Team"

from sherlockml.config import Config, load_config

__all__ = ["Config", "load_config", "__version__"]
