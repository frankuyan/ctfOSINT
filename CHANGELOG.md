# Changelog

All notable changes to SherlockML are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with sections grouped
by intent (Added / Changed / Fixed) under each release.

## Unreleased

### Added

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
  skip list, and pattern-count regressions.
- **15 further tests** for the shared flag module (`extract_flags` full-match
  behaviour, including user-supplied capturing-group patterns) and the
  orchestrator's `_scan_flags` helper. Total suite now: 162 tests.

### Changed

- **`--variants` and `--no-variants` are now mutually exclusive.** Passing
  both raises a `click.UsageError` instead of silently disabling basic
  variants while applying full expansion.
- **`--variants` top-20 selection is now similarity-ranked**, not
  alphabetical. Previously the truncation favoured digit-prefixed leet forms
  (`0john_doe`, `4john_doe`, …) over more plausible variants.
- **Default discovery budget raised from 5 to 15** discovered usernames
  (with the new `--max-hops`/`--max-discovered` knobs in place).

### Fixed

- **Flag detection only captured the flag prefix, not the flag.** The default
  flag regex wrote its alternation as a *capturing* group
  (`(flag|ctf|…)\{…\}`), and every scanner used `re.findall`, which returns
  only captured groups — so `flag{s3cr3t}` was recorded as `flag`. All flag
  extraction now goes through a shared `sherlockml.flags` module
  (`compile_flag_patterns` / `extract_flags`) that returns the full match via
  `finditer` + `group(0)`, so even user-supplied patterns with capturing
  groups yield whole flags. Fixed across the orchestrator, Wayback scanner
  (four sites), and GitHub scanner.
- **PageRank centrality was silently disabled on clean installs.**
  `SocialMediaParser.get_central_nodes` calls `networkx.pagerank`, which
  requires `scipy` — a package that was not declared as a dependency. The
  missing import was swallowed by a bare `except Exception`, so the feature
  always returned `[]`. `scipy` is now a declared dependency, and the handler
  no longer hides unexpected errors (it logs and narrows to
  `PowerIterationFailedConvergence`/`ImportError`).
- **Importing `sherlockml.ml` force-loaded chromadb and spaCy.** The package
  `__init__` eagerly imported `RAGPipeline` (chromadb + sentence-transformers)
  and `NERExtractor` (spaCy), so even using the lightweight `RLController`
  (numpy + sqlite only) required the entire ML stack. Imports are now lazy
  (PEP 562), loading only what each attribute needs.
- **Removed a stray `test_parse.py` scratch script** from the repo root that
  contained an outdated, buggy copy of `_parse_llm_response`.
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
