# Changelog

All notable changes to SherlockML are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with sections grouped
by intent (Added / Changed / Fixed) under each release.

## Unreleased

### Added

- **Evidence capture (`search --evidence-dir DIR`).** Each run writes a new
  timestamped case folder holding every found profile (captured HTML, or the
  observed API data), `manifest.json` (target, variants, discovery chain,
  UTC capture time, SHA-256 per item, whether a proxy was used) and a
  `SHA256SUMS` file that `sha256sum -c` verifies.
- **Discovery provenance.** Results carry `checked_at` (UTC), `hop` and
  `discovered_from` (`platform:username` of the page that linked them), and
  `SearchResults.discoveries` lists every pivot. Live output shows
  `(via github:alice)`; the summary and JSON report list discoveries.
- **Graph export (`search --graph PATH`).** Identity → profile → linked
  identity graph as GraphML, DOT, or rendered SVG/PNG/PDF (falls back to
  DOT if Graphviz is missing). Discovered-but-not-found usernames stay in
  the graph as open leads.
- **`sherlockml exif` image forensics command.** MD5/SHA-1/SHA-256, magic
  vs. extension mismatch, EXIF camera/software/timestamps, GPS as decimal
  degrees with map links, PNG `tEXt`/`zTXt`/`iTXt`, JPEG comments, XMP, XP
  tags, `UserComment`, data appended after EOI/IEND with embedded file
  type and offset, custom PNG chunks, and flags anywhere in the file.
  Pixel data is never decoded; metadata is markup-escaped before printing.
- **`--proxy` on `wayback` and `scan-github`.**
- **Tor identity rotation (`proxy.rotate: true`).** `search`, `wayback` and
  `scan-github` send `SIGNAL NEWNYM` over the Tor control port at the start
  of a run and every `rotate_interval` seconds (minimum 10). Authenticates
  with the new `proxy.control_password`, Tor's cookie file, or no auth;
  keep-alive is disabled while rotating so requests move to the new
  circuits. Failures log one warning and the run continues. These settings
  were previously documented but had no effect.
- **JSON report now includes `contacts` and `verification`.**

- **Multi-hop cross-platform discovery.** `--deep` now follows discovered
  profiles for N hops (default 2) instead of a single hop. Two new CLI flags:
  - `--max-hops` (default 2): depth bound. `1` = one hop from seeds;
    `2` = also follow links of discovered profiles.
  - `--max-discovered` (default 15): total cap on discovered usernames across
    all hops.
- **~28 platform URL patterns for discovery.** Added per-platform extractors
  for Telegram (`t.me` and `telegram.me`), TikTok, Threads, Pinterest, Vimeo,
  SoundCloud, Steam (`/id/` vanity form only — numeric `/profiles/` is
  excluded), Lobsters, Tumblr (both `tumblr.com/<user>` and
  `<user>.tumblr.com`), and additional Mastodon hosts (`mstdn.social`,
  `hachyderm.io`, `tech.lgbt`, `techhub.social`). Each pattern uses a
  left-boundary look-behind so look-alike domains (`notgithub.com`,
  `box.com`, `linux.com`) cannot false-positive.
- **Email + `@handle` extraction.** When a profile is found, SherlockML now
  scans its HTML for:
  - Non-role email addresses (`alice@protonmail.com`, skipping
    `noreply@`/`support@`/etc.) — surfaced in `results.contacts` and the
    CLI summary's new **Contacts** section.
  - Bare `@handle` mentions in bios — folded into the discovery seed set
    under the same hop/cap budget. The look-behind rejects URL-attached
    handles (`x.com/@user`), email locals (`alice@gmail.com`), and the
    second `@host` portion of Mastodon-style `@user@instance`.
- **Aggressive default variant generation.** `generate_basic` now produces
  reversed parts (`john_doe` → `doe_john`, `doejohn`), reverse-initial forms
  (`john_doe` → `johnd`), and light digit suffixes (`alice` → `alice1`,
  `alice2024`) in addition to the previous separator/initial forms.
  Candidates are validity-filtered, ranked by Jaro-Winkler similarity to the
  input, and capped at `max_variants` (default 15).
- **34 new tests** covering `generate_basic`, the per-platform extractors,
  email/handle/contact extraction, the shared text-collection helper, the
  skip list, and pattern-count regressions. Total suite now: 147 tests.

