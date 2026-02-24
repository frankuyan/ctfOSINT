"""Tests for GitHub scanner (non-network methods)."""

import pytest

from sherlockml.extract.github_scanner import GitHubScanner


class TestGitHubScanner:
    """Test GitHub scanner non-network functionality."""

    @pytest.fixture
    def scanner(self):
        return GitHubScanner()

    def test_extract_emails_from_git_config(self, scanner):
        config = """
[core]
    repositoryformatversion = 0
[user]
    name = John Doe
    email = john@example.com
[remote "origin"]
    url = https://github.com/johndoe/repo.git
"""
        emails = scanner.extract_emails_from_git_config(config)
        assert "john@example.com" in emails

    def test_extract_emails_multiple(self, scanner):
        config = """
[user]
    email = dev@company.com
[commit]
    # Also uses personal@email.org for signing
"""
        content_with_extra = config + "\nContact: personal@email.org"
        emails = scanner.extract_emails_from_git_config(content_with_extra)
        assert "dev@company.com" in emails
        assert "personal@email.org" in emails

    def test_extract_emails_empty(self, scanner):
        emails = scanner.extract_emails_from_git_config("no emails here")
        assert emails == []

    def test_find_sensitive_files(self, scanner):
        files = [
            "src/main.py",
            ".env",
            "config.yaml",
            "secrets.json",
            "id_rsa",
            "cert.pem",
            "README.md",
            "api_key.txt",
        ]
        sensitive = scanner.find_sensitive_files(files)
        assert ".env" in sensitive
        assert "config.yaml" in sensitive
        assert "secrets.json" in sensitive
        assert "id_rsa" in sensitive
        assert "cert.pem" in sensitive
        assert "api_key.txt" in sensitive
        assert "README.md" not in sensitive
        assert "src/main.py" not in sensitive

    def test_find_sensitive_files_empty(self, scanner):
        assert scanner.find_sensitive_files([]) == []

    def test_find_sensitive_files_none_match(self, scanner):
        files = ["README.md", "main.py", "setup.cfg"]
        assert scanner.find_sensitive_files(files) == []

    def test_flag_regex(self, scanner):
        matches = scanner.FLAG_REGEX.findall("Found flag{test_123} in commit")
        assert len(matches) >= 1

    def test_flag_regex_various_formats(self, scanner):
        text = "Flags: CTF{abc}, picoCTF{xyz}, HTB{123}"
        matches = scanner.FLAG_REGEX.findall(text)
        assert len(matches) >= 3

    def test_email_regex(self, scanner):
        matches = scanner.EMAIL_REGEX.findall("Contact alice@example.com")
        assert "alice@example.com" in matches

    def test_default_rate_limit(self, scanner):
        assert scanner.rate_limit == 30.0

    def test_custom_auth_token(self):
        scanner = GitHubScanner(auth_token="ghp_test123")
        headers = scanner._get_headers()
        assert headers["Authorization"] == "token ghp_test123"

    def test_headers_without_auth(self, scanner):
        headers = scanner._get_headers()
        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github.v3+json"
