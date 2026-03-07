"""SherlockML Command-Line Interface."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sherlockml import __version__
from sherlockml.config import Config, load_config, create_default_config_file


console = Console()


def async_command(f):
    """Decorator to run async click commands."""
    import functools
    
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    
    return wrapper


@click.group()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    default=None,
    help='Path to config file (default: ~/.sherlockml/config.yaml)',
)
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.version_option(version=__version__, prog_name='sherlockml')
@click.pass_context
def main(ctx: click.Context, config: Path | None, verbose: bool) -> None:
    """SherlockML - OSINT Framework for CTF Competitions
    
    Combine Sherlock-style enumeration with ML, RAG, and RL
    for intelligent reconnaissance.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    try:
        ctx.obj['config'] = load_config(config)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        ctx.obj['config'] = Config()


@main.command()
@click.argument('username')
@click.option('--max-time', '-t', type=int, default=90, help='Maximum search time in seconds')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file path')
@click.option('--format', '-f', 'output_format', type=click.Choice(['json', 'md', 'both']), default='json')
@click.option('--fast-fail', is_flag=True, help='Stop after first flag found')
@click.option('--rate-limit', '-r', type=float, default=None, help='Global requests/sec')
@click.option('--proxy', type=str, help='Proxy URL (socks5://host:port)')
@click.option('--wordlist', '-w', type=click.Path(exists=True, path_type=Path), help='Username variants wordlist')
@click.option('--variants', is_flag=True, help='Auto-generate username variants')
@click.option('--verify', is_flag=True, help='Use LLM to verify found profiles are real')
@click.option('--llm-key', type=str, envvar='SHERLOCKML_LLM_KEY', help='LLM API key (overrides config)')
@click.pass_context
@async_command
async def search(
    ctx: click.Context,
    username: str,
    max_time: int,
    output: Path | None,
    output_format: str,
    fast_fail: bool,
    rate_limit: float | None,
    proxy: str | None,
    wordlist: Path | None,
    variants: bool,
    verify: bool,
    llm_key: str | None,
) -> None:
    """Search for USERNAME across platforms.
    
    Examples:
    
        sherlockml search john_doe
        
        sherlockml search john_doe --max-time 120 -o results.json
        
        sherlockml search john_doe --fast-fail --variants
    """
    config: Config = ctx.obj['config']
    
    # Override config with CLI options
    if rate_limit is not None:
        config.search.default_rate_limit = rate_limit
    if proxy:
        config.proxy.enabled = True
        from urllib.parse import urlparse
        parsed = urlparse(proxy)
        if parsed.scheme:
            config.proxy.type = parsed.scheme
        if parsed.hostname:
            config.proxy.host = parsed.hostname
        if parsed.port:
            config.proxy.port = parsed.port
        if parsed.username:
            config.proxy.username = parsed.username
        if parsed.password:
            config.proxy.password = parsed.password
    if fast_fail:
        config.ctf.fast_fail = True
    
    # Generate usernames to search
    usernames = [username]
    
    if wordlist:
        usernames.extend(wordlist.read_text().strip().split('\n'))
    
    if variants:
        from sherlockml.enum.variants import UsernameVariants
        generator = UsernameVariants()
        generated = generator.generate(username, leet=True, include_common=True)
        usernames.extend(generated[:20])  # Limit variants
    
    usernames = list(dict.fromkeys(usernames))  # Dedupe preserving order
    
    console.print(f"[bold blue]SherlockML[/bold blue] v{__version__}")
    console.print(f"Searching for [green]{username}[/green] ({len(usernames)} variants)")
    console.print()
    
    # Load platforms
    from sherlockml.enum.registry import get_registry
    from sherlockml.enum.orchestrator import Orchestrator
    
    registry = get_registry()
    platforms = registry.get_enabled(config)
    
    if not platforms:
        console.print("[yellow]No platforms enabled. Check your config.[/yellow]")
        return
    
    console.print(f"Platforms: {len(platforms)} enabled")
    
    # Run search
    orchestrator = Orchestrator(config)
    
    found_count = 0
    
    def progress_callback(result):
        nonlocal found_count
        if result.exists:
            found_count += 1
            console.print(f"  [green]✓[/green] {result.platform}: {result.url}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching...", total=None)
        
        results = await orchestrator.search(
            usernames=usernames,
            platforms=platforms,
            callback=progress_callback,
            fast_fail=fast_fail,
            max_time=max_time,
        )
        
        progress.update(task, completed=True)
    
    # LLM Verification of found profiles
    verification_results = []
    if verify or config.llm.enabled:
        from sherlockml.enum.verify import verify_results as run_verification

        # Override API key from CLI if provided
        if llm_key:
            config.llm.api_key = llm_key
            config.llm.enabled = True

        if not config.llm.api_key:
            console.print(
                "[yellow]LLM verification requested but no API key configured.[/yellow]"
            )
            console.print(
                "[dim]Set llm.api_key in config, SHERLOCKML_LLM_KEY env var, or --llm-key flag.[/dim]"
            )
        else:
            # Collect found results that have raw HTML
            to_verify = []
            for r in results.found_results:
                raw = r.metadata.get("_raw_response", "")
                if raw and r.url:
                    to_verify.append({
                        "platform": r.platform,
                        "url": r.url,
                        "username": r.username,
                        "raw_html": raw,
                    })

            if to_verify:
                console.print()
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    vtask = progress.add_task(
                        f"Verifying {len(to_verify)} profiles with LLM...",
                        total=None,
                    )
                    verification_results = await run_verification(to_verify, config.llm)
                    progress.update(vtask, completed=True)

                # Build lookup for display
                verdict_map = {v.url: v for v in verification_results}

                # Update result metadata with verification
                for r in results.found_results:
                    v = verdict_map.get(r.url)
                    if v:
                        r.metadata["llm_verdict"] = v.verdict
                        r.metadata["llm_confidence"] = v.confidence
                        r.metadata["llm_reason"] = v.reason
                        if v.error:
                            r.metadata["llm_error"] = v.error

    # Display results
    console.print()
    console.print(f"[bold]Results:[/bold]")
    console.print(f"  Platforms checked: {results.total_platforms}")
    console.print(f"  Profiles found: {results.found_count}")
    console.print(f"  Flags found: {len(results.flags_found)}")
    console.print(f"  Time: {results.elapsed_time:.1f}s")

    # Show verification summary if we ran it
    if verification_results:
        real_count = sum(1 for v in verification_results if v.verdict == "real")
        empty_count = sum(1 for v in verification_results if v.verdict == "empty")
        suspicious_count = sum(1 for v in verification_results if v.verdict == "suspicious")
        console.print()
        console.print(f"[bold]LLM Verification:[/bold]")
        console.print(f"  [green]Real accounts:[/green] {real_count}")
        console.print(f"  [red]Empty/default pages:[/red] {empty_count}")
        console.print(f"  [yellow]Suspicious:[/yellow] {suspicious_count}")
        console.print()

        # Detailed verification table
        vtable = Table(show_header=True, title="Profile Verification")
        vtable.add_column("Platform", style="cyan")
        vtable.add_column("Verdict", justify="center")
        vtable.add_column("Conf.", justify="right")
        vtable.add_column("Reason")

        for v in sorted(verification_results, key=lambda x: x.verdict):
            if v.verdict == "real":
                verdict_str = "[green]REAL[/green]"
            elif v.verdict == "empty":
                verdict_str = "[red]EMPTY[/red]"
            else:
                verdict_str = "[yellow]SUSPICIOUS[/yellow]"

            reason = v.reason[:60] + "..." if len(v.reason) > 60 else v.reason
            if v.error:
                reason = f"[red]Error: {v.error[:50]}[/red]"

            vtable.add_row(v.platform, verdict_str, f"{v.confidence:.0%}", reason)

        console.print(vtable)

    if results.flags_found:
        console.print()
        console.print("[bold red]🚩 FLAGS FOUND:[/bold red]")
        for flag in results.flags_found:
            console.print(f"  {flag}")
    
    # Attach verification data to results dict for output
    if verification_results:
        results_dict = results.to_dict()
        results_dict["verification"] = [v.to_dict() for v in verification_results]

    # Save output
    if output is not None or output_format in ('md', 'both'):
        from sherlockml.output.json_reporter import JSONReporter
        from sherlockml.output.markdown_writer import MarkdownWriter

        output = output or Path(f"sherlockml_{username}")
        
        if output_format in ('json', 'both'):
            reporter = JSONReporter()
            report = reporter.generate_report(results)
            json_path = output.with_suffix('.json')
            reporter.save(report, json_path)
            console.print(f"\n[dim]Saved JSON: {json_path}[/dim]")
        
        if output_format in ('md', 'both'):
            writer = MarkdownWriter()
            markdown = writer.generate_writeup(results)
            md_path = output.with_suffix('.md')
            writer.save(markdown, md_path)
            console.print(f"[dim]Saved Markdown: {md_path}[/dim]")


