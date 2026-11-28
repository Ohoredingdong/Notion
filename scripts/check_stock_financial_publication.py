"""Fail closed before a partial official-financial refresh can publish a new catalogue.

This gate is separate from identity validation: retained historical coverage may
be valid even when the current provider attempt failed. Never equate the two.
"""
from __future__ import annotations

import json
from pathlib import Path


def require_publishable_refresh(document):
    if document.get("current_run_failed") is not False:
        raise ValueError("current_financial_refresh_unverified_do_not_publish")
    return document


def main():
    path = Path("stock-financial-coverage.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        require_publishable_refresh(data)
    except ValueError as exc:
        print("CURRENT_REFRESH_REJECTED", data.get("refresh_status"), str(exc))
        raise SystemExit(1) from exc
    print("CURRENT_REFRESH_VERIFIED_FOR_PUBLICATION", data.get("refresh_status"))
    # Catalogue identity verification and the remote-source lease remain
    # separate required workflow steps. This gate grants no trading approval.


if __name__ == "__main__":
    main()
