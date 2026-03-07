"""LLM-powered profile verification for SherlockML.

Visits found profile URLs and uses an LLM to determine whether
the page represents a real/active account or an empty/default page.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from sherlockml.config import LLMConfig

SYSTEM_PROMPT = """\
You are a profile verification assistant. You will receive the HTML content \
of a web page that is supposed to be a user's profile on a platform.

Analyze the page and determine:
1. Is this a REAL profile with actual user content (bio, posts, activity)?
2. Or is this an EMPTY/DEFAULT page (no real content, placeholder, suspended, \
deleted, or generic template)?

Respond with ONLY a JSON object (no markdown fences):
{
  "verdict": "real" | "empty" | "suspicious",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}

- "real": The page shows genuine user activity, bio, posts, or profile data.
- "empty": The page is blank, default, suspended, deleted, or has no user content.
- "suspicious": The page exists but has very minimal content — could be a \
placeholder or abandoned account.
"""

USER_PROMPT_TEMPLATE = """\
Platform: {platform}
URL: {url}
Username searched: {username}

Page content (truncated):
{content}
"""

# Max chars of page content to send to the LLM
_MAX_CONTENT_CHARS = 8000


@dataclass
class VerificationResult:
    """Result of LLM verification for a single profile."""
    platform: str
    url: str
    verdict: str  # "real", "empty", "suspicious"
    confidence: float
    reason: str
    error: str | None = None

    @property
    def is_real(self) -> bool:
        return self.verdict == "real"

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "url": self.url,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reason": self.reason,
            "error": self.error,
        }


def _strip_to_text(html: str) -> str:
    """Strip HTML to meaningful text content for LLM analysis."""
    # Extract structural JSON data before removing scripts
    json_data = re.findall(
        r'<script[^>]*type=["\'](?:application/ld\+json|application/json)["\'][^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Keep some structure hints
    text = re.sub(r"<(h[1-6]|title)[^>]*>", r"\n## ", text, flags=re.IGNORECASE)
    text = re.sub(r"<(p|div|br|li|tr)[^>]*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    text = text.strip()
    
    # If we found JSON data, prepend it so the LLM sees it first
    if json_data:
        json_text = "\n".join(json_data).strip()
        text = f"Structured Data:\n{json_text}\n\nPage Text:\n{text}"
        
    return text[:_MAX_CONTENT_CHARS]


async def _call_openai(
    session: aiohttp.ClientSession,
    config: "LLMConfig",
    messages: list[dict[str, str]],
) -> str:
    """Call OpenAI-compatible chat completion API."""
    base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }

    payload = {
        "model": config.model,
        "messages": messages,
        "max_tokens": config.max_tokens,
        "temperature": 0.1,
    }

    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise RuntimeError(f"LLM API error {resp.status}: {body[:300]}")
        data = await resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_anthropic(
    session: aiohttp.ClientSession,
    config: "LLMConfig",
    messages: list[dict[str, str]],
) -> str:
    """Call Anthropic Messages API."""
    url = "https://api.anthropic.com/v1/messages"

    # Extract system message
    system_text = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        else:
            user_messages.append(msg)

    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.api_key,
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "system": system_text,
        "messages": user_messages,
    }

    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise RuntimeError(f"Anthropic API error {resp.status}: {body[:300]}")
        data = await resp.json()
        return data["content"][0]["text"]


async def _call_gemini(
    session: aiohttp.ClientSession,
    config: "LLMConfig",
    messages: list[dict[str, str]],
) -> str:
    """Call Google Gemini (Generative Language) API."""
    base_url = (
        config.base_url
        or "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    url = f"{base_url}/models/{config.model}:generateContent?key={config.api_key}"

    # Convert messages to Gemini format
    system_text = ""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        else:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Prepend system instruction into first user message if present
    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": config.max_tokens,
            "temperature": 0.1,
        },
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    headers = {"Content-Type": "application/json"}

    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise RuntimeError(f"Gemini API error {resp.status}: {body[:300]}")
        data = await resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Parse the JSON verdict from the LLM response."""
    cleaned = raw.strip()
    
    # 1. Try to extract JSON from markdown fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Try parsing the whole cleaned string (removing leading/trailing fences if present)
    cleaned_fences = cleaned
    if cleaned_fences.startswith("```"):
        cleaned_fences = re.sub(r"^```\w*\n?", "", cleaned_fences)
        cleaned_fences = re.sub(r"\n?```$", "", cleaned_fences)

    try:
        return json.loads(cleaned_fences)
    except json.JSONDecodeError:
        pass

    # 3. Fallback: try to find the outermost JSON object using regex
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
            
    return {
        "verdict": "suspicious",
        "confidence": 0.3,
        "reason": f"Could not parse LLM response: {raw[:100]}",
    }


async def verify_profile(
    platform: str,
    url: str,
    username: str,
    raw_html: str,
    config: "LLMConfig",
    session: aiohttp.ClientSession,
) -> VerificationResult:
    """Verify a single profile page using the LLM.

    Args:
        platform: Platform name
        url: Profile URL
        username: Username searched
        raw_html: Raw HTML content of the page
        config: LLM configuration
        session: aiohttp session for API calls

    Returns:
        VerificationResult with the LLM's verdict
    """
    content = _strip_to_text(raw_html)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                platform=platform,
                url=url,
                username=username,
                content=content,
            ),
        },
    ]

    try:
        if config.provider == "anthropic":
            raw_response = await _call_anthropic(session, config, messages)
        elif config.provider == "gemini":
            raw_response = await _call_gemini(session, config, messages)
        else:
            raw_response = await _call_openai(session, config, messages)

        parsed = _parse_llm_response(raw_response)

        return VerificationResult(
            platform=platform,
            url=url,
            verdict=parsed.get("verdict", "suspicious"),
            confidence=float(parsed.get("confidence", 0.5)),
            reason=parsed.get("reason", ""),
        )

    except Exception as e:
        return VerificationResult(
            platform=platform,
            url=url,
            verdict="suspicious",
            confidence=0.0,
            reason="",
            error=str(e),
        )


async def verify_results(
    results: list[dict[str, Any]],
    config: "LLMConfig",
) -> list[VerificationResult]:
    """Verify multiple search results in parallel.

    Args:
        results: List of dicts with keys: platform, url, username, raw_html
        config: LLM configuration

    Returns:
        List of VerificationResult objects
    """
    if not config.api_key:
        raise ValueError(
            "LLM API key not configured. Set llm.api_key in config "
            "or the appropriate environment variable."
        )

    semaphore = asyncio.Semaphore(config.max_concurrent_verifications)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async def _verify_one(item: dict[str, Any]) -> VerificationResult:
            async with semaphore:
                return await verify_profile(
                    platform=item["platform"],
                    url=item["url"],
                    username=item["username"],
                    raw_html=item["raw_html"],
                    config=config,
                    session=session,
                )

        tasks = [_verify_one(item) for item in results]
        return await asyncio.gather(*tasks)