@main.command('generate-variants')
@click.argument('base_username')
@click.option('--leet', is_flag=True, help='Include leetspeak variants')
@click.option('--years', type=str, help='Year range (e.g., 2015-2025)')
@click.option('--common', is_flag=True, help='Include common prefixes/suffixes')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file')
@click.option('--max', '-n', type=int, default=100, help='Maximum variants')
def generate_variants(
    base_username: str,
    leet: bool,
    years: str | None,
    common: bool,
    output: Path | None,
    max: int,
) -> None:
    """Generate username variants for a BASE_USERNAME.
    
    Examples:
    
        sherlockml generate-variants john_doe --leet
        
        sherlockml generate-variants john_doe --years 2015-2025 -o variants.txt
    """
    from sherlockml.enum.variants import UsernameVariants, parse_years
    
    generator = UsernameVariants()
    
    year_range = None
    if years:
        year_range = parse_years(years)
    
    variants = generator.generate(
        base_username,
        leet=leet,
        years=year_range,
        include_common=common,
        max_variants=max,
    )
    
    console.print(f"Generated [green]{len(variants)}[/green] variants for '{base_username}'")
    console.print()
    
    if output:
        output.write_text('\n'.join(variants))
        console.print(f"[dim]Saved to: {output}[/dim]")
    else:
        for variant in variants[:50]:
            console.print(f"  {variant}")
        
        if len(variants) > 50:
            console.print(f"  [dim]... and {len(variants) - 50} more[/dim]")


