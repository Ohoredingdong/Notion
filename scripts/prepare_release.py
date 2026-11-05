#!/usr/bin/env python3
"""Prepare a reviewed site candidate; this command cannot publish or deploy it.

The input is a successful --all dev_check receipt for the exact clean checkout.
Every tracked file is rehashed and the current full check plan is recalculated.
The resulting archive is an inspection artifact, not approval to deploy, and is
not a replacement for the repository's existing Pages/data publishing policy.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urljoin, urlsplit
import zipfile


SCHEMA_VERSION = 1
ARCHIVE_NAME = "site-candidate.zip"
MANIFEST_NAME = "release-manifest.json"
EXCLUDED_DIRECTORIES = frozenset({"scripts", "tests", "services", "supabase", "config"})
SITE_SUFFIXES = frozenset({
    ".html", ".htm", ".js", ".mjs", ".css", ".json", ".jsonl", ".txt",
    ".xml", ".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ".avif", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".map",
    ".webmanifest", ".mp3", ".mp4", ".ogg", ".wav", ".pdf", ".csv", ".wasm",
})
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
MINIMUM_CHECK_IDS = frozenset({"repository-policy", "workflow-lint", "python-unit", "service-unit",
                               "node-unit", "radar-js-unit", "radar-browser", "radar-flow-browser",
                               "radar-entry-browser", "radar-advanced-browser", "syntax", "data-integrity"})
CSS_URL = re.compile(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*))\s*\)", re.I)
CSS_IMPORT = re.compile(r"@import\s+(?:\"([^\"]*)\"|'([^']*)')", re.I)


class ReleaseRejected(ValueError):
    """The candidate is not eligible for preparation or fails integrity checks."""


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def exact_sha(value: str) -> str:
    if not isinstance(value, str) or not SHA_PATTERN.fullmatch(value):
        raise ReleaseRejected("Use an exact lowercase 40-character commit SHA.")
    return value


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(char) < 32 for char in value) or re.match(r"^[A-Za-z]:", value)):
        raise ReleaseRejected("Invalid relative path in the release input.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ReleaseRejected("Absolute paths and path traversal are not allowed.")
    if str(path) != value:
        raise ReleaseRejected("Release paths must be normalized POSIX paths.")
    return value


def git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ReleaseRejected("Unable to inspect the selected Git checkout.") from error


def checkout_root(value: Path) -> Path:
    root = value.resolve(strict=True)
    actual = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if root != actual:
        raise ReleaseRejected("--root must be the root of the selected checkout.")
    return root


def require_clean(root: Path, sha: str) -> None:
    if git(root, "rev-parse", "HEAD").decode().strip() != sha:
        raise ReleaseRejected("The checked out commit differs from the requested SHA.")
    if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseRejected("The checkout is dirty; commit and rerun every required check.")


def tracked_snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in git(root, "ls-files", "--stage", "-z").split(b"\x00"):
        if not row:
            continue
        metadata, raw_name = row.split(b"\t", 1)
        mode, _, stage = metadata.split()
        if mode not in (b"100644", b"100755") or stage != b"0":
            raise ReleaseRejected("Symlinks, submodules and unresolved index entries are not allowed.")
        name = relative_path(os.fsdecode(raw_name))
        path = root / name
        ancestor = path
        while ancestor != root:
            if ancestor.is_symlink():
                raise ReleaseRejected("Symlinked release inputs are not allowed.")
            ancestor = ancestor.parent
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ReleaseRejected("A tracked input is missing or outside the checkout.")
        result[name] = digest(path.read_bytes())
    if not result:
        raise ReleaseRejected("The checkout has no tracked files.")
    return result


def current_check_ids(root: Path, output: Path) -> list[str]:
    """Ask the same runner for its current complete plan; do not trust a receipt alone."""
    path = root / "scripts" / "dev_check.py"
    if not path.is_file() or path.is_symlink():
        raise ReleaseRejected("The full development check planner is missing.")
    spec = importlib.util.spec_from_file_location("release_dev_check", path)
    if spec is None or spec.loader is None:
        raise ReleaseRejected("The full development check planner cannot be loaded.")
    module = importlib.util.module_from_spec(spec)
    # dataclasses and other module helpers expect the module to be registered.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        plan = module.build_plan(root, all_checks=True, output=output)
        ids = [check["id"] for check in plan["checks"]]
        if "expected_check_ids" in plan and plan["expected_check_ids"] != ids:
            raise ReleaseRejected("The current full check plan is inconsistent.")
        ids = validate_ids(ids)
        if not MINIMUM_CHECK_IDS.issubset(ids):
            raise ReleaseRejected("The current complete check plan omits a required validation scope.")
        return ids
    except ReleaseRejected:
        raise
    except Exception as error:
        raise ReleaseRejected("Unable to calculate the current full development check plan.") from error
    finally:
        sys.modules.pop(spec.name, None)


def validate_ids(value: object) -> list[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(item, str) or not item for item in value)
            or len(value) != len(set(value))):
        raise ReleaseRejected("The full check plan must contain nonempty unique check IDs.")
    return value


def validate_receipt(report: object, sha: str, snapshot: dict[str, str],
                     required_ids: list[str]) -> None:
    if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
            or report.get("schema_version") != SCHEMA_VERSION):
        raise ReleaseRejected("Unknown development check receipt format.")
    if report.get("head_sha") != sha:
        raise ReleaseRejected("Checks were recorded for a different commit.")
    if report.get("mode") != "all" or report.get("status") != "passed":
        raise ReleaseRejected("A successful --all check run is required.")
    if report.get("working_tree_clean") is not True:
        raise ReleaseRejected("The check run did not finish with a clean checkout.")
    if validate_ids(report.get("expected_check_ids")) != required_ids:
        raise ReleaseRejected("The recorded plan differs from the current complete check plan.")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks or any(not isinstance(c, dict) for c in checks):
        raise ReleaseRejected("No completed checks were recorded.")
    if validate_ids([c.get("id") for c in checks]) != required_ids:
        raise ReleaseRejected("A required check is missing, duplicated or out of plan.")
    for check in checks:
        if check.get("status") != "passed" or type(check.get("returncode")) is not int or check["returncode"] != 0:
            raise ReleaseRejected("A required check failed, was skipped or did not execute.")
        try:
            started = datetime.fromisoformat(check["started_at"].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(check["ended_at"].replace("Z", "+00:00"))
            valid_times = started.tzinfo is not None and ended.tzinfo is not None and ended >= started
        except (KeyError, TypeError, ValueError, AttributeError):
            valid_times = False
        if not valid_times:
            raise ReleaseRejected("A check has no completed execution timestamps.")
    saved = report.get("snapshot")
    if not isinstance(saved, dict) or saved != snapshot:
        raise ReleaseRejected("Tracked input content changed after the check run.")
    for name, value in saved.items():
        relative_path(name)
        if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
            raise ReleaseRejected("The check receipt has an invalid tracked-file digest.")


def servable(name: str) -> bool:
    parts = PurePosixPath(relative_path(name)).parts
    if len(parts) == 1 and name in ("CNAME", ".nojekyll"):
        return True
    if any(part.startswith(".") for part in parts) or parts[0] in EXCLUDED_DIRECTORIES:
        return False
    return PurePosixPath(name).suffix.lower() in SITE_SUFFIXES


def source_set(value: str) -> list[str]:
    """Read URL candidates while preserving commas inside a data URL."""
    urls, position = [], 0
    while position < len(value):
        while position < len(value) and (value[position].isspace() or value[position] == ","):
            position += 1
        start = position
        data = value[start:start + 5].lower() == "data:"
        while position < len(value) and not value[position].isspace() and (data or value[position] != ","):
            position += 1
        url = value[start:position]
        if url:
            urls.append(url.rstrip(",") if data else url)
        if position < len(value) and value[position] == ",":
            position += 1
            continue
        if data and url.endswith(","):
            continue
        while position < len(value) and value[position] != ",":
            position += 1
    return urls


def css_references(value: str) -> list[str]:
    return [next(part for part in match if part) for match in CSS_URL.findall(value)
            if any(match)] + [next(part for part in match if part) for match in CSS_IMPORT.findall(value)
                              if any(match)]


class RuntimeReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.base_href = ""
        self.styles = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "base" and not self.base_href:
            self.base_href = attrs.get("href") or ""
        keys = {
            "script": ("src",), "img": ("src",), "source": ("src",),
            "iframe": ("src",), "video": ("src", "poster"), "audio": ("src",),
            "embed": ("src",), "object": ("data",), "image": ("href", "xlink:href"),
            "use": ("href", "xlink:href"),
        }.get(tag, ())
        if tag == "link" and set((attrs.get("rel") or "").lower().split()) & {
                "stylesheet", "preload", "modulepreload", "icon", "manifest"}:
            keys = ("href",)
        if tag == "input" and (attrs.get("type") or "").lower() == "image":
            keys = ("src",)
        self.references.extend(attrs[key] for key in keys if attrs.get(key))
        if tag in ("img", "source") and attrs.get("srcset"):
            self.references.extend(source_set(attrs["srcset"]))
        if attrs.get("style"):
            self.references.extend(css_references(attrs["style"]))
        if tag == "style":
            self.styles = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.styles = False

    def handle_data(self, value):
        if self.styles:
            self.references.extend(css_references(value))


def site_base_path(value: str) -> str:
    if (not isinstance(value, str) or not value.startswith("/") or not value.endswith("/")
            or "?" in value or "#" in value or "\\" in value):
        raise ReleaseRejected("The site base path must be an absolute URL directory such as /Notion/.")
    if value != "/":
        relative_path(value[1:-1])
    return value


def template_contract(value: object) -> dict:
    if not isinstance(value, dict):
        raise ReleaseRejected("The HTML template context contract must be an object.")
    for name, context in value.items():
        relative_path(name)
        if not isinstance(context, dict):
            raise ReleaseRejected("An HTML template context is invalid.")
        target = relative_path(context.get("render_at"))
        generator = relative_path(context.get("generator"))
        if (PurePosixPath(name).suffix.lower() not in (".html", ".htm")
                or PurePosixPath(target).suffix.lower() not in (".html", ".htm")
                or not generator.startswith("scripts/") or not generator.endswith(".py")
                or not isinstance(context.get("reason"), str) or not context["reason"].strip()
                or name == target or target in value):
            raise ReleaseRejected("An HTML template context is missing a valid installation target or reason.")
    return value


def load_site_sources(root: Path, snapshot: dict[str, str]) -> dict:
    name = "config/site-sources.json"
    path = root / name
    if not path.exists():
        return {"template_contexts": {}, "preserved_archives": {}}
    if name not in snapshot or path.is_symlink():
        raise ReleaseRejected("The site source contract must be part of the tested tracked inputs.")
    try:
        document = json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        raise ReleaseRejected("Unable to read the site source contract.") from error
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int
            or document.get("schema_version") != SCHEMA_VERSION):
        raise ReleaseRejected("Unknown site source contract format.")
    contexts = template_contract(document.get("template_contexts"))
    archives = archive_contract(document.get("preserved_archives", {}))
    if set(contexts) & set(archives):
        raise ReleaseRejected("A source cannot be both an installation template and historical archive.")
    for name, context in contexts.items():
        if any(path not in snapshot for path in (name, context["render_at"], context["generator"])):
            raise ReleaseRejected("The site source contract points to missing or untracked source files.")
        generator = root / context["generator"]
        if not generator.is_file() or generator.is_symlink():
            raise ReleaseRejected("The declared HTML generator is not a regular tracked source file.")
    for name, context in archives.items():
        if name not in snapshot or context["original_context"] not in snapshot:
            raise ReleaseRejected("The archive contract points to missing or untracked source files.")
    if any(info["render_at"] in archives for info in contexts.values()):
        raise ReleaseRejected("An HTML template must install at a real entry, not an archive.")
    if any(info["original_context"] in contexts or info["original_context"] in archives
           for info in archives.values()):
        raise ReleaseRejected("A source archive must declare an original entry context.")
    return {"template_contexts": contexts, "preserved_archives": archives}


def archive_contract(value: object) -> dict:
    if not isinstance(value, dict):
        raise ReleaseRejected("The preserved archive contract must be an object.")
    for name, context in value.items():
        relative_path(name)
        if not isinstance(context, dict):
            raise ReleaseRejected("A preserved archive context is invalid.")
        target = relative_path(context.get("original_context"))
        if (PurePosixPath(name).suffix.lower() not in (".html", ".htm")
                or PurePosixPath(target).suffix.lower() not in (".html", ".htm")
                or not isinstance(context.get("reason"), str) or not context["reason"].strip()
                or name == target or target in value):
            raise ReleaseRejected("A preserved archive is missing its original context or reason.")
    return value


def dependency_closure(files: dict[str, bytes], base_path: str,
                       template_contexts: dict | None = None,
                       preserved_archives: dict | None = None) -> dict:
    """Verify packaged static resources, without pretending to parse dynamic JS."""
    base_path = site_base_path(base_path)
    contexts = template_contract(template_contexts or {})
    archives = archive_contract(preserved_archives or {})
    if set(contexts) & set(archives):
        raise ReleaseRejected("A source has conflicting template/archive contexts.")
    for name, context in contexts.items():
        if name not in files or context["render_at"] not in files:
            raise ReleaseRejected("An HTML template or its installation target is not packaged.")
    for name, context in archives.items():
        if name not in files or context["original_context"] not in files:
            raise ReleaseRejected("A preserved archive or its original context is not packaged.")
    origin = "https://release-candidate.invalid"
    external, local = set(), set()
    for name, body in files.items():
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in (".html", ".htm", ".svg", ".css"):
            continue
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReleaseRejected("A static resource cannot be checked as UTF-8: " + name) from error
        if suffix == ".css":
            references, base_href = css_references(text), ""
        else:
            parser = RuntimeReferences()
            parser.feed(text)
            references, base_href = parser.references, parser.base_href
        installed_at = contexts.get(name, {}).get(
            "render_at", archives.get(name, {}).get("original_context", name))
        owner_url = origin + base_path + quote(installed_at, safe="/")
        reference_base = urljoin(owner_url, base_href) if base_href else owner_url
        for reference in references:
            if not reference.strip() or reference.strip().startswith("#"):
                continue
            resolved = urlsplit(urljoin(reference_base, reference.strip()))
            if resolved.scheme in ("data", "blob", "about"):
                continue
            if resolved.scheme not in ("http", "https"):
                raise ReleaseRejected("Unsupported runtime resource URL in " + name)
            if resolved.netloc != "release-candidate.invalid":
                # Public origins/paths only; query tokens are never copied into the receipt.
                external.add(resolved.scheme + "://" + resolved.netloc + resolved.path)
                continue
            path = unquote(resolved.path)
            if not path.startswith(base_path):
                raise ReleaseRejected("A runtime resource escapes the site base path: " + name)
            target = path[len(base_path):]
            if path.endswith("/"):
                target += "index.html"
            target = relative_path(target)
            if target not in files:
                raise ReleaseRejected("A runtime resource is not tracked and packaged: " + name + " -> " + target)
            if target in contexts or target in archives:
                raise ReleaseRejected("A source template/archive is referenced as a standalone runtime page: " + target)
            local.add(target)
    return {
        "site_base_path": base_path,
        "static_local_resource_count": len(local),
        "external_resources_unverified": sorted(external),
        "template_contexts": contexts,
        "preserved_archives": archives,
        "scope": "Packaged HTML/SVG resource attributes and CSS url/import references. Declared generation templates and historical source archives use their original or installation context, not their source URL. Dynamic JavaScript dependencies and external CDN contents require separate browser checks.",
    }


def external_path(root: Path, value: Path) -> Path:
    if any(part.is_symlink() for part in (value.absolute(), *value.absolute().parents)):
        raise ReleaseRejected("Symlinked external paths are not allowed.")
    path = value.resolve()
    if path == root or path.is_relative_to(root):
        raise ReleaseRejected("Reports and release artifacts must be outside the checkout.")
    return path


def verify_candidate(directory: Path, expected_sha: str,
                     expected_manifest_sha256: str | None = None) -> dict:
    """Check a prepared archive before a separately authorized publication step.

    A caller must pin the trusted manifest hash when moving artifacts between
    systems. This is a content integrity check, not proof of CI provenance or
    human approval. No deployment operation is implemented by this module.
    """
    expected_sha = exact_sha(expected_sha)
    archive = directory / ARCHIVE_NAME
    manifest_path = directory / MANIFEST_NAME
    if directory.is_symlink() or archive.is_symlink() or manifest_path.is_symlink():
        raise ReleaseRejected("A candidate contains a symlink.")
    try:
        manifest_bytes = manifest_path.read_bytes()
        if expected_manifest_sha256 is not None and digest(manifest_bytes) != expected_manifest_sha256:
            raise ReleaseRejected("The candidate manifest differs from the trusted digest.")
        manifest = json.loads(manifest_bytes)
        if not isinstance(manifest, dict):
            raise ReleaseRejected("The candidate manifest must be an object.")
        if (type(manifest.get("schema_version")) is not int
                or manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("source_sha") != expected_sha):
            raise ReleaseRejected("The candidate is for a different commit or format.")
        if manifest.get("deployment_authorized") is not False:
            raise ReleaseRejected("This candidate must not claim deployment approval.")
        if manifest.get("archive") != ARCHIVE_NAME or digest(archive.read_bytes()) != manifest.get("archive_sha256"):
            raise ReleaseRejected("The prepared archive was changed.")
        if not MINIMUM_CHECK_IDS.issubset(validate_ids(manifest.get("checked_ids"))):
            raise ReleaseRejected("The candidate omits a required check scope.")
        if not isinstance(manifest.get("check_report_sha256"), str) or not HASH_PATTERN.fullmatch(manifest["check_report_sha256"]):
            raise ReleaseRejected("The candidate check receipt digest is invalid.")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ReleaseRejected("The candidate has no site files.")
        with zipfile.ZipFile(archive) as zipped:
            content = {}
            entries = zipped.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or set(names) != set(files):
                raise ReleaseRejected("Archive entries differ from the candidate manifest.")
            for entry in entries:
                name = relative_path(entry.filename)
                if not servable(name) or stat.S_ISLNK(entry.external_attr >> 16):
                    raise ReleaseRejected("The archive contains a disallowed file or symlink.")
                body = zipped.read(entry)
                info = files[name]
                if (not isinstance(info, dict) or type(info.get("bytes")) is not int
                        or digest(body) != info.get("sha256") or len(body) != info.get("bytes")):
                    raise ReleaseRejected("A candidate file differs from the tested file manifest.")
                content[name] = body
        dependencies = manifest.get("static_dependencies")
        if not isinstance(dependencies, dict):
            raise ReleaseRejected("The static resource closure receipt is missing.")
        if dependency_closure(content, dependencies.get("site_base_path"),
                              dependencies.get("template_contexts"),
                              dependencies.get("preserved_archives")) != dependencies:
            raise ReleaseRejected("The static resource closure receipt differs from the archive.")
        return manifest
    except ReleaseRejected:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise ReleaseRejected("The prepared candidate is missing or corrupt.") from error


def prepare_candidate(root: Path, sha: str, report_path: Path, output: Path,
                      base_path: str = "/Notion/") -> dict:
    root = checkout_root(root)
    sha = exact_sha(sha)
    output = external_path(root, output)
    report_path = external_path(root, report_path)
    if output.exists():
        raise ReleaseRejected("Use a new output directory; existing artifacts are never overwritten.")
    if not report_path.is_file():
        raise ReleaseRejected("The completed development check receipt is missing.")
    require_clean(root, sha)
    snapshot = tracked_snapshot(root)
    try:
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes)
    except (OSError, ValueError) as error:
        raise ReleaseRejected("Unable to read the completed development check receipt.") from error
    required_ids = validate_ids(current_check_ids(root, output))
    validate_receipt(report, sha, snapshot, required_ids)
    selected = [name for name in sorted(snapshot) if servable(name)]
    if not any(PurePosixPath(name).suffix.lower() in (".html", ".htm") for name in selected):
        raise ReleaseRejected("The tested checkout has no site HTML to prepare.")
    content = {name: (root / name).read_bytes() for name in selected}
    dependencies = dependency_closure(content, base_path, **load_site_sources(root, snapshot))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="notion-release-", dir=output.parent) as folder:
        stage = Path(folder) / "candidate"
        stage.mkdir()
        files = {}
        with zipfile.ZipFile(stage / ARCHIVE_NAME, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for name in selected:
                path = root / name
                if path.is_symlink():
                    raise ReleaseRejected("A site input was replaced with a symlink.")
                body = path.read_bytes()
                if digest(body) != snapshot[name]:
                    raise ReleaseRejected("A site input changed while preparing the candidate.")
                # Fixed timestamps make the archive reproducible for the same tested bytes.
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                zipped.writestr(entry, body)
                files[name] = {"sha256": snapshot[name], "bytes": len(body)}
        require_clean(root, sha)
        if tracked_snapshot(root) != snapshot:
            raise ReleaseRejected("Tracked content changed while preparing the candidate.")
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "source_sha": sha,
            "check_report_sha256": digest(report_bytes),
            "checked_ids": required_ids,
            "archive": ARCHIVE_NAME,
            "archive_sha256": digest((stage / ARCHIVE_NAME).read_bytes()),
            "files": files,
            "excluded_tracked_paths": sorted(set(snapshot) - set(selected)),
            "static_dependencies": dependencies,
            "deployment_authorized": False,
            "scope": "Inspection candidate only. Human approval, protected deployment and CI provenance are separate requirements.",
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
        (stage / MANIFEST_NAME).write_bytes(manifest_bytes)
        verify_candidate(stage, sha, digest(manifest_bytes))
        # A preexisting directory is never merged with a new candidate.
        if output.exists():
            raise ReleaseRejected("The output directory was created by another process.")
        stage.rename(output)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sha", required=True, help="Exact tested 40-character commit SHA")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-base-path", default="/Notion/",
                        help="Publication URL directory; defaults to this repository's /Notion/ Pages path")
    args = parser.parse_args()
    try:
        manifest = prepare_candidate(args.root, args.sha, args.report, args.output, args.site_base_path)
    except (ReleaseRejected, OSError) as error:
        print("RELEASE_CANDIDATE_REJECTED: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps({"source_sha": manifest["source_sha"], "output": str(args.output),
                      "files": len(manifest["files"]), "deployment_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
