"""Tests for the Wayback integration's pure helpers (no network)."""

from sherlockml.extract.wayback import WaybackIntegration, WaybackSnapshot


class TestDateWindow:
    """_date_window must use real calendar arithmetic."""

    def test_simple_offset(self):
        assert WaybackIntegration._date_window("20240101", days=30) == (
            "20240101",
            "20240131",
        )

    def test_crosses_month_boundary(self):
        # 20 Jan + 30 days = 19 Feb, NOT the invalid "20240150".
        start, end = WaybackIntegration._date_window("20240120", days=30)
        assert (start, end) == ("20240120", "20240219")

    def test_crosses_year_boundary(self):
        # 20 Dec 2024 + 30 days = 19 Jan 2025.
        assert WaybackIntegration._date_window("20241220", days=30) == (
            "20241220",
            "20250119",
        )

    def test_truncates_long_timestamp(self):
        # A full 14-digit CDX timestamp is truncated to the date part.
        start, end = WaybackIntegration._date_window("20240115123000", days=30)
        assert start == "20240115"
        assert end == "20240214"

    def test_malformed_date_drops_upper_bound(self):
        assert WaybackIntegration._date_window("garbage", days=30) == (
            "garbage",
            None,
        )


class TestDiffContent:
    def test_detects_added_and_removed_lines(self):
        old = "<p>alpha</p>\n<p>beta</p>"
        new = "<p>beta</p>\n<p>gamma</p>"
        diff = WaybackIntegration._diff_content("20240101", "20240201", old, new)
        assert "gamma" in diff.added_lines
        assert "alpha" in diff.removed_lines
        assert "beta" not in diff.added_lines
        assert "beta" not in diff.removed_lines


class TestHiddenEndpoints:
    def test_flags_interesting_paths(self):
        wb = WaybackIntegration()
        entries = ["/public", "/admin", "/images", "/.git", "/api/v1"]
        hidden = wb._find_hidden_endpoints(entries)
        assert "/admin" in hidden
        assert "/.git" in hidden
        assert "/api/v1" in hidden
        assert "/public" not in hidden
        assert "/images" not in hidden


class TestBuildProfileUrls:
    def test_all_platforms_by_default(self):
        urls = dict(WaybackIntegration._build_profile_urls("alice"))
        assert urls["github"] == "https://github.com/alice"
        assert urls["mastodon"] == "https://mastodon.social/@alice"
        assert len(urls) > 20

    def test_filter_by_platforms(self):
        urls = WaybackIntegration._build_profile_urls("alice", ["github", "reddit"])
        names = {name for name, _ in urls}
        assert names == {"github", "reddit"}


class TestStripToolbar:
    def test_removes_wayback_toolbar(self):
        html = (
            "<body>keep"
            "<!-- BEGIN WAYBACK TOOLBAR --><div>junk</div><!-- END WAYBACK TOOLBAR -->"
            "end</body>"
        )
        stripped = WaybackIntegration._strip_wayback_toolbar(html)
        assert "junk" not in stripped
        assert "keep" in stripped and "end" in stripped


class TestSnapshot:
    def test_wayback_url_and_datetime(self):
        snap = WaybackSnapshot(
            url="https://web.archive.org/web/20240115120000/https://example.com",
            timestamp="20240115120000",
            original_url="https://example.com",
            status_code=200,
            mime_type="text/html",
        )
        assert snap.wayback_url.endswith("/20240115120000/https://example.com")
        assert snap.datetime.year == 2024
        assert snap.datetime.month == 1
