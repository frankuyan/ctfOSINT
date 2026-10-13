"""Tests for Tor identity rotation against a fake Tor control port."""

import asyncio
import logging

import pytest

import sherlockml.tor as tor
from sherlockml.config import Config
from sherlockml.enum.orchestrator import Orchestrator
from sherlockml.net import create_session
from sherlockml.tor import TorControlError, identity_rotation, new_identity, rotation_enabled


class FakeTorControl:
    """Minimal Tor ControlPort: PROTOCOLINFO, AUTHENTICATE, SIGNAL NEWNYM, QUIT."""

    def __init__(self, methods="NULL", password=None, cookie_file=None):
        self.methods = methods
        self.password = password
        self.cookie_file = cookie_file
        self.commands: list[str] = []
        self.newnym_count = 0
        self.server = None

    @property
    def port(self) -> int:
        return self.server.sockets[0].getsockname()[1]

    async def __aenter__(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(self, *exc):
        self.server.close()
        await self.server.wait_closed()

    def _expected_auth(self):
        if self.password is not None:
            escaped = self.password.replace("\\", "\\\\").replace('"', '\\"')
            return f'AUTHENTICATE "{escaped}"'
        if self.cookie_file is not None:
            return f"AUTHENTICATE {self.cookie_file.read_bytes().hex()}"
        return "AUTHENTICATE"

    async def _handle(self, reader, writer):
        authed = False
        try:
            while line := await reader.readline():
                cmd = line.decode().rstrip("\r\n")
                self.commands.append(cmd)
                if cmd == "PROTOCOLINFO 1":
                    auth = f"250-AUTH METHODS={self.methods}"
                    if self.cookie_file is not None:
                        auth += f' COOKIEFILE="{self.cookie_file}"'
                    writer.write(
                        f'250-PROTOCOLINFO 1\r\n{auth}\r\n250-VERSION Tor="0.4.8.0"\r\n250 OK\r\n'.encode()
                    )
                elif cmd.startswith("AUTHENTICATE"):
                    if cmd == self._expected_auth():
                        authed = True
                        writer.write(b"250 OK\r\n")
                    else:
                        writer.write(b"515 Authentication failed: Password did not match\r\n")
                        await writer.drain()
                        break
                elif cmd == "SIGNAL NEWNYM" and authed:
                    self.newnym_count += 1
                    writer.write(b"250 OK\r\n")
                elif cmd == "QUIT":
                    writer.write(b"250 closing connection\r\n")
                    await writer.drain()
                    break
                else:
                    writer.write(b"514 Authentication required.\r\n")
                await writer.drain()
        finally:
            writer.close()


def _config(port: int, **proxy) -> Config:
    config = Config()
    config.proxy.enabled = True
    config.proxy.host = "127.0.0.1"
    config.proxy.control_port = port
    config.proxy.rotate = True
    for key, value in proxy.items():
        setattr(config.proxy, key, value)
    return config


class TestNewIdentity:
    async def test_null_auth(self):
        async with FakeTorControl() as fake:
            await new_identity("127.0.0.1", fake.port)
        assert fake.commands == ["PROTOCOLINFO 1", "AUTHENTICATE", "SIGNAL NEWNYM", "QUIT"]
        assert fake.newnym_count == 1

    async def test_password_auth_is_quoted(self):
        password = 'p"ass\\word'
        async with FakeTorControl("HASHEDPASSWORD", password=password) as fake:
            await new_identity("127.0.0.1", fake.port, password=password)
        assert fake.newnym_count == 1

    async def test_wrong_password(self):
        async with FakeTorControl("HASHEDPASSWORD", password="right") as fake:
            with pytest.raises(TorControlError, match="Authentication failed"):
                await new_identity("127.0.0.1", fake.port, password="wrong")
        assert fake.newnym_count == 0

    async def test_password_required_but_missing(self):
        async with FakeTorControl("HASHEDPASSWORD", password="secret") as fake:
            with pytest.raises(TorControlError, match="control_password"):
                await new_identity("127.0.0.1", fake.port)

    async def test_cookie_auth(self, tmp_path):
        cookie = tmp_path / "control_auth_cookie"
        cookie.write_bytes(bytes(range(32)))
        async with FakeTorControl("COOKIE,SAFECOOKIE", cookie_file=cookie) as fake:
            await new_identity("127.0.0.1", fake.port)
        assert fake.newnym_count == 1

    async def test_empty_password_falls_back_to_cookie(self, tmp_path):
        # control_password: ${TOR_CONTROL_PASSWORD} with the variable unset
        cookie = tmp_path / "control_auth_cookie"
        cookie.write_bytes(b"\x01" * 32)
        async with FakeTorControl("COOKIE", cookie_file=cookie) as fake:
            await new_identity("127.0.0.1", fake.port, password="")
        assert fake.newnym_count == 1

    async def test_unreadable_cookie(self, tmp_path):
        missing = tmp_path / "gone"
        async with FakeTorControl("COOKIE", cookie_file=missing) as fake:
            with pytest.raises(TorControlError, match="cannot read Tor auth cookie"):
                await new_identity("127.0.0.1", fake.port)

    async def test_unreachable(self):
        async with FakeTorControl() as fake:
            port = fake.port
        with pytest.raises(OSError):
            await new_identity("127.0.0.1", port, timeout=2)


class TestRotation:
    @pytest.fixture(autouse=True)
    def fast_interval(self, monkeypatch):
        monkeypatch.setattr(tor, "MIN_ROTATE_INTERVAL", 0.05)

    async def test_rotates_at_start_and_periodically_then_stops(self):
        async with FakeTorControl() as fake:
            async with identity_rotation(_config(fake.port, rotate_interval=0)):
                assert fake.newnym_count == 1  # fresh identity before any request
                await asyncio.sleep(0.3)
            during = fake.newnym_count
            await asyncio.sleep(0.2)
        assert during >= 3
        assert fake.newnym_count == during  # loop cancelled on exit

    async def test_disabled_unless_rotate_set(self):
        async with FakeTorControl() as fake:
            async with identity_rotation(_config(fake.port, rotate=False)):
                await asyncio.sleep(0.1)
            async with identity_rotation(_config(fake.port, rotate_enabled=False)):
                await asyncio.sleep(0.1)
        assert fake.commands == []

    async def test_failure_warns_and_scan_continues(self, caplog):
        async with FakeTorControl("HASHEDPASSWORD", password="right") as fake:
            config = _config(fake.port, rotate_interval=0, control_password="wrong")
            with caplog.at_level(logging.WARNING, logger="sherlockml.tor"):
                async with identity_rotation(config):
                    ran = True
                    await asyncio.sleep(0.2)
        assert ran
        assert fake.commands.count("PROTOCOLINFO 1") == 1  # no retry loop
        assert "Tor identity rotation disabled" in caplog.text

    async def test_search_rotates(self, stub_platform):
        async with FakeTorControl() as fake:
            config = _config(fake.port)
            results = await Orchestrator(config).search(["alice"], [stub_platform()])
        assert results.found_count == 1
        assert fake.newnym_count == 1


class TestConfig:
    def test_rotation_enabled_requires_proxy_and_rotate(self):
        config = Config()
        config.proxy.rotate = True
        assert not rotation_enabled(config.proxy)
        config.proxy.enabled = True
        assert rotation_enabled(config.proxy)
        config.proxy.rotate_enabled = False
        assert not rotation_enabled(config.proxy)

    def test_control_password_env_expansion(self, monkeypatch):
        from sherlockml.config import ProxyConfig

        monkeypatch.setenv("TOR_CONTROL_PASSWORD", "s3cret")
        proxy = ProxyConfig(control_password="${TOR_CONTROL_PASSWORD}")
        assert proxy.control_password == "s3cret"

    async def test_keep_alive_off_only_when_rotating(self):
        config = _config(9051)
        async with create_session(config) as session:
            assert session.connector.force_close
        config.proxy.rotate = False
        async with create_session(config) as session:
            assert not session.connector.force_close
