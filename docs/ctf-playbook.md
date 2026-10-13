# CTF Playbook

Strategies and techniques for using SherlockML in CTF competitions.

## Quick Reference

| Situation | Command |
|-----------|---------|
| Basic recon | `sherlockml search $TARGET` |
| Fast flag hunt | `sherlockml search $TARGET --fast-fail` |
| Deep GitHub | `sherlockml scan-github $TARGET --commits -d 50` |
| Wayback URL scan | `sherlockml wayback $URL --scan-content --diff` |
| Wayback profile scan | `sherlockml wayback $TARGET --mode profile -s` |
| Wayback domain scan | `sherlockml wayback $DOMAIN --mode domain -s` |
| Generate wordlist | `sherlockml generate-variants $TARGET --leet --years 2020-2025` |
| Image forensics | `sherlockml exif $FILE_OR_DIR -r` |
| Evidence + pivot graph | `sherlockml search $TARGET --deep --evidence-dir cases/ --graph graph.graphml` |

---

## OSINT Challenge Workflow

### Step 1: Initial Reconnaissance

Start with a broad search:

```bash
sherlockml search johndoe --max-time 120 --output recon.json
```

Review results:
```json
{
  "profiles_found": 5,
  "platforms": ["github", "twitter", "reddit", "hackernews", "keybase"]
}
```

### Step 2: Username Variants

Generate variations if initial search yields little:

```bash
# Leetspeak + years
sherlockml generate-variants johndoe --leet --years 2018-2024

# Common patterns
sherlockml generate-variants johndoe --common -o variants.txt

# Search all variants
sherlockml search johndoe -w variants.txt --fast-fail
```

### Step 3: Deep Platform Analysis

Focus on high-value platforms:

```bash
# GitHub: commits, gists, email leaks
sherlockml scan-github johndoe --commits --gists -d 30

# Look for flags in commit messages
grep -i "flag\|ctf" github_results.json
```

### Step 4: Historical Analysis

Check Wayback Machine for deleted content using the CLI:

```bash
# Scan a specific URL for archived content and flags
sherlockml wayback https://github.com/johndoe --scan-content --diff --from-date 2020

# Scan all archived profiles for the username
sherlockml wayback johndoe --mode profile --scan-content -o wayback.json

# Wildcard scan for hidden files on a challenge domain
sherlockml wayback challenge-site.com --mode domain --scan-content
```

Or use the Python API directly:

```python
from sherlockml.extract.wayback import WaybackIntegration
import aiohttp
import asyncio

async def check_history():
    wayback = WaybackIntegration()
    async with aiohttp.ClientSession() as session:
        result = await wayback.analyze_url(
            "https://github.com/johndoe",
            session,
            from_date="2020",
            scan_content=True,
            diff_snapshots=True,
        )
        print(f"Snapshots: {result.snapshot_count}")
        for endpoint in result.hidden_endpoints:
            print(f"Hidden: {endpoint}")
        for flag in result.flags_found:
            print(f"Flag: {flag}")

asyncio.run(check_history())
```

### Step 5: Cross-Platform Correlation

`--deep` records which profile led to each discovered username. Export it
as a graph to see the pivot chain at a glance:

```bash
sherlockml search johndoe --deep --graph pivots.svg      # or .graphml for Gephi/yEd
```

For hand-built graphs from your own profile data:

```python
from sherlockml.extract.social_parser import SocialMediaParser

parser = SocialMediaParser()
# ... analyze profiles
graph = parser.build_social_graph(profiles)
central = parser.get_central_nodes(n=3)
print(f"Most connected: {central}")
```

---

## Flag Detection

### Automatic Detection

SherlockML auto-detects common flag formats:

```
flag{...}
CTF{...}
picoCTF{...}
HTB{...}
hxp{...}
FLAG{...}
```

### Fast-Fail Mode

Stop immediately when a flag is found:

```bash
sherlockml search target --fast-fail
```

### Custom Flag Patterns

Add CTF-specific patterns:

```yaml
# config.yaml
ctf:
  flag_patterns:
    - 'MYCTF{[^}]+}'
    - 'secret_[a-f0-9]{32}'
```

---

## Platform Priorities

### Default CTF Priority

```
 1. Pastebin     - Flag leaks, code pastes
 2. GitHub       - Commit history, email leaks
 3. GitHub Gist  - Code snippets, hidden flags
 4. Keybase      - Cross-platform links, PGP keys
 5. HackerNews   - Tech profiles
 6. TryHackMe    - CTF platform profiles
 7. Hack The Box - CTF platform profiles
 8. HackerOne    - Bug bounty profiles
 9. GitLab       - Repos, project search
10. Bitbucket    - Repos, team info
11. Codeberg     - Alternative git hosting
```

### Competition-Specific Tuning

Train the RL model on past challenges:

```bash
# Create training data
cat > ctf_data.json << EOF
[
  {"challenge": "osint1", "platforms": {"pastebin": true, "github": true}},
  {"challenge": "osint2", "platforms": {"twitter": false, "reddit": true}}
]
EOF

# Train
sherlockml rl-train --dataset ctf_data.json --epochs 50
```

---

## Common Challenge Types

### Type 1: Find the Username

Given: Email, handle fragment, avatar
Goal: Find all social profiles

**Approach:**
```bash
# Generate variants from known info
sherlockml generate-variants partial_name --leet --common

# Broad search
sherlockml search partial_name --variants
```

### Type 2: Find Hidden Information

Given: Known profile
Goal: Find sensitive data (emails, old posts)

