#!/usr/bin/env python3
"""Plan and run change-related checks without running data publishers.

Only the Python standard library is required to plan. Execution uses the tools
declared by the selected checks (for example Node, Playwright and PyYAML).
Every check runs in a disposable snapshot; the source checkout is read-only.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html.parser
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import unquote, urlsplit


CONFIG = ".github/validation-routes.json"
CODE_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".html", ".css", ".sh", ".yml", ".yaml", ".toml", ".json", ".jsonl"}
STATIC_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".html", ".json", ".jsonl", ".yml", ".yaml"}


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def safe_path(path: str) -> str:
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or not p.parts or ".git" in p.parts:
        raise ValueError(f"Unsafe repository path: {path!r}")
    return p.as_posix()


def parse_name_status(data: bytes) -> list[dict]:
    """Parse -z output: renamed paths may contain spaces, tabs or newlines."""
    items = data.decode("utf-8", errors="surrogateescape").split("\0")
    changes, index = [], 0
    while index < len(items) and items[index]:
        status = items[index]
        index += 1
        if index >= len(items) or not items[index]:
            raise ValueError("Incomplete git name-status output")
        old = safe_path(items[index])
        index += 1
        new = None
        if status.startswith(("R", "C")):
            if index >= len(items) or not items[index]:
                raise ValueError("Incomplete git rename output")
            new = safe_path(items[index])
            index += 1
        changes.append({"status": status, "path": new or old,
                        **({"old_path": old} if new else {})})
    return changes


def discover_changes(root: Path, base: str, head: str = "HEAD", working_tree: bool = False,
                     files: list[str] | None = None) -> list[dict]:
    if files is not None:
        return [{"status": "M" if (root / safe_path(p)).exists() else "D", "path": safe_path(p)}
                for p in dict.fromkeys(files)]
    changes = parse_name_status(git(root, "diff", "--name-status", "-z", "--find-renames", base, head, "--"))
    if working_tree:
        changes.extend(parse_name_status(git(root, "diff", "--name-status", "-z", "--find-renames", head, "--")))
        changes.extend({"status": "A", "path": safe_path(p)} for p in
                       git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0") if p)
    # Keep both rename endpoints. Later worktree status wins for a duplicate path.
    unique = {}
    for change in changes:
        unique[(change.get("old_path"), change["path"])] = change
    return list(unique.values())


def path_matches(path: str, pattern: str) -> bool:
    """Match root globs only at root; ** may cross directory boundaries."""
    parts, wanted = PurePosixPath(path).parts, PurePosixPath(pattern).parts

    def match(left, right):
        if not right:
            return not left
        if right[0] == "**":
            return match(left, right[1:]) or bool(left) and match(left[1:], right)
        return bool(left) and fnmatch.fnmatchcase(left[0], right[0]) and match(left[1:], right[1:])
    return bool(match(parts, wanted))


def load_config(root: Path, content: bytes | str | None = None) -> dict:
    config = json.loads((root / CONFIG).read_bytes() if content is None else content)
    if config.get("version") != 1 or not isinstance(config.get("checks"), dict):
        raise ValueError("Unsupported validation-routes configuration")
    for route in config["routes"]:
        if not route.get("patterns") or not route.get("checks"):
            raise ValueError("Each route needs patterns and checks")
        for name in route["checks"]:
            if name not in config["checks"]:
                raise ValueError(f"Unknown check {name}")
    for name, check in config["checks"].items():
        argv = check.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError(f"Invalid argv for {name}")
        if argv[0] not in ("{python}", "node"):
            raise ValueError(f"Check {name} must invoke Python or Node directly, without a shell")
        # Production entrypoints must never be used as validation commands.
        for arg in argv[1:]:
            leaf = Path(arg).name
            if leaf.startswith(("publish_", "update-", "update_", "run_stock_", "install_", "refresh_")):
                raise ValueError(f"Check {name} invokes a production writer: {arg}")
    return config


def plan_checks(changes: list[dict], config: dict) -> dict:
    selected, uncovered, exempt, coverage = {}, [], [], {}
    for change in changes:
        paths = [change["path"]] + ([change["old_path"]] if "old_path" in change else [])
        names = []
        for route in config["routes"]:
            if any(path_matches(p, pattern) for p in paths for pattern in route["patterns"]):
                for name in route["checks"]:
                    if name not in names:
                        names.append(name)
                    selected.setdefault(name, {"id": name, "kind": "command", "status": "unrun",
                                               **config["checks"][name], "paths": []})
                    selected[name]["paths"].append(change["path"])
        if change["status"] != "D" and Path(change["path"]).suffix.lower() in STATIC_SUFFIXES:
            name = "static:" + change["path"]
            selected[name] = {"id": name, "kind": "static", "status": "unrun", "paths": [change["path"]]}
        functional = [n for n in names if config["checks"][n].get("functional", True)]
        coverage[change["path"]] = functional
        code = any(Path(p).suffix.lower() in CODE_SUFFIXES for p in paths)
        ignored = all(any(path_matches(p, rule) for rule in config.get("documentation", [])) for p in paths)
        # Documentation may include JSON evidence, but docs globs never waive
        # functional coverage for executable source or operational configuration.
        documentation_only = ignored and not any(Path(p).suffix.lower() in CODE_SUFFIXES - {".json", ".jsonl"} for p in paths)
        if code and not functional and not documentation_only:
            uncovered.append({"path": change["path"], "reason": "No related functional test route; syntax alone is insufficient"})
        elif documentation_only and not names:
            exempt.append({"path": change["path"], "reason": "Documentation; no runtime behavior changed"})
        elif not names and change["status"] == "D" and not ignored:
            uncovered.append({"path": change["path"], "reason": "Deleted file needs related functional coverage"})
        elif not names and not code and Path(change["path"]).suffix.lower() not in {".json", ".jsonl"}:
            # Unknown binary/configuration files need a deliberate validation route too.
            uncovered.append({"path": change["path"], "reason": "No validation route for this file type"})
    return {"changes": changes, "selected": list(selected.values()), "uncovered": uncovered,
            "not_applicable": exempt, "functional_coverage": coverage,
            "limitations": ["JSON/JSONL parsing alone is insufficient; operational data requires an explicit consumer or data-contract check.",
                            "Only explicitly routed radar feeds receive browser coverage; live market accuracy is not verified.",
                            "Passing checks do not deploy or authorize a deployment."]}


class Resources(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.resources, self.scripts, self.active = [], [], None

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag in {"script", "img", "iframe", "source", "audio", "video"} and attr.get("src"):
            self.resources.append((tag, attr["src"]))
        if tag == "link" and "stylesheet" in attr.get("rel", "") and attr.get("href"):
            self.resources.append((tag, attr["href"]))
        if tag == "script" and not attr.get("src") and attr.get("type", "").lower() in {
                "", "text/javascript", "application/javascript", "module"}:
            self.active = {"source": "", "module": attr.get("type") == "module"}

    def handle_data(self, data):
        if self.active is not None:
            self.active["source"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self.active is not None:
            self.scripts.append(self.active)
            self.active = None


def validate_javascript(path: Path, source: str | None = None, module: bool = False) -> None:
    if module or path.suffix == ".mjs":
        argv, body = ["node", "--input-type=module", "--check"], source if source is not None else path.read_text(encoding="utf-8")
    elif source is None:
        argv, body = ["node", "--check", str(path)], None
    else:
        argv, body = ["node", "--check"], source
    result = subprocess.run(argv, input=body, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "JavaScript syntax check failed")


def static_check(root: Path, relative: str) -> str:
    path = root / safe_path(relative)
    if not path.is_file():
        raise ValueError(f"Changed file is missing: {relative}")
    suffix = path.suffix.lower()
    if suffix == ".py":
        compile(path.read_bytes(), relative, "exec")  # No pyc or __pycache__ writes.
    elif suffix in {".js", ".cjs", ".mjs"}:
        validate_javascript(path)
    elif suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(f"Non-finite JSON number: {s}")))
    elif suffix == ".jsonl":
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(f"Non-finite JSON number: {s}")))
                except ValueError as error:
                    raise ValueError(f"{relative}:{number}: {error}") from error
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as error:
            raise ValueError("PyYAML is required to validate workflow YAML; install requirements-dev.txt") from error
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise ValueError(f"Invalid YAML: {error}") from error
    elif suffix == ".html":
        document = Resources()
        document.feed(path.read_text(encoding="utf-8"))
        for tag, value in document.resources:
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path:
                continue
            local = (root / unquote(url.path).lstrip("/")) if url.path.startswith("/") else path.parent / unquote(url.path)
            local = local.resolve()
            if not local.is_relative_to(root.resolve()) or not local.is_file():
                raise ValueError(f"{relative}: missing local {tag} resource {value}")
            if tag == "script":
                # External module scripts are valid even without a package.json.
                validate_javascript(local, module=True)
        for index, script in enumerate(document.scripts, 1):
            try:
                validate_javascript(path, source=script["source"], module=script["module"])
            except ValueError as error:
                raise ValueError(f"{relative}: inline script {index}: {error}") from error
    return f"Validated {relative}"


def snapshot(root: Path, target: Path, head: str, working_tree: bool, explicit_files: list[str] | None) -> None:
    """Copy committed head, optionally overlay worktree files; never copy .git or credentials."""
    archive = git(root, "archive", "--format=tar", head)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    if not working_tree and explicit_files is None:
        return
    tracked = git(root, "ls-files", "-z").decode().split("\0")
    extras = (git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
              if working_tree and explicit_files is None else [])
    overlay = list(dict.fromkeys(tracked + extras + (explicit_files or [])))
    for relative in overlay:
        if not relative:
            continue
        relative = safe_path(relative)
        source, dest = root / relative, target / relative
        if not source.exists():
            if dest.is_file() or dest.is_symlink():
                dest.unlink()
            continue
        if source.is_symlink():
            # Do not copy a symlink which could let a test write outside the snapshot.
            if not source.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"External symlink in worktree: {relative}")
        if source.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_symlink():
                dest.unlink()
            shutil.copy2(source, dest)


def command_check(check: dict, root: Path, artifacts: Path, browser: str | None,
                  dependency_root: Path | None = None) -> dict:
    values = {"python": sys.executable, "root": str(root), "output": str(artifacts),
              "browser": browser or ""}
    def expand(argument):
        for key, value in values.items():
            argument = argument.replace("{" + key + "}", value)
        return argument
    argv = [expand(arg) for arg in check["argv"]]
    if "--browser-executable" in argv and not browser:
        index = argv.index("--browser-executable")
        del argv[index:index + 2]
    environment = os.environ.copy()
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "scripts") + os.pathsep + str(root),
                        "DEV_CHECK_SNAPSHOT": "1"})
    if dependency_root is not None and (dependency_root / "node_modules").is_dir():
        environment["NODE_PATH"] = str(dependency_root / "node_modules") + os.pathsep + environment.get("NODE_PATH", "")
    environment.update(check.get("env", {}))
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=root, env=environment, capture_output=True, text=True,
                                timeout=check.get("timeout", 180))
        output = result.stdout + result.stderr
        code, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as error:
        raw = lambda x: x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
        output, code, timed_out = raw(error.stdout) + raw(error.stderr), None, True
    except OSError as error:
        output, code, timed_out = str(error), None, False
    # A unittest invocation which discovered zero tests must never count as green.
    empty_suite = "unittest" in argv and ("Ran 0 tests" in output or not __import__("re").search(r"Ran [1-9][0-9]* tests?", output))
    passed = code == 0 and not timed_out and not empty_suite
    log = artifacts / (check["id"] + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(output, encoding="utf-8")
    return {"status": "passed" if passed else "failed", "argv": argv, "exit_code": code,
            "timed_out": timed_out, "empty_suite": empty_suite,
            "duration_seconds": round(time.monotonic() - start, 3), "log": str(log), "output_tail": output[-12000:]}


def execute_plan(plan: dict, root: Path, artifacts: Path, browser: str | None,
                 dependency_root: Path | None = None) -> dict:
    for check in plan["selected"]:
        if check["kind"] == "static":
            start = time.monotonic()
            try:
                detail = static_check(root, check["paths"][0])
                check.update(status="passed", detail=detail)
            except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as error:
                check.update(status="failed", detail=str(error))
            check["duration_seconds"] = round(time.monotonic() - start, 3)
        else:
            check.update(command_check(check, root, artifacts, browser, dependency_root))
    return finish_report(plan)


def finish_report(plan: dict) -> dict:
    counts = {status: sum(c["status"] == status for c in plan["selected"]) for status in ["passed", "failed", "unrun"]}
    counts["uncovered"] = len(plan["uncovered"])
    plan["counts"] = counts
    plan["status"] = "failed" if plan.get("infrastructure_error") or any(counts[x] for x in ["failed", "unrun", "uncovered"]) else "passed"
    if not plan["changes"] and not plan.get("infrastructure_error"):
        plan["status"] = "no_changes"
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Exact baseline commit/ref (git diff base head, not merge-base)")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--working-tree", action="store_true", help="Include tracked edits and nonignored untracked files")
    parser.add_argument("--files", nargs="+", help="Explicit paths for a focused local check; do not use to bypass PR diff")
    parser.add_argument("--run", "--check", dest="run", action="store_true")
    parser.add_argument("--output", type=Path, help="Report JSON outside checkout (default: /tmp/notion-dev-check-*/report.json)")
    parser.add_argument("--browser-executable")
    args = parser.parse_args(argv)
    try:
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
        base = git(root, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
        head = git(root, "rev-parse", "--verify", args.head + "^{commit}").decode().strip()
        if args.output and args.output.resolve().is_relative_to(root):
            raise ValueError("--output must be outside the checkout to preserve source files")
        committed_scope = not args.working_tree and args.files is None
        configuration = git(root, "show", head + ":" + CONFIG) if committed_scope else (root / CONFIG).read_bytes()
        config = load_config(root, configuration)
        changes = discover_changes(root, base, head, args.working_tree, args.files)
        plan = {"version": 1, "base": base, "head": head,
                "configuration_sha256": hashlib.sha256(configuration).hexdigest(),
                "configuration_source": "commit:" + head + ":" + CONFIG if committed_scope else "working_tree:" + CONFIG,
                "scope": "explicit_files" if args.files is not None else "working_tree" if args.working_tree else "commit_diff",
                "status": "planned", **plan_checks(changes, config)}
        if not args.run:
            encoded = json.dumps(plan, indent=2, ensure_ascii=False)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(encoded + "\n", encoding="utf-8")
            print(encoded)
            return 0
        artifacts = args.output.resolve().parent if args.output else Path(tempfile.mkdtemp(prefix="notion-dev-check-"))
        artifacts.mkdir(parents=True, exist_ok=True)
        output = args.output.resolve() if args.output else artifacts / "report.json"
        try:
            with tempfile.TemporaryDirectory(prefix="notion-validation-snapshot-") as temp:
                isolated = Path(temp)
                snapshot(root, isolated, head, args.working_tree, args.files)
                execute_plan(plan, isolated, artifacts, args.browser_executable, root)
        except (ValueError, OSError, tarfile.TarError) as error:
            plan["infrastructure_error"] = str(error)
            finish_report(plan)
        output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": plan["status"], "counts": plan["counts"], "report": str(output)}, ensure_ascii=False))
        return 1 if plan["status"] == "failed" else 0
    except (ValueError, OSError, json.JSONDecodeError, tarfile.TarError) as error:
        print(json.dumps({"status": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
