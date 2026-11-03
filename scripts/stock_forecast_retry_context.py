"""Dependency-free retry ownership shared by the bounded controller and OHLC reader.

This module must stay standard-library-only so independent synthetic audits can
exercise SafeCollector without installing pandas, yfinance or market-data code.
"""
from contextlib import contextmanager
from contextvars import ContextVar

_EXTERNAL_RETRY_OWNER = ContextVar("stock_forecast_external_retry_owner", default=False)


@contextmanager
def external_source_retry_owner():
    """Let the outer bounded collector own cache-lock retries in this context."""
    token = _EXTERNAL_RETRY_OWNER.set(True)
    try:
        yield
    finally:
        _EXTERNAL_RETRY_OWNER.reset(token)


def outer_source_retry_owned():
    """True only while this execution context is under outer retry control."""
    return _EXTERNAL_RETRY_OWNER.get()
