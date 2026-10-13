"""Tor identity rotation over the Tor control port.

With ``proxy.rotate: true`` SherlockML sends ``SIGNAL NEWNYM`` when a scan
starts and then every ``proxy.rotate_interval`` seconds, so a long scan
isn't served from a single exit IP and each investigation starts on fresh
circuits.  Tor must expose a ControlPort (``proxy.control_port``, default
9051) on ``proxy.host`` and accept one of:

* ``HashedControlPassword`` — set ``proxy.control_password``
* ``CookieAuthentication 1`` — the cookie file Tor reports must be readable
* no authentication (only sensible on an isolated network/container)

Rotation is best effort: if the control port can't be reached or refuses
us, a warning is logged and the scan carries on without rotating.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sherlockml.config import Config, ProxyConfig

logger = logging.getLogger(__name__)

# Tor ignores NEWNYM more often than once every 10 seconds
MIN_ROTATE_INTERVAL = 10.0
CONTROL_TIMEOUT = 10.0


class TorControlError(RuntimeError):
    """The control port replied with an error or demanded unknown auth."""


def rotation_enabled(proxy: ProxyConfig) -> bool:
    """Whether identity rotation should run for this proxy config."""
    return proxy.enabled and proxy.rotate and proxy.rotate_enabled


def _quote(value: str) -> str:
    """Encode a control-protocol QuotedString."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


async def _command(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    line: str,
) -> list[str]:
    """Send one command and return its reply lines ("250-..." ... "250 OK")."""
    writer.write(line.encode("utf-8") + b"\r\n")
    await writer.drain()
    reply: list[str] = []
    while True:
        raw = await reader.readline()
        if not raw:
            raise TorControlError(f"control port closed the connection after {line.split()[0]}")
        text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        reply.append(text)
        # "250 OK" ends a reply; "250-" and "250+" lines continue it
        if len(text) >= 4 and text[3] == " ":
            return reply


def _expect_ok(reply: list[str], what: str) -> None:
    if not reply[-1].startswith("250"):
        raise TorControlError(f"{what} failed: {reply[-1]}")


async def _authenticate(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    password: str | None,
) -> None:
    info = await _command(reader, writer, "PROTOCOLINFO 1")
    _expect_ok(info, "PROTOCOLINFO")
    auth = next((line[4:] for line in info if line[4:].startswith("AUTH ")), "")
    methods_match = re.search(r"METHODS=(\S+)", auth)
    methods = set(methods_match.group(1).split(",")) if methods_match else set()
    cookie_match = re.search(r'COOKIEFILE="((?:[^"\\]|\\.)*)"', auth)

    # An empty password means "not set": ${TOR_CONTROL_PASSWORD} expands to
    # "" when the variable is missing, and cookie/no-auth should still work.
    if password:
        command = f"AUTHENTICATE {_quote(password)}"
    elif "NULL" in methods:
        command = "AUTHENTICATE"
    elif "COOKIE" in methods and cookie_match:
        cookie_path = re.sub(r"\\(.)", r"\1", cookie_match.group(1))
        try:
            cookie = Path(cookie_path).read_bytes()
        except OSError as e:
            raise TorControlError(f"cannot read Tor auth cookie {cookie_path}: {e}") from e
        command = f"AUTHENTICATE {cookie.hex()}"
    else:
        offered = ",".join(sorted(methods)) or "unknown"
        raise TorControlError(
            f"Tor control port requires authentication ({offered}); "
            "set proxy.control_password"
        )
    _expect_ok(await _command(reader, writer, command), "AUTHENTICATE")


async def new_identity(
    host: str,
    port: int,
    password: str | None = None,
    timeout: float = CONTROL_TIMEOUT,
) -> None:
    """Ask Tor for clean circuits (``SIGNAL NEWNYM``).

    Raises:
        OSError: control port unreachable
        TimeoutError: no reply within ``timeout``
        TorControlError: authentication or the signal was refused
    """
    async def run() -> None:
        reader, writer = await asyncio.open_connection(host, port)
        try:
            await _authenticate(reader, writer, password)
            _expect_ok(await _command(reader, writer, "SIGNAL NEWNYM"), "SIGNAL NEWNYM")
            await _command(reader, writer, "QUIT")
        finally:
            writer.close()
            with suppress(OSError):
                await writer.wait_closed()

    await asyncio.wait_for(run(), timeout)


async def _rotate(proxy: ProxyConfig) -> bool:
    """One rotation; returns False (after warning) if it failed."""
    try:
        await new_identity(proxy.host, proxy.control_port, proxy.control_password)
    except (TimeoutError, OSError, TorControlError) as e:
        logger.warning(
            "Tor identity rotation disabled (control port %s:%s): %s",
            proxy.host, proxy.control_port, str(e) or type(e).__name__,
        )
        return False
    logger.info("Requested a new Tor identity")
    return True


async def _rotation_loop(proxy: ProxyConfig) -> None:
    interval = max(MIN_ROTATE_INTERVAL, float(proxy.rotate_interval))
    while True:
        await asyncio.sleep(interval)
        if not await _rotate(proxy):
            return


@asynccontextmanager
async def identity_rotation(config: Config) -> AsyncIterator[None]:
    """Rotate the Tor identity now and periodically while the block runs.

    A no-op unless ``rotation_enabled(config.proxy)``.
    """
    if not rotation_enabled(config.proxy) or not await _rotate(config.proxy):
        yield
        return

    task = asyncio.create_task(_rotation_loop(config.proxy))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
