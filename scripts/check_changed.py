"""Read-only, change-scoped checks. No collectors, publishers or deployments.

Checks execute in a disposable source copy so legacy result writers cannot
overwrite tracked evidence. An incomplete browser check is never a green check.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import functools
import hashlib
from html.parser import HTMLParser
import http.server
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TOOLING = ("AGENTS.md", ".agents/", ".github/", "package", "requirements-dev", "scripts/check_changed.py",
           "scripts/prepare_release.py", "scripts/audit_workflows.py", "scripts/check_actions.py", "scripts/install_actionlint.sh", "tests/test_development", "tests/test_workflow_inventory.py")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def source_files(root):
    paths = git(root, "ls-files", "-c", "--others", "--exclude-standard", "-z").decode().split("\0")
    return sorted({p for p in paths if p and (root / p).is_file()})


def source_digest(root):
    digest = hashlib.sha256()
    for name in source_files(root):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Unsupported source symlink: {name}")
        digest.update(name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def changed_files(root, base, head, working_tree=False):
    # Triple-dot means the PR's changes, excluding concurrent main data updates.
    names = git(root, "diff", "--name-only", "-z", f"{base}...{head}").decode().split("\0")
    if working_tree:
        names += git(root, "diff", "--name-only", "-z", "HEAD").decode().split("\0")
        names += git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    return sorted({name for name in names if name})


def plan_checks(paths):
    groups = set()
    unknown_ui = []
    for path in paths:
        if path.startswith(TOOLING) or path.startswith("scripts/test_radar_development_browser.py"):
            groups.update(("tooling", "radar", "publishers", "fridge", "auction", "toss"))
        elif path.startswith(("stock", "assets/stock", "scripts/stock", "scripts/test_stock", "scripts/publish_stock", "scripts/install_stock", "scripts/audit_stock")):
            groups.add("radar")
        elif path.startswith(("use-me-first", "tests/fridge", "scripts/test_fridge_development_browser.py", "supabase/")):
            groups.add("fridge")
        elif "auction-study" in path or "auction_study" in path:
            groups.add("auction")
        elif path.startswith("services/toss-live/"):
            groups.add("toss")
        elif path.startswith("scripts/") and path.endswith((".py", ".cjs", ".js")):
            groups.add("publishers")
        elif path.endswith((".html", ".js", ".css", ".ts", ".tsx", ".jsx")):
            unknown_ui.append(path)
    return {"groups": sorted(groups), "unknown_ui": unknown_ui,
            "browser_required": sorted(groups & {"radar", "fridge", "auction"})}


class LocalReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.inline_scripts = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "img", "source", "iframe") and attrs.get("src"):
            self.references.append(attrs["src"])
        if tag == "link" and attrs.get("href") and "stylesheet" in attrs.get("rel", "").split():
            self.references.append(attrs["href"])
        if tag == "script" and not attrs.get("src") and attrs.get("type", "") in ("", "text/javascript", "module", "application/javascript"):
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.inline_scripts.append("".join(self.script))
            self.script = None


def local_reference(root, html, value):
    url = urlsplit(value)
    if url.scheme or url.netloc or not url.path:
        return None
    decoded = unquote(url.path)
    # Site-root links are relative to the checkout when locally served.
    target = (root / decoded.lstrip("/")) if decoded.startswith("/") else (root / html).parent / decoded
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Local reference escapes checkout: {html}: {value}")
    return target.resolve()


def static_checks(root, paths):
    errors = []
    checked = 0
    changed = set(paths)
    # Reverse dependencies: deleting/changing an asset checks its HTML consumers too.
    html_files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.html"))
    consumers = set()
    for html in html_files:
        parser = LocalReferences()
        parser.feed((root / html).read_text(encoding="utf-8"))
        for ref in parser.references:
            try:
                target = local_reference(root, html, ref)
                if target and target.relative_to(root).as_posix() in changed:
                    consumers.add(html)
            except ValueError:
                if html in changed:
                    consumers.add(html)
    for name in sorted(changed | consumers):
        path = root / name
        if not path.is_file():
            continue
        suffix = path.suffix
        try:
            if suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=name)
            elif suffix in (".js", ".cjs", ".mjs"):
                result = subprocess.run(["node", "--input-type=module" if suffix != ".cjs" else "--input-type=commonjs", "--check"], input=path.read_text(), text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
            elif suffix == ".sh":
                result = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
            elif suffix in (".json", ".jsonl"):
                texts = path.read_text().splitlines() if suffix == ".jsonl" else [path.read_text()]
                for line in texts:
                    if line.strip():
                        json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            elif suffix in (".yml", ".yaml"):
                import yaml
                yaml.safe_load(path.read_text())
            elif suffix == ".html":
                parser = LocalReferences()
                parser.feed(path.read_text())
                for ref in parser.references:
                    target = local_reference(root, name, ref)
                    if target and not target.is_file():
                        raise ValueError(f"Missing local dependency: {ref}")
                for inline in parser.inline_scripts:
                    result = subprocess.run(["node", "--input-type=module", "--check"], input=inline, text=True, capture_output=True)
                    if result.returncode:
                        raise ValueError(result.stderr.strip())
            else:
                continue
            checked += 1
        except Exception as error:
            errors.append(f"{name}: {error}")
    return {"name": "changed-file-syntax-and-local-dependencies", "status": "failed" if errors else "passed",
            "checked_files": checked, "errors": errors}


def commands_for(groups):
    py = sys.executable
    commands = []
    if "tooling" in groups:
        commands += [("actions-semantics", [py, "-B", "scripts/check_actions.py"]), ("development-safety", [py, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_development*.py", "-v"]),
                     ("workflow-inventory", [py, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_workflow_inventory.py", "-v"])]
    if "publishers" in groups:
        commands += [("publisher-races-and-data-failure", [py, "-B", "-m", "unittest", "scripts.test_widget_data_repairs", "scripts.test_market_repairs", "-v"])]
    if "radar" in groups:
        commands += [("radar-publisher-ui-protection", [py, "-B", "scripts/test_stock_radar_publish_protection.py"]),
                     ("radar-financial-regressions", [py, "-B", "-m", "unittest", "scripts.test_stock_decisions", "scripts.test_market_context", "scripts.test_stock_event_outlook", "scripts.test_stock_forecasts", "scripts.test_stock_forecast_directions", "scripts.test_stock_autopilot", "-v"]),
                     ("radar-entry-ui", ["node", "tests/stock-entry-ui.test.cjs"])]
    if "fridge" in groups:
        commands += [(name.removesuffix(".test.cjs"), ["node", "tests/" + name]) for name in ("fridge-domain.test.cjs", "fridge-store.test.cjs", "fridge-kitchen-state.test.cjs", "fridge-ui.test.cjs")]
    if "auction" in groups:
        commands += [("auction-financial-model", ["node", "tests/auction-study-model.test.cjs"])]
    if "toss" in groups:
        commands += [("toss-offline-adapter", [py, "-B", "-m", "unittest", "discover", "-s", "services/toss-live", "-p", "test_*.py", "-v"])]
    return commands


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run_checks(root, args):
    artifacts = Path(args.artifacts).resolve()
    if artifacts.is_relative_to(root.resolve()) and not artifacts.is_relative_to(root.resolve() / ".dev-artifacts"):
        raise ValueError("Artifacts must be outside the checkout or inside ignored .dev-artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)
    actual_head = git(root, "rev-parse", "HEAD").decode().strip()
    requested_head = git(root, "rev-parse", "--verify", f"{args.head}^{{commit}}").decode().strip()
    if actual_head != requested_head:
        raise ValueError("--head must identify the current checkout; do not validate a different commit against these files")
    if not args.working_tree and git(root, "status", "--porcelain").strip():
        raise ValueError("Source has working changes; use --working-tree or commit them before validating")
    paths = changed_files(root, args.base, args.head, args.working_tree)
    plan = plan_checks(paths)
    if args.profile:
        extra = plan_checks(["AGENTS.md"])["groups"] if "tooling" in args.profile else args.profile
        plan["groups"] = sorted(set(plan["groups"]) | set(extra))
        plan["browser_required"] = sorted(set(plan["groups"]) & {"radar", "fridge", "auction"})
    report = {"schema_version": 1, "started_at": datetime.now(timezone.utc).isoformat(), "head_sha": git(root, "rev-parse", "HEAD").decode().strip(),
              "base": args.base, "changed_files": paths, "plan": plan, "source_digest": source_digest(root), "checks": [], "unverified": []}
    if args.plan_only:
        print(json.dumps({"mode": "plan-only-not-validation", **plan, "changed_files": paths}, ensure_ascii=False, indent=2))
        return 0
    with tempfile.TemporaryDirectory(prefix="widget-check-source-") as directory:
        snapshot = Path(directory)
        for name in source_files(root):
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        report["checks"].append(static_checks(snapshot, paths))
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2",
               "PYTHONPATH": os.pathsep.join([str(snapshot), str(snapshot / "scripts"), os.environ.get("PYTHONPATH", "")]),
               "NODE_PATH": os.pathsep.join([str(root / "node_modules"), os.environ.get("NODE_PATH", "")])}

        def run(name, command, extra_env=None):
            log = artifacts / (name + ".log")
            with log.open("w") as stream:
                try:
                    result = subprocess.run(command, cwd=snapshot, env={**env, **(extra_env or {})}, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
                    code = result.returncode
                except (OSError, subprocess.TimeoutExpired) as error:
                    stream.write(str(error) + "\n")
                    code = 124
            entry = {"name": name, "command": command, "status": "passed" if code == 0 else "failed", "returncode": code, "log": str(log)}
            # A zero-test discovery is not an executed suite.
            output = log.read_text(errors="replace")
            if re.search(r"Ran 0 tests|(?:ℹ |# )?tests 0\b", output):
                entry.update(status="failed", reason="zero_tests")
            report["checks"].append(entry)
            print(f"{entry['status'].upper()}: {name}; {log}", flush=True)

        for name, command in commands_for(plan["groups"]):
            run(name, command)
        if plan["browser_required"] and not args.browser:
            report["unverified"].append("Required browser checks were not requested; run with --browser")
        elif plan["browser_required"]:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(snapshot)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}/"
            try:
                for group in plan["browser_required"]:
                    if group == "auction":
                        run("auction-browser", [sys.executable, "-B", "scripts/test_auction_study_browser.py"], {"AUCTION_STUDY_URL": base_url + "auction-study.html", "BROWSER_EXECUTABLE": args.executable or ""})
                    else:
                        if group == "radar":
                            legacy_env = {"RADAR_BASE_URL": base_url, "BROWSER_EXECUTABLE": args.executable or "", "RADAR_ARTIFACTS": str(artifacts / "radar-existing-flow")}
                            run("radar-existing-canonical", [sys.executable, "-B", "scripts/test_stock_radar_canonical_browser.py"], legacy_env)
                            run("radar-existing-flow", [sys.executable, "-B", "scripts/test_stock_radar_flow_browser.py"], legacy_env)
                        command = [sys.executable, "-B", f"scripts/test_{group}_development_browser.py", "--base-url", base_url, "--artifacts", str(artifacts / (group + "-browser"))]
                        if args.executable:
                            command += ["--executable", args.executable]
                        run(group + "-browser", command)
            finally:
                server.shutdown()
                server.server_close()
    if plan["unknown_ui"]:
        report["unverified"].append("No functional/browser profile for: " + ", ".join(plan["unknown_ui"]))
    if source_digest(root) != report["source_digest"]:
        report["unverified"].append("Source changed during validation; rerun on the final source")
    report["status"] = "failed" if any(c["status"] == "failed" for c in report["checks"]) else "incomplete" if report["unverified"] else "passed"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (artifacts / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"RESULT: {report['status']}; {artifacts / 'report.json'}", flush=True)
    return 0 if report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--executable", help="Optional system Chromium; omitted uses pinned Playwright browser")
    parser.add_argument("--artifacts", default="/tmp/widget-checks")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--profile", action="append", choices=["tooling", "radar", "publishers", "fridge", "auction", "toss"], help="Also run an explicit profile; tooling runs all supported profiles")
    args = parser.parse_args()
    try:
        return run_checks(ROOT, args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"CHECK INFRASTRUCTURE FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
