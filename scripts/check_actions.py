"""Run real Actions semantic validation without executing workflows."""
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
binary = shutil.which("actionlint")
if not binary:
    raise SystemExit("actionlint is required: install with scripts/install_actionlint.sh and add its directory to PATH")
files = sorted((root / ".github/workflows").glob("*.yml"))
if not files:
    raise SystemExit("No workflows found; refusing a zero-target validation")
subprocess.run([binary, "-version"], check=True)
print(f"Validating {len(files)} workflows (shellcheck is a separate, unrun check)", flush=True)
raise SystemExit(subprocess.run([binary, "-shellcheck=", *map(str, files)], cwd=root).returncode)