@main.command('rl-train')
@click.option('--dataset', '-d', type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--epochs', '-e', type=int, default=50, help='Training epochs')
@click.pass_context
def rl_train(ctx: click.Context, dataset: Path, epochs: int) -> None:
    """Train RL model on historical CTF data.
    
    The dataset should be a JSON file with past challenge results.
    
    Example:
    
        sherlockml rl-train --dataset past-challenges.json --epochs 100
    """
    from sherlockml.ml.rl_controller import RLController
    
    config: Config = ctx.obj['config']
    
    console.print(f"Training RL model on {dataset}")
    console.print(f"Epochs: {epochs}")
    
    with RLController(config.ml.rl_weights_path) as rl:
        stats = rl.train(dataset, epochs=epochs)
        
        console.print()
        console.print(f"[green]Training complete![/green]")
        console.print(f"  Entries: {stats['entries']}")
        console.print(f"  Updates: {stats['total_updates']}")
        
        # Show top platforms
        weights = rl.export_weights()
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        
        console.print()
        console.print("[bold]Top Platforms:[/bold]")
        
        table = Table(show_header=True)
        table.add_column("Platform")
        table.add_column("Score", justify="right")
        
        for platform, score in sorted_weights[:10]:
            table.add_row(platform, f"{score:.3f}")
        
        console.print(table)


@main.command('rag-query')
@click.argument('query')
@click.option('--top-k', '-k', type=int, default=5, help='Number of results')
@click.option('--threshold', '-t', type=float, default=0.0, help='Minimum similarity')
@click.pass_context
def rag_query(ctx: click.Context, query: str, top_k: int, threshold: float) -> None:
    """Query the RAG vectorstore.
    
    Search indexed OSINT data for relevant information.
    
    Example:
    
        sherlockml rag-query "Find emails related to target" --top-k 10
    """
    from sherlockml.ml.rag_pipeline import RAGPipeline
    
    config: Config = ctx.obj['config']
    
    rag = RAGPipeline(config.ml.vectorstore_dir)
    
    if rag.count == 0:
        console.print("[yellow]Vectorstore is empty. Run searches to populate.[/yellow]")
        return
    
    console.print(f"Querying: [green]{query}[/green]")
    console.print()
    
    results = rag.query(query, top_k=top_k, threshold=threshold)
    
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    for i, result in enumerate(results, 1):
        console.print(f"[bold]{i}. Score: {result.score:.3f}[/bold]")
        console.print(f"   {result.content[:200]}...")
        if result.metadata:
            console.print(f"   [dim]{result.metadata}[/dim]")
        console.print()


@main.command('scan-github')
@click.argument('username')
@click.option('--commits', is_flag=True, help='Search commit history')
@click.option('--gists/--no-gists', default=True, help='Include gists')
@click.option('--depth', '-d', type=int, default=10, help='Search depth (pages)')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file')
@click.pass_context
@async_command
async def scan_github(
    ctx: click.Context,
    username: str,
    commits: bool,
    gists: bool,
    depth: int,
    output: Path | None,
) -> None:
    """Deep GitHub enumeration for USERNAME.
    
    Searches commits, gists, and repos for sensitive data.
    
    Example:
    
        sherlockml scan-github targetuser --commits --depth 20
    """
    import aiohttp
    from sherlockml.extract.github_scanner import GitHubScanner
    
    config: Config = ctx.obj['config']
    github_config = config.get_platform('github')
    
    scanner = GitHubScanner(auth_token=github_config.auth_token)
    
    console.print(f"Scanning GitHub user: [green]{username}[/green]")
    
    async with aiohttp.ClientSession() as session:
        result = await scanner.scan_user(
            username, session,
            commits=commits,
            gists=gists,
            depth=depth,
        )
    
    console.print()
    console.print(f"[bold]Results:[/bold]")
    console.print(f"  Repositories: {len(result.repos)}")
    console.print(f"  Commits: {len(result.commits)}")
    console.print(f"  Gists: {len(result.gists)}")
    console.print(f"  Emails found: {len(result.emails_found)}")
    console.print(f"  Flags found: {len(result.flags_found)}")
    
    if result.emails_found:
        console.print()
        console.print("[bold]Emails:[/bold]")
        for email in result.emails_found[:10]:
            console.print(f"  📧 {email}")
    
    if result.flags_found:
        console.print()
        console.print("[bold red]🚩 FLAGS:[/bold red]")
        for flag in result.flags_found:
            console.print(f"  {flag}")
    
    if output:
        import json
        output.write_text(json.dumps(result.to_dict(), indent=2))
        console.print(f"\n[dim]Saved to: {output}[/dim]")


@main.command('wayback')
@click.argument('target')
@click.option('--mode', '-m', type=click.Choice(['url', 'profile', 'domain']), default='url',
              help='Scan mode: url (single URL), profile (username across platforms), domain (wildcard)')
@click.option('--from-date', type=str, help='Start date (YYYY or YYYYMMDD)')
@click.option('--to-date', type=str, help='End date (YYYY or YYYYMMDD)')
@click.option('--scan-content', '-s', is_flag=True, help='Fetch and scan snapshot content for flags')
@click.option('--diff', '-d', is_flag=True, help='Show differences between snapshots')
@click.option('--platforms', '-p', type=str, help='Comma-separated platform names (profile mode)')
@click.option('--max-snapshots', type=int, default=5, help='Max snapshots to fetch content from')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output file (JSON)')
@click.option('--rate-limit', '-r', type=float, default=10.0, help='Requests per minute to Wayback API')
@click.pass_context
@async_command
async def wayback(
    ctx: click.Context,
    target: str,
    mode: str,
    from_date: str | None,
    to_date: str | None,
    scan_content: bool,
    diff: bool,
    platforms: str | None,
    max_snapshots: int,
    output: Path | None,
    rate_limit: float,
) -> None:
    """Query the Wayback Machine for historical OSINT data.

    TARGET is a URL, username, or domain depending on --mode.

    Examples:

        sherlockml wayback https://example.com/user --scan-content

        sherlockml wayback john_doe --mode profile --scan-content

        sherlockml wayback example.com --mode domain --scan-content

        sherlockml wayback https://ctf-site.com/challenge --from-date 2023 --diff
    """
    import aiohttp
    import json
    from sherlockml.extract.wayback import WaybackIntegration

    config = ctx.obj['config']
    wb = WaybackIntegration(rate_limit=rate_limit)

    # Get flag patterns from config
    flag_patterns = config.ctf.flag_patterns if config.ctf.auto_detect_format else None

    platform_list = platforms.split(',') if platforms else None

    console.print(f"[bold blue]SherlockML Wayback[/bold blue] - Mode: [green]{mode}[/green]")
    console.print(f"Target: [cyan]{target}[/cyan]")
    if from_date or to_date:
        console.print(f"Date range: {from_date or '...'} to {to_date or '...'}")
    console.print()

    async with aiohttp.ClientSession() as session:
        if mode == 'url':
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Querying Wayback Machine...", total=None)
                result = await wb.analyze_url(
                    target, session,
                    from_date=from_date, to_date=to_date,
                    flag_patterns=flag_patterns,
                    scan_content=scan_content,
                    diff_snapshots=diff,
                    max_content_snapshots=max_snapshots,
                )
                progress.update(task, completed=True)

            _display_wayback_result(result, diff)

            if output:
                output.write_text(json.dumps(result.to_dict(), indent=2))
                console.print(f"\n[dim]Saved to: {output}[/dim]")

        elif mode == 'profile':
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Scanning archived profiles for '{target}'...", total=None
                )
                results = await wb.scan_profile_history(
                    target, session,
                    platforms=platform_list,
                    from_date=from_date, to_date=to_date,
                    flag_patterns=flag_patterns,
                )
                progress.update(task, completed=True)

            if not results:
                console.print("[yellow]No archived profiles found.[/yellow]")
                return

            all_flags: list[str] = []
            for r in results:
                _display_wayback_result(r, show_diffs=False)
                all_flags.extend(r.flags_found)

            console.print()
            console.print(f"[bold]Total:[/bold] {len(results)} platforms with archived data")

            if all_flags:
                console.print()
                console.print("[bold red]FLAGS FOUND:[/bold red]")
                for flag in all_flags:
                    console.print(f"  {flag}")

            if output:
                data = [r.to_dict() for r in results]
                output.write_text(json.dumps(data, indent=2))
                console.print(f"\n[dim]Saved to: {output}[/dim]")

        elif mode == 'domain':
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Wildcard scanning {target}...", total=None
                )
                result = await wb.scan_url_wildcard(
                    target, session,
                    from_date=from_date, to_date=to_date,
                    flag_patterns=flag_patterns,
                )
                progress.update(task, completed=True)

            # Show unique URLs discovered
            seen: set[str] = set()
            unique_urls = []
            for s in result.snapshots:
                if s.original_url not in seen:
                    seen.add(s.original_url)
                    unique_urls.append(s.original_url)

            console.print(f"[bold]Discovered URLs:[/bold] {len(unique_urls)}")
            for url in unique_urls[:30]:
                console.print(f"  {url}")
            if len(unique_urls) > 30:
                console.print(f"  [dim]... and {len(unique_urls) - 30} more[/dim]")

            if result.hidden_endpoints:
                console.print()
                console.print(f"[bold yellow]Interesting endpoints:[/bold yellow] {len(result.hidden_endpoints)}")
                for ep in result.hidden_endpoints:
                    console.print(f"  [yellow]{ep}[/yellow]")

            if result.flags_found:
                console.print()
                console.print("[bold red]FLAGS FOUND:[/bold red]")
                for flag in result.flags_found:
                    console.print(f"  {flag}")

            if output:
                output.write_text(json.dumps(result.to_dict(), indent=2))
                console.print(f"\n[dim]Saved to: {output}[/dim]")


