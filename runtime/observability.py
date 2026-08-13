#!/usr/bin/env python3
"""Observability integrations: Sentry error tracking and Prometheus export.

Sentry integration is optional and activated only when SENTRY_DSN is set.
Prometheus export is always available via ``format_metrics``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_sentry_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry SDK if SENTRY_DSN is set.

    Returns True if Sentry was initialized, False otherwise.
    """
    global _sentry_initialized
    if _sentry_initialized:
        return True
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
            release=os.environ.get("AIOS_VERSION", "unknown"),
        )
        _sentry_initialized = True
        logger.info("Sentry initialized successfully")
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed; SENTRY_DSN is set but ignored")
        return False
    except Exception as exc:
        logger.error("Failed to initialize Sentry: %s", exc)
        return False


def capture_exception(exc: Exception, **context: Any) -> None:
    """Capture an exception in Sentry if initialized, otherwise log it."""
    if _sentry_initialized:
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                sentry_sdk.capture_exception(exc)
        except Exception:
            logger.error("Failed to capture exception in Sentry: %s", exc)
    else:
        logger.error("Exception: %s | Context: %s", exc, context)


def capture_message(msg: str, level: str = "info", **context: Any) -> None:
    """Capture a message in Sentry if initialized, otherwise log it."""
    if _sentry_initialized:
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                sentry_sdk.capture_message(msg, level=level)
        except Exception:
            logger.log(getattr(logging, level.upper(), logging.INFO), msg)
    else:
        logger.log(getattr(logging, level.upper(), logging.INFO), msg)


def prometheus_export(kernel: Any) -> str:
    """Export Prometheus-compatible metrics from the kernel.

    This is a thin wrapper around ``format_metrics`` for the observability module.
    """
    from .metrics import format_metrics

    return format_metrics(kernel)