**Approach:**
```bash
# Deep GitHub scan
sherlockml scan-github knownuser --commits -d 50

# Wayback Machine - scan profile and domain
sherlockml wayback knownuser --mode profile --scan-content
sherlockml wayback target-site.com --mode domain --scan-content
```

### Type 3: Find the Flag

Given: Target identity information
Goal: Locate CTF flag

**Approach:**
```bash
# Fast mode with flag detection
sherlockml search target --fast-fail --max-time 60

# Check results
jq '.flags' results.json
```

### Type 4: Build a Profile

Given: Minimal starting info
Goal: Comprehensive dossier

**Approach:**
```bash
# Full search
sherlockml search target -o profile.json --format both

# Generate writeup
cat profile.md  # Auto-generated markdown
```

---

## Time-Sensitive Strategies

### Speed Run (< 5 minutes)

```bash
# Fast search, priority platforms only
sherlockml search target \
  --max-time 60 \
  --fast-fail \
  --rate-limit 20
```

### Thorough Analysis (30+ minutes)

```bash
# Full search with variants
sherlockml generate-variants target --leet --years 2018-2025 -o vars.txt
sherlockml search target -w vars.txt --max-time 900 --format both

# Deep dives
sherlockml scan-github target --commits -d 50
```

---

## Team Workflow

### Shared Vectorstore

Set up central ChromaDB:

```yaml
# docker-compose.yaml
services:
  chromadb:
    ports:
      - "8000:8000"
```

Configure team members:
```yaml
ml:
  chromadb_host: team-server
  chromadb_port: 8000
```

### Flag Sharing

Export found flags:

```bash
sherlockml search target -o results.json
jq '.flags' results.json > team_flags.json
```

### Result Aggregation

Query across all team findings:

```bash
sherlockml rag-query "all email addresses found" --top-k 50
```

---

## Image & File Forensics

Images attached to a challenge, or downloaded from a target's profiles,
are frequent flag carriers. One pass covers the usual checks:

```bash
sherlockml exif challenge.jpg
```

| Finding | What to do next |
|---------|-----------------|
| `GPS:` line | Open the map link; check `DateTimeOriginal` / GPS time for the "when" |
| `Extension mismatch` | Rename to the real type and open it |
| `Appended data ... contains zip at offset N` | `dd if=challenge.jpg of=out.zip bs=1 skip=N`, then unzip |
| `png:<key>` / `XPComment` / `UserComment` / `xmp` | Read the hidden text; try base64/rot13 if it looks encoded |
| Unusual name in `PNG chunks:` | Custom chunk: inspect it with `pngcheck -v` or a hex editor |
| `software=Photoshop`/`GIMP` | The image was edited; compare timestamps, look for layers/thumbnails |

Beyond what `exif` covers, the usual next tools are `binwalk` (carving
nested files), `zsteg` (PNG/BMP LSB stego), `steghide` (JPEG with a
passphrase) and `exiftool` (vendor maker notes).

---

## Evidence Handling

For investigations that may need to stand up later (reports, disclosures,
incident response), capture as you search:

```bash
sherlockml search johndoe --deep --verify --evidence-dir cases/johndoe -o cases/johndoe/report --format both
cd cases/johndoe/johndoe_*/ && sha256sum -c SHA256SUMS
```

- Each run writes a new timestamped folder; nothing is overwritten.
- `manifest.json` records target, variants, discovery chain, UTC capture
  time and SHA-256 for every saved page.
- Hash the image files you analyse too: `sherlockml exif -o` records
  MD5/SHA-1/SHA-256 for each.

---

## Anonymization

All target-facing traffic (search, `--verify` page fetches, `wayback`,
`scan-github`) goes through the configured proxy. Pass `--proxy` per
command or set it once in config. LLM API calls for `--verify` go
directly to your LLM provider.

### Using Tor

```bash
sherlockml search target --proxy socks5://127.0.0.1:9050
sherlockml wayback target.com --mode domain --proxy socks5://127.0.0.1:9050
```

DNS is resolved by the SOCKS5 proxy, so hostnames don't leak to the local
resolver. `type: tor` and `socks5h://` are accepted as aliases for socks5.

To get a fresh exit IP for each run and every few minutes during long
scans, enable identity rotation (requires `ControlPort 9051` plus
`HashedControlPassword` or `CookieAuthentication 1` in torrc):

```yaml
# config.yaml
proxy:
  enabled: true
  type: socks5
  host: 127.0.0.1
  port: 9050
  rotate: true
  rotate_interval: 120
  control_password: ${TOR_CONTROL_PASSWORD}   # omit for cookie auth
```

### Rate Limiting

Avoid detection:

```yaml
search:
  max_concurrent: 3
  default_rate_limit: 2.0
```

---

## Output Formats

### JSON (Machine-Readable)

```bash
sherlockml search target -o results.json
```

### Markdown (Writeup Ready)

```bash
sherlockml search target -o results.md --format md
```

### Both

```bash
sherlockml search target -o results --format both
# Creates results.json and results.md
```

---

## Troubleshooting

### No Results Found

1. Try username variants: `--variants`
2. Check platform status manually
3. Try alternative spellings
4. Check Wayback Machine

### Rate Limited

1. Lower rate limit: `--rate-limit 1`
2. Enable Tor proxy
3. Wait and retry

### False Positives

SherlockML automatically filters many false positives (soft 404s, empty pages, login walls, redirects, error titles) with multilingual "not found" detection in 9 languages. For remaining borderline results:

1. Check confidence scores in JSON - results with `confidence < 0.7` or `low_confidence: true` in metadata are suspect
2. Verify profiles manually by opening the URL
3. Cross-reference metadata across platforms
