#!/usr/bin/env python3
"""Tests for runtime.observability — Sentry integration and Prometheus export."""

from __future__ import annotations

import logging
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from runtime import observability


@pytest.fixture(autouse=True)
def _reset_sentry_state():
    """Reset the module-level _sentry_initialized flag before each test."""
    observability._sentry_initialized = False
    yield
    observability._sentry_initialized = False
    sys.modules.pop("sentry_sdk", None)


def _install_fake_sentry(init_side_effect=None, push_scope_exc=None):
    """Install a fake sentry_sdk module into sys.modules."""
    fake = types.ModuleType("sentry_sdk")
    fake.init = MagicMock(side_effect=init_side_effect)
    scope = MagicMock()
    scope.__enter__ = MagicMock(return_value=scope)
    scope.__exit__ = MagicMock(return_value=False)
    fake.push_scope = MagicMock(return_value=scope)
    fake.capture_exception = MagicMock()
    fake.capture_message = MagicMock()
    sys.modules["sentry_sdk"] = fake
    return fake, scope


# ---------------------------------------------------------------------------
# init_sentry
# ---------------------------------------------------------------------------


def test_init_sentry_already_initialized(monkeypatch) -> None:
    observability._sentry_initialized = True
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert observability.init_sentry() is True


def test_init_sentry_no_dsn(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert observability.init_sentry() is False
    assert observability._sentry_initialized is False


def test_init_sentry_success(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.5")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "staging")
    monkeypatch.setenv("AIOS_VERSION", "1.2.3")
    fake, _ = _install_fake_sentry()
    assert observability.init_sentry() is True
    assert observability._sentry_initialized is True
    fake.init.assert_called_once()
    _, kwargs = fake.init.call_args
    assert kwargs["dsn"] == "https://example@sentry.io/1"
    assert kwargs["traces_sample_rate"] == 0.5
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == "1.2.3"


def test_init_sentry_import_error(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
    sys.modules.pop("sentry_sdk", None)
    with patch("builtins.__import__", side_effect=ImportError("no sentry")):
        assert observability.init_sentry() is False
    assert observability._sentry_initialized is False


def test_init_sentry_generic_exception(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
    _fake, _ = _install_fake_sentry(init_side_effect=RuntimeError("boom"))
    assert observability.init_sentry() is False
    assert observability._sentry_initialized is False


# ---------------------------------------------------------------------------
# capture_exception
# ---------------------------------------------------------------------------


def test_capture_exception_with_sentry() -> None:
    observability._sentry_initialized = True
    fake, scope = _install_fake_sentry()
    exc = ValueError("test error")
    observability.capture_exception(exc, request_id="abc")
    fake.push_scope.assert_called_once()
    scope.set_context.assert_called_once_with("request_id", "abc")
    fake.capture_exception.assert_called_once_with(exc)


def test_capture_exception_sentry_fails_logs(caplog) -> None:
    observability._sentry_initialized = True
    fake, _ = _install_fake_sentry()
    fake.push_scope.side_effect = RuntimeError("sentry down")
    exc = ValueError("test error")
    with caplog.at_level(logging.ERROR):
        observability.capture_exception(exc, ctx="val")
    # Should not raise; should log the error
    assert any("Failed to capture" in r.message for r in caplog.records)


def test_capture_exception_without_sentry_logs(caplog) -> None:
    observability._sentry_initialized = False
    exc = ValueError("test error")
    with caplog.at_level(logging.ERROR):
        observability.capture_exception(exc, request_id="xyz")
    assert any("Exception:" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# capture_message
# ---------------------------------------------------------------------------


def test_capture_message_with_sentry() -> None:
    observability._sentry_initialized = True
    fake, scope = _install_fake_sentry()
    observability.capture_message("hello", level="warning", user="bob")
    fake.push_scope.assert_called_once()
    scope.set_context.assert_called_once_with("user", "bob")
    fake.capture_message.assert_called_once_with("hello", level="warning")


def test_capture_message_sentry_fails_logs(caplog) -> None:
    observability._sentry_initialized = True
    fake, _ = _install_fake_sentry()
    fake.push_scope.side_effect = RuntimeError("sentry down")
    with caplog.at_level(logging.WARNING):
        observability.capture_message("hello", level="warning")
    assert any("hello" in r.message for r in caplog.records)


def test_capture_message_without_sentry_logs(caplog) -> None:
    observability._sentry_initialized = False
    with caplog.at_level(logging.INFO):
        observability.capture_message("hello", level="info")
    assert any("hello" in r.message for r in caplog.records)


def test_capture_message_default_level(caplog) -> None:
    observability._sentry_initialized = False
    with caplog.at_level(logging.INFO):
        observability.capture_message("default msg")
    assert any("default msg" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# prometheus_export
# ---------------------------------------------------------------------------


def test_prometheus_export_delegates_to_format_metrics() -> None:
    kernel = MagicMock()
    with patch("runtime.metrics.format_metrics", return_value="# metrics\n") as mock_fm:
        result = observability.prometheus_export(kernel)
    mock_fm.assert_called_once_with(kernel)
    assert result == "# metrics\n"
