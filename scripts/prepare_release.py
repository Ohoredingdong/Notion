"""Prepare a verified static candidate. This command NEVER publishes or merges."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

from check_changed import ROOT, git, source_digest, source_files

PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".jsonl", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".mp3", ".mp4"}


def verify_report(root, report):
    if report.get("schema_version") != 1 or report.get("status") != "passed":
        raise ValueError("Candidate blocked: checks failed, incomplete, or not a recognized report")
    if report.get("unverified"):
        raise ValueError("Candidate blocked: required checks remain unverified")
    checks = report.get("checks", [])
    if not checks or any(c.get("status") != "passed" for c in checks):
        raise ValueError("Candidate blocked: missing or unsuccessful check")
    if any(c.get("returncode", 0) != 0 for c in checks):
        raise ValueError("Candidate blocked: check exit code is not successful")
    if not any(c.get("returncode") == 0 for c in checks):
        raise ValueError("Candidate blocked: no executed regression suite")
    required = report.get("plan", {}).get("browser_required", [])
    for group in required:
        if not any(c.get("name") == group + "-browser" and c.get("returncode") == 0 for c in checks):
            raise ValueError(f"Candidate blocked: {group} browser check did not execute")
    if git(root, "status", "--porcelain").strip():
        raise ValueError("Candidate blocked: source must be committed and clean")
    if git(root, "rev-parse", "HEAD").decode().strip() != report.get("head_sha"):
        raise ValueError("Candidate blocked: report belongs to another commit")
    if source_digest(root) != report.get("source_digest"):
        raise ValueError("Candidate blocked: source differs from validated content")


def public_files(root):
    for name in source_files(root):
        path = Path(name)
        if path.parts[0] in {".github", ".agents", "scripts", "tests", "docs", "services", "supabase", "backups"}:
            continue
        if path.name == ".nojekyll" or path.suffix.lower() in PUBLIC_SUFFIXES:
            yield name


def prepare(root, report_path, output):
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    verify_report(root, report)
    if output.resolve().is_relative_to(root.resolve()) and not output.resolve().is_relative_to(root / ".dev-artifacts"):
        raise ValueError("Candidate output must be outside checkout or inside ignored .dev-artifacts")
    if output.exists():
        raise ValueError("Candidate output already exists; choose a fresh output path")
    names = set(public_files(root))
    # Read immutable Git objects from the validated commit, never re-read mutable
    # working files between hashing and archiving.
    source = git(root, "archive", "--format=tar", report["head_sha"])
    entries = {}
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:") as committed:
        for member in committed.getmembers():
            if member.name in names:
                if not member.isfile():
                    raise ValueError("Candidate blocked: unsupported public file type")
                entries[member.name] = committed.extractfile(member).read()
    if not entries or set(entries) != names:
        raise ValueError("Candidate blocked: public files differ from validated commit")
    manifest = {"kind": "review-only-not-deployed", "source_commit": report["head_sha"],
                "source_digest": report["source_digest"], "validation_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".widget-candidate-", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
        with tarfile.open(temporary, "w:gz") as archive:
            for name, data in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
            info = tarfile.TarInfo("_candidate-manifest.json")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        verify_report(root, report)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = prepare(ROOT, args.report, args.output)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"REVIEW CANDIDATE ONLY: {args.output}; {len(manifest['files'])} files; commit {manifest['source_commit']}; NOT DEPLOYED")


if __name__ == "__main__":
    main()
