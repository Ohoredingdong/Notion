#!/usr/bin/env python3
"""Package and promote the auction widget without touching other site data.

Promotion is local only: callers own checkout, CI approval, commits and pushes.
Runtime files are replaced atomically one at a time, with the release manifest
last; a failed replacement rolls earlier replacements back. Git publication of
the complete successful change is the caller's transaction boundary.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import stat
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


MANIFEST = "auction-release.json"
SOURCE_TREE = "_auction"
REQUIRED = frozenset({"auction-study.html", "assets/auction-study.js",
                      "assets/auction-study.css", "assets/auction-study-model.js",
                      "assets/auction-study-format.js"})
PUBLIC_REQUIRED = REQUIRED - {"assets/auction-study-format.js"}
SHA40 = re.compile(r"[0-9a-fA-F]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCRIPT = re.compile(r"assets/auction-study[^/]*\.(?:js|css)\Z")


class ReleaseError(ValueError):
    pass


@dataclass(frozen=True)
class Bundle:
    manifest: dict
    contents: dict[str, bytes]
    manifest_bytes: bytes


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def relative_path(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise ReleaseError("Invalid runtime path")
    path = PurePosixPath(name)
    if path.is_absolute() or path.as_posix() != name or any(p in (".", "..") for p in path.parts):
        raise ReleaseError("Unsafe runtime path: " + name)
    return path


def allowed(name: str) -> bool:
    path = relative_path(name)
    return (name == "auction-study.html" or bool(SCRIPT.fullmatch(name)) or
            (name.startswith("assets/auction-practice/") and path.suffix in (".png", ".webp", ".jpg")))


def safe_path(path: Path) -> Path:
    """Reject existing symlinks in the path, including all parent components."""
    path = Path(os.path.abspath(path))
    for current in [*reversed(path.parents), path]:
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ReleaseError("Symlink is not allowed: " + str(current))
        if current != path and not stat.S_ISDIR(mode):
            raise ReleaseError("Parent is not a directory: " + str(current))
    return path


def read_file(path: Path) -> bytes:
    path = safe_path(path)
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise ReleaseError("Expected a regular file: " + str(path))
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ReleaseError("Expected a regular file: " + str(path))
        return handle.read()


def tree_files(directory: Path) -> dict[str, Path]:
    directory = safe_path(directory)
    if not directory.is_dir():
        raise ReleaseError("Expected a directory: " + str(directory))
    result = {}
    def walk_error(error):
        raise error
    for parent, directories, files in os.walk(directory, followlinks=False, onerror=walk_error):
        for name in directories + files:
            path = safe_path(Path(parent) / name)
            mode = path.lstat().st_mode
            if name in directories and not stat.S_ISDIR(mode):
                raise ReleaseError("Expected a directory: " + str(path))
            if name in files:
                if not stat.S_ISREG(mode):
                    raise ReleaseError("Expected a regular file: " + str(path))
                result[path.relative_to(directory).as_posix()] = path
    return result


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError("Duplicate manifest key: " + str(key))
        result[key] = value
    return result


def parse_manifest(body: bytes, *, legacy_public: bool = False) -> dict:
    try:
        manifest = json.loads(body, object_pairs_hook=no_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ReleaseError("Invalid release manifest") from error
    if not isinstance(manifest, dict) or set(manifest) != {"version", "source_sha", "files"}:
        raise ReleaseError("Invalid release manifest fields")
    if type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ReleaseError("Unsupported release manifest version")
    if not isinstance(manifest["source_sha"], str) or not SHA40.fullmatch(manifest["source_sha"]):
        raise ReleaseError("source_sha must be a full 40-character commit SHA")
    files = manifest["files"]
    required = PUBLIC_REQUIRED if legacy_public else REQUIRED
    if not isinstance(files, dict) or not required.issubset(files):
        raise ReleaseError("Release is missing required auction runtime files")
    for name, expected in files.items():
        if not allowed(name) or not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ReleaseError("Invalid runtime manifest entry: " + str(name))
    return manifest


def package(source: Path, output: Path, source_sha: str) -> Bundle:
    if not isinstance(source_sha, str) or not SHA40.fullmatch(source_sha):
        raise ReleaseError("source_sha must be a full 40-character commit SHA")
    source, output = safe_path(source), safe_path(output)
    if source == output or source in output.parents or output in source.parents:
        raise ReleaseError("Source and bundle directories must not overlap")
    entries = tree_files(source)
    for name in entries:
        if not allowed(name):
            raise ReleaseError("Unapproved source file: " + name)
    if not REQUIRED.issubset(entries):
        raise ReleaseError("Source is missing required auction runtime files")
    contents = {name: read_file(entries[name]) for name in sorted(entries)}
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ReleaseError("Bundle output must be absent or empty")
    manifest = {"version": 1, "source_sha": source_sha.lower(),
                "files": {name: digest(body) for name, body in contents.items()}}
    body = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in {**contents, MANIFEST: body}.items():
        target = safe_path(output / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return verify_bundle(output)


def verify_bundle(directory: Path) -> Bundle:
    directory = safe_path(directory)
    body = read_file(directory / MANIFEST)
    manifest = parse_manifest(body)
    actual = tree_files(directory)
    if set(actual) != set(manifest["files"]) | {MANIFEST}:
        raise ReleaseError("Bundle contains missing or unlisted files")
    contents = {}
    for name, expected in manifest["files"].items():
        payload = read_file(actual[name])
        if digest(payload) != expected:
            raise ReleaseError("Bundle hash mismatch: " + name)
        contents[name] = payload
    return Bundle(manifest, contents, body)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True)
    if result.returncode:
        raise ReleaseError("Git source validation failed: " + result.stderr.strip())
    return result.stdout.strip()


def source_tree(root: Path, revision: str) -> str:
    git(root, "rev-parse", "--verify", revision + "^{commit}")
    tree = git(root, "rev-parse", "--verify", revision + ":" + SOURCE_TREE)
    if git(root, "cat-file", "-t", tree) != "tree" or not git(root, "ls-tree", "-r", tree):
        raise ReleaseError("Source commit must contain a nonempty _auction tree")
    return tree


def check_source(bundle: Bundle, root: Path) -> None:
    root = safe_path(root)
    if Path(git(root, "rev-parse", "--show-toplevel")) != root:
        raise ReleaseError("Publication root must be the Git repository root")
    current = source_tree(root, "HEAD")
    original = source_tree(root, bundle.manifest["source_sha"].lower())
    if current != original:
        raise ReleaseError("Auction source changed after validation; refusing an older bundle")


def runtime_files(root: Path) -> dict[str, Path]:
    root = safe_path(root)
    if not root.is_dir():
        raise ReleaseError("Expected a site root directory")
    result = {}
    html = safe_path(root / "auction-study.html")
    if html.exists():
        result["auction-study.html"] = html
    assets = safe_path(root / "assets")
    if assets.exists():
        if not assets.is_dir():
            raise ReleaseError("Site assets is not a directory")
        for path in assets.iterdir():
            name = "assets/" + path.name
            if allowed(name):
                result[name] = safe_path(path)
    practice = safe_path(root / "assets/auction-practice")
    if practice.exists():
        for name, path in tree_files(practice).items():
            relative = "assets/auction-practice/" + name
            if allowed(relative):
                result[relative] = path
    return result


def check_public(root: Path) -> Bundle:
    root = safe_path(root)
    body = read_file(root / MANIFEST)
    manifest = parse_manifest(body, legacy_public=True)
    actual = runtime_files(root)
    if set(actual) != set(manifest["files"]):
        raise ReleaseError("Public runtime contains missing or unlisted auction files")
    contents = {}
    for name, expected in manifest["files"].items():
        payload = read_file(actual[name])
        if digest(payload) != expected:
            raise ReleaseError("Public runtime hash mismatch: " + name)
        contents[name] = payload
    return Bundle(manifest, contents, body)


def promote(directory: Path, root: Path) -> Bundle:
    bundle = verify_bundle(directory)
    root = safe_path(root)
    check_source(bundle, root)
    if set(runtime_files(root)) - set(bundle.contents):
        raise ReleaseError("Existing auction assets must stay in the validated bundle")
    payloads = {**bundle.contents, MANIFEST: bundle.manifest_bytes}
    originals = {}
    for name in payloads:
        target = safe_path(root / name)
        originals[name] = read_file(target) if target.exists() else None
    with tempfile.TemporaryDirectory(prefix=".auction-release-", dir=root) as temporary:
        staging = Path(temporary)
        for name, payload in payloads.items():
            staged = staging / name
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(payload)
        changed = []
        try:
            for name in payloads:
                target = safe_path(root / name)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / name, target)
                changed.append(name)
        except (OSError, ReleaseError):
            for name in reversed(changed):
                target = safe_path(root / name)
                if originals[name] is None:
                    target.unlink()
                else:
                    backup = staging / name
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_bytes(originals[name])
                    os.replace(backup, target)
            raise
    check_public(root)
    return bundle


class HTTPSRedirectsOnly(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        target = urlsplit(new_url)
        if target.scheme != "https" or target.username or target.password:
            raise ReleaseError("Refusing a non-HTTPS public verification redirect")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def summary(message: str) -> None:
    location = os.environ.get("GITHUB_STEP_SUMMARY")
    if location:
        with open(location, "a", encoding="utf-8") as handle:
            handle.write(message + "\n\n")


def public_body(response, expected_size: int, deadline: float) -> bytes:
    """Bound response size and recheck the total deadline between socket reads."""
    chunks = []
    length = 0
    while length <= expected_size:
        if time.monotonic() >= deadline:
            raise TimeoutError("Public verification deadline exceeded")
        chunk = response.read1(min(65536, expected_size + 1 - length))
        if not chunk:
            break
        chunks.append(chunk)
        length += len(chunk)
    return b"".join(chunks)


def verify_public(directory: Path, base_url: str, attempts: int = 36, delay: float = 10,
                  timeout: float = 15, max_seconds: float = 600) -> None:
    bundle = verify_bundle(directory)
    url = urlsplit(base_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
        raise ReleaseError("Public base URL must be HTTPS without credentials, query or fragment")
    if (type(attempts) is not int or attempts < 1 or
            not all(math.isfinite(value) for value in (delay, timeout, max_seconds)) or
            delay < 0 or timeout <= 0 or max_seconds <= 0):
        raise ReleaseError("Invalid public verification retry limits")
    opener = build_opener(HTTPSRedirectsOnly(), HTTPSHandler(context=ssl.create_default_context()))
    expected = {**bundle.contents, MANIFEST: bundle.manifest_bytes}
    deadline = time.monotonic() + max_seconds
    last_error = None
    for attempt in range(attempts):
        try:
            for name, payload in expected.items():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Public verification deadline exceeded")
                query = urlencode({"SOURCE_SHA": bundle.manifest["source_sha"]})
                address = base_url.rstrip("/") + "/" + quote(name, safe="/") + "?" + query
                request = Request(address, headers={"Cache-Control": "no-cache"})
                with opener.open(request, timeout=min(timeout, remaining)) as response:
                    if response.status != 200 or digest(public_body(response, len(payload), deadline)) != digest(payload):
                        raise ReleaseError("Public hash mismatch: " + name)
            message = ("VERIFIED_PUBLIC_AUCTION_RELEASE " + bundle.manifest["source_sha"] +
                       " (" + str(len(expected)) + " files including release manifest)")
            print(message, flush=True)
            summary(message)
            return
        except (HTTPError, URLError, OSError, ReleaseError) as error:
            last_error = error
            print("Awaiting public auction release: " + str(error), flush=True)
        remaining = deadline - time.monotonic()
        if attempt + 1 >= attempts or remaining <= 0:
            break
        time.sleep(min(delay, remaining))
    message = "PUBLIC_AUCTION_RELEASE_FAILED: " + str(last_error)
    summary(message)
    raise ReleaseError(message) from last_error


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("package")
    pack.add_argument("--source", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    pack.add_argument("--source-sha", required=True)
    for name in ("verify", "promote", "check-source", "verify-public"):
        command = commands.add_parser(name)
        command.add_argument("--bundle", type=Path, required=True)
        if name in ("promote", "check-source"):
            command.add_argument("--root", type=Path, required=True)
        if name == "verify-public":
            command.add_argument("--url", required=True)
            command.add_argument("--attempts", type=int, default=36)
            command.add_argument("--delay", type=float, default=10)
            command.add_argument("--timeout", type=float, default=15)
            command.add_argument("--max-seconds", type=float, default=600)
    public = commands.add_parser("check-public")
    public.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            package(args.source, args.output, args.source_sha)
        elif args.command == "verify":
            verify_bundle(args.bundle)
        elif args.command == "promote":
            promote(args.bundle, args.root)
        elif args.command == "check-source":
            check_source(verify_bundle(args.bundle), args.root)
        elif args.command == "check-public":
            check_public(args.root)
        else:
            verify_public(args.bundle, args.url, args.attempts, args.delay, args.timeout, args.max_seconds)
    except (ReleaseError, OSError) as error:
        print("AUCTION_RELEASE_ERROR: " + str(error), file=sys.stderr)
        return 1
    print("AUCTION_RELEASE_OK " + args.command, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
