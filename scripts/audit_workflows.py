#!/usr/bin/env python3
"""Inventory local GitHub Actions without calling GitHub or running any job.

The report describes source configuration, not historical job outcomes, effective
repository permissions, branch protection, or the active Pages source setting.
Requires PyYAML (a development dependency).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import shlex

import yaml


class ActionsLoader(yaml.SafeLoader):
    """Keep the Actions `on` key as text instead of YAML 1.1 boolean True."""


ActionsLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in resolvers
          if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
ActionsLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.I), list("tTfF")
)

ENTRYPOINT = re.compile(
    r"(?:^|[\s;&|])(?:python(?:3)?|node|bash)\s+"
    r"(?:(?:-B|--check)\s+)*"
    r"((?:scripts|tests|services|assets)/[\w./-]+\.(?:py|cjs|js|sh))(?=[\s;&|]|$)"
)
MODULE_COMMAND = re.compile(r"\bpython(?:3)?\s+-m\s+unittest\s+([^\n]+)")
TEST_DISCOVERY = re.compile(r"unittest\s+discover\s+-s\s+([\w/-]+)\s+-p\s+['\"]([^'\"]+)['\"]")


def _line(source: str, text: str) -> int | None:
    for number, line in enumerate(source.splitlines(), 1):
        if text in line:
            return number
    return None


def inventory(root: Path) -> dict:
    root = root.resolve()
    files = sorted((root / ".github/workflows").glob("*.yml"))
    files += sorted((root / ".github/workflows").glob("*.yaml"))
    files = sorted(set(files))
    workflows, errors, referenced_tests = [], [], set()
    names, command_owners = defaultdict(list), defaultdict(list)
    tests = sorted(
        p.relative_to(root).as_posix()
        for directory in (root / "scripts", root / "tests", root / "services")
        if directory.exists()
        for p in directory.rglob("*")
        if p.is_file() and (p.name.startswith("test_") and p.suffix in {".py", ".cjs"}
                            or p.name.endswith(".test.cjs") or p.name.endswith("-browser.cjs"))
    )
    for path in files:
        name = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        try:
            data = yaml.load(source, Loader=ActionsLoader)
            if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
                raise ValueError("Workflow must have a jobs mapping")
            triggers = data.get("on")
            if isinstance(triggers, str):
                triggers = {triggers: None}
            if isinstance(triggers, list):
                triggers = {event: None for event in triggers}
            if not isinstance(triggers, dict) or not triggers:
                raise ValueError("Workflow must declare at least one event")
        except (ValueError, yaml.YAMLError) as exc:
            errors.append({"path": name, "error": str(exc)})
            continue
        names[str(data.get("name", name))].append(name)
        jobs = []
        entrypoints, publications, page_builds, ignored_failures = [], [], [], []
        for job_name, job in data["jobs"].items():
            if not isinstance(job, dict):
                errors.append({"path": name, "error": f"Invalid job {job_name}"})
                continue
            steps = job.get("steps", [])
            refs = []
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append({"path": name, "error": f"Invalid step in {job_name}"})
                    continue
                if str(step.get("uses", "")).startswith("actions/checkout@"):
                    refs.append((step.get("with") or {}).get("ref", "event default"))
                run = str(step.get("run", ""))
                label = step.get("name", f"{job_name}:step-{index + 1}")
                if step.get("continue-on-error"):
                    ignored_failures.append({"job": job_name, "step": label,
                                             "condition": step.get("if")})
                for target in ENTRYPOINT.findall(run):
                    entrypoints.append(target)
                    if not (root / target).is_file():
                        errors.append({"path": name, "job": job_name,
                                       "error": f"Missing literal script target: {target}"})
                for module_command in MODULE_COMMAND.findall(run):
                    tokens = shlex.split(module_command)
                    if tokens and tokens[0] == "discover":
                        continue
                    for module in tokens:
                        if not re.fullmatch(r"(?:(?:scripts|tests)\.)?test_[\w.]+", module):
                            continue
                        relative = module.replace(".", "/") + ".py"
                        candidates = [relative] if "." in module else [f"scripts/{relative}", f"tests/{relative}"]
                        target = next((target for target in candidates if (root / target).is_file()), candidates[0])
                        entrypoints.append(target)
                        if not (root / target).is_file():
                            errors.append({"path": name, "job": job_name,
                                           "error": f"Missing unittest module: {target}"})
                for directory, pattern in TEST_DISCOVERY.findall(run):
                    referenced_tests.update(p.relative_to(root).as_posix()
                                            for p in (root / directory).glob(pattern) if p.is_file())
                for command in run.splitlines():
                    compact = " ".join(command.split())
                    if ("scripts/test_" in compact or "tests/" in compact
                            or "-m unittest " in compact) and not any(
                                x in compact for x in ("py_compile", "--check", "git ", "pip ", "npm ")
                            ):
                        command_owners[compact].append({"workflow": name, "job": job_name,
                                                       "step": label})
                publisher_helpers = sorted(set(re.findall(r"scripts/publish_[\w_]+\.py", run)))
                if "git push" in run or publisher_helpers:
                    publications.append({
                        "job": job_name, "step": label, "condition": step.get("if"),
                        "line": _line(source, label) if step.get("name") else _line(source, "git push"),
                        "direct_git_push": "git push" in run,
                        "explicit_main_target": "HEAD:main" in run,
                        "helpers": publisher_helpers,
                        "helper_scope_requires_source_review": bool(publisher_helpers),
                    })
                if "pages/builds" in run or "actions/deploy-pages@" in str(step.get("uses", "")):
                    page_builds.append({"job": job_name, "step": label, "condition": step.get("if"),
                                        "line": _line(source, "pages/builds")})
            jobs.append({"id": job_name, "condition": job.get("if"),
                         "needs": job.get("needs", []), "timeout_minutes": job.get("timeout-minutes"),
                         "permissions": job.get("permissions", data.get("permissions", "repository default")),
                         "checkout_refs": refs})
        for test in tests:
            if test in source or test.removesuffix(".py").replace("/", ".") in source:
                referenced_tests.add(test)
        referenced_tests.update(set(entrypoints) & set(tests))
        workflows.append({
            "path": name, "name": data.get("name", path.stem),
            "events": triggers, "permissions": data.get("permissions", "repository default"),
            "concurrency": data.get("concurrency"), "jobs": jobs,
            "entrypoints": sorted(set(entrypoints)), "publication_steps": publications,
            "pages_build_steps": page_builds, "continue_on_error_steps": ignored_failures,
        })
    duplicate_names = {key: value for key, value in names.items() if len(value) > 1}
    for name, paths in duplicate_names.items():
        errors.append({"error": f"Duplicate workflow name: {name}", "paths": paths})
    duplicate_commands = {command: owners for command, owners in command_owners.items() if len(owners) > 1}
    permission_counts = Counter(str(w["permissions"]) for w in workflows)
    return {
        "schema_version": 1,
        "evidence": "local source only; no remote Actions history or effective policy inspected",
        "workflow_count": len(workflows), "job_count": sum(len(w["jobs"]) for w in workflows),
        "summary": {
            "pull_request_workflows": sum("pull_request" in w["events"] for w in workflows),
            "scheduled_workflows": sum("schedule" in w["events"] for w in workflows),
            "workflows_with_publication_steps": sum(bool(w["publication_steps"]) for w in workflows),
            "explicit_pages_build_workflows": sum(bool(w["pages_build_steps"]) for w in workflows),
            "workflows_with_continue_on_error": sum(bool(w["continue_on_error_steps"]) for w in workflows),
            "permission_declarations": dict(sorted(permission_counts.items())),
        },
        "workflows": workflows,
        "duplicate_test_commands": duplicate_commands,
        "test_files_not_named_in_workflows": sorted(set(tests) - referenced_tests),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="JSON destination; stdout when omitted")
    parser.add_argument("--check", action="store_true", help="Nonzero for malformed YAML or missing literal scripts")
    args = parser.parse_args()
    report = inventory(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Inventoried {report['workflow_count']} workflows, {report['job_count']} jobs; "
              f"{len(report['errors'])} static errors. Report: {args.output}")
    else:
        print(rendered, end="")
    return int(args.check and bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
