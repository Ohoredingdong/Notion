"""Separate the initiating GitHub event from the code checkout that ran it.

This is local execution metadata, not price validation or an authenticated
attestation. Staged forecast data directories are never used as the code root.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess


CODE_ROOT = Path(__file__).resolve().parents[1]
RESOLVED = "git_head_resolved"


class SourceIdentityError(RuntimeError):
    """A CI producer cannot safely label its execution source."""


def valid_commit(value):
    return (isinstance(value, str)
            and re.fullmatch(r"[a-fA-F0-9]{40}", value) is not None
            and value != "0" * 40)


def _checked_out_commit(code_root):
    root = Path(code_root).resolve()
    options = dict(check=True, capture_output=True, text=True, timeout=5)
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                         **options).stdout.strip()
    if Path(top).resolve() != root:
        raise ValueError("unexpected_code_repository")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
                          **options).stdout.strip()
    if not valid_commit(head):
        raise ValueError("invalid_code_commit")
    return head


def execution_identity(code_root=None, environ=None):
    """Resolve code HEAD, retaining GITHUB_SHA only as event_commit.

    CI errors propagate before collection, model execution or output writes.
    A local non-Git fixture remains explicitly unverified instead of pretending
    its environment's event SHA identifies an unavailable checkout.
    """
    env = os.environ if environ is None else environ
    event = env.get("GITHUB_SHA") or None
    ci = env.get("GITHUB_ACTIONS") == "true"
    if ci and not valid_commit(event):
        raise SourceIdentityError("ci_event_commit_missing_or_invalid")
    identity = {"event_commit": event, "source_commit": None,
                "source_identity_status": "unverified"}
    try:
        identity["source_commit"] = _checked_out_commit(
            CODE_ROOT if code_root is None else code_root)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if ci:
            raise SourceIdentityError("ci_code_checkout_identity_unavailable") from exc
        identity["source_identity_reason"] = "git_head_unavailable"
        return identity
    identity["source_identity_status"] = RESOLVED
    return identity