### Changed

- **Pillow is now a dependency** (used by `exif`).
- **`sherlockml.ml` imports lazily**, so `RLController` no longer needs
  chromadb/spaCy installed just to import.
- **Discovered usernames are processed in sorted order**, making the
  `--max-discovered` cut reproducible between runs.
- **`--verify` reuses pages captured during the search** instead of
  fetching every HTML profile a second time; only API-backed platforms are
  fetched.
- **`scan-github` also scans repo and gist descriptions for flags.**
- **`scan-github` uses `ctf.flag_patterns`** like `search` and `wayback`
  instead of its built-in regex only.
- **`--variants` and `--no-variants` are now mutually exclusive.** Passing
  both raises a `click.UsageError` instead of silently disabling basic
  variants while applying full expansion.
- **`--variants` top-20 selection is now similarity-ranked**, not
  alphabetical. Previously the truncation favoured digit-prefixed leet forms
  (`0john_doe`, `4john_doe`, …) over more plausible variants.
- **Default discovery budget raised from 5 to 15** discovered usernames
  (with the new `--max-hops`/`--max-discovered` knobs in place).

### Fixed

- **Hostile text could crash or spoof terminal output.** Profile bios, LLM
  summaries, archived page diffs, robots.txt entries and commit author emails
  were interpolated into Rich markup, so a value like `[/i]` raised
  `MarkupError` after the scan finished and `[red]...` could restyle output.
  All such values are now escaped.
- **Malformed LLM verdicts crashed `--verify`.** A prompt-injected page could
  make the model return `null`/objects/lists for text fields; they are now
  coerced to text, verdicts are normalised and confidence clamped to [0, 1].
- **Flags were reported as `"flag"` instead of `"flag{...}"`.** The default
  pattern `(flag|ctf|...)\{...\}` has a capture group and `re.findall`
  returns the group. `search`, `scan-github` and `wayback` now share
  `sherlockml.flags.find_flags`, which returns the full match and
  deduplicates.
- **Proxy was bypassed outside the main search.** `--verify` page fetches,
  `wayback` and `scan-github` used bare `aiohttp` sessions, so running
  behind Tor still exposed the investigator's IP to targets. All
  target-facing requests now go through `sherlockml.net.create_session`.
  `tor` and `socks5h` proxy types no longer crash.
- **`--verify` results were dropped from the saved JSON**, and harvested
  contacts never reached the JSON or Markdown report.
- **`generated_at` was malformed** (`...+00:00Z`).
- **`JSONReporter(include_raw=...)` was ignored**; internal `_`-prefixed
  metadata is now dropped unless requested.
- **Graphviz export produced invalid DOT** for names containing a quote
  (quotes were escaped before backslashes; labels weren't escaped).
- **Markdown writeup** hard-coded `v1.0.0` and used deprecated
  `datetime.utcnow()`.
- **`--deep` was silently broken.** The orchestrator used
  `asyncio.as_completed(tasks)`, which captures its input as a set at call
  time — tasks appended to `tasks` mid-iteration during discovery were
  never awaited via the loop and their results never entered
  `results.results`. Replaced with a `pending: set` +
  `asyncio.wait(..., FIRST_COMPLETED)` loop that handles dynamic task
  insertion correctly. Also enforces the `max_time` deadline via
  `asyncio.wait`'s `timeout=` argument, so a single hung task cannot
  outlast `--max-time`.
- **Discovery URL regex was double-broken.** The shared `\.com` suffix was
  pinned to the entire alternation group, so `dev.to`, `mastodon.*`,
  `bsky.app`, `twitch.tv`, and `news.ycombinator.com` could never match.
  Simultaneously, the `|x|` alternative with no left boundary matched any
  URL ending in `…x.com/<path>` (e.g. `box.com/foo`, `linux.com/articles`)
  and produced false-positive discovered usernames. Replaced with a list of
  per-platform patterns with proper TLDs and `(?<![\w.-])` left-boundary
  look-behinds.
- **Dead code in the URL extractor.** `m.group(1).rstrip("/")` could never
  affect the result because the capture group's character class excludes
  `/`. Removed.

## Notes

This changelog began with the v1.x active-search improvement series. Earlier
history is in `git log`.