def _display_wayback_result(result: "WaybackResult", show_diffs: bool = False) -> None:
    """Display a single WaybackResult to the console."""
    from sherlockml.extract.wayback import WaybackResult as _WR  # noqa: F811

    date_range = result.date_range

    console.print(f"[bold cyan]{result.original_url}[/bold cyan]")
    console.print(f"  Snapshots: {result.snapshot_count}")
    if date_range:
        console.print(f"  Date range: {date_range[0]} - {date_range[1]}")

    if result.hidden_endpoints:
        console.print(f"  [yellow]Hidden endpoints: {len(result.hidden_endpoints)}[/yellow]")
        for ep in result.hidden_endpoints[:10]:
            console.print(f"    {ep}")

    if result.robots_entries:
        console.print(f"  Robots.txt entries: {len(result.robots_entries)}")

    if result.sitemap_urls:
        console.print(f"  Sitemap URLs: {len(result.sitemap_urls)}")

    if result.historical_content:
        console.print(f"  [dim]Content snapshots fetched: {len(result.historical_content)}[/dim]")

    if show_diffs and result.diffs:
        console.print()
        console.print(f"  [bold]Changes detected: {len(result.diffs)}[/bold]")
        for d in result.diffs[:5]:
            console.print(f"    {d.old_timestamp} -> {d.new_timestamp}")
            for line in d.added_lines[:5]:
                console.print(f"      [green]+ {line[:120]}[/green]")
            for line in d.removed_lines[:5]:
                console.print(f"      [red]- {line[:120]}[/red]")
            if len(d.added_lines) > 5 or len(d.removed_lines) > 5:
                console.print(f"      [dim]... and more changes[/dim]")

    if result.flags_found:
        console.print()
        console.print("  [bold red]FLAGS:[/bold red]")
        for flag in result.flags_found:
            console.print(f"    {flag}")

    console.print()


@main.command('init')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing config')
def init(force: bool) -> None:
    """Initialize SherlockML configuration.
    
    Creates ~/.sherlockml/config.yaml with default settings.
    """
    config_path = Path.home() / '.sherlockml' / 'config.yaml'
    
    if config_path.exists() and not force:
        console.print(f"[yellow]Config already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        return
    
    create_default_config_file(config_path)
    
    console.print(f"[green]Created config:[/green] {config_path}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Edit the config to add API tokens")
    console.print("  2. Run: sherlockml search <username>")


if __name__ == '__main__':
    main()
