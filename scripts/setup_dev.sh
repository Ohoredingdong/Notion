#!/usr/bin/env bash
# Reproducible test tools only; never collects data or changes tracked source.
set -euo pipefail

DEV_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_STATE="${NOTION_DEV_STATE:-${TMPDIR:-/tmp}/notion-dev-${UID}}"
DEV_INSTALL_BROWSER=false
DEV_BROWSER=""
while (($#)); do
  case "$1" in
    --state) DEV_STATE="${2:?--state requires a directory}"; shift 2 ;;
    --install-browser) DEV_INSTALL_BROWSER=true; shift ;;
    --browser-executable) DEV_BROWSER="${2:?--browser-executable requires a path}"; shift 2 ;;
    *) echo "Usage: bash scripts/setup_dev.sh [--state EXTERNAL_DIRECTORY] [--install-browser] [--browser-executable PATH]" >&2; exit 2 ;;
  esac
done
command -v python3 >/dev/null
command -v node >/dev/null
command -v npm >/dev/null
python3 - "$DEV_ROOT" "$DEV_STATE" <<'PY'
from pathlib import Path
import sys
root, state = map(lambda p: Path(p).resolve(), sys.argv[1:])
if state == root or state.is_relative_to(root):
    raise SystemExit('The dependency/cache directory must be outside the checkout.')
if sys.version_info[:2] != (3, 12):
    raise SystemExit('Use Python 3.12, matching the development CI lock.')
PY
DEV_STATE="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$DEV_STATE")"
mkdir -p "$DEV_STATE/node" "$DEV_STATE/artifacts" "$DEV_STATE/pip-cache" "$DEV_STATE/npm-cache"
export PIP_CACHE_DIR="$DEV_STATE/pip-cache"
export PYTHONPYCACHEPREFIX="$DEV_STATE/pycache"
export PLAYWRIGHT_BROWSERS_PATH="$DEV_STATE/playwright-browsers"

python3 -m venv "$DEV_STATE/venv"
"$DEV_STATE/venv/bin/python" -m pip install --disable-pip-version-check \
  --require-hashes -r "$DEV_ROOT/requirements-dev.txt"
cp "$DEV_ROOT/package.json" "$DEV_ROOT/package-lock.json" "$DEV_STATE/node/"
npm --cache "$DEV_STATE/npm-cache" ci --prefix "$DEV_STATE/node" \
  --ignore-scripts --no-audit --no-fund
"$DEV_STATE/venv/bin/python" -m pip check
FRIDGE_TEST_DOM="$DEV_STATE/node/node_modules/linkedom" \
  node -e 'require(process.env.FRIDGE_TEST_DOM);if(Number(process.versions.node.split(".")[0])<20)process.exit(1)'
bash "$DEV_ROOT/scripts/install_actionlint.sh" "$DEV_STATE/bin"

if [[ -n "$DEV_BROWSER" ]]; then
  [[ -x "$DEV_BROWSER" ]] || { echo 'Browser executable is unavailable.' >&2; exit 1; }
  "$DEV_BROWSER" --version
elif [[ "$DEV_INSTALL_BROWSER" == true ]]; then
  "$DEV_STATE/venv/bin/python" -m playwright install --with-deps chromium
fi

"$DEV_STATE/venv/bin/python" - "$DEV_ROOT" "$DEV_STATE" "$DEV_BROWSER" <<'PY'
from pathlib import Path
import json, shlex, sys
root, state, browser = sys.argv[1:]
q = shlex.quote
lines = [
    '# Source this in each new shell. No services or data updates start automatically.',
    f'source {q(state + "/venv/bin/activate")}',
    f'export NOTION_DEV_STATE={q(state)}',
    f'export NODE_PATH={q(state + "/node/node_modules")}"${{NODE_PATH:+:$NODE_PATH}}"',
    f'export PATH={q(state + "/bin:" + state + "/node/node_modules/.bin")}:"$PATH"',
    f'export FRIDGE_TEST_DOM={q(state + "/node/node_modules/linkedom")}',
    f'export PYTHONPATH={q(root + ":" + root + "/scripts")}"${{PYTHONPATH:+:$PYTHONPATH}}"',
    f'export PYTHONPYCACHEPREFIX={q(state + "/pycache")}',
    f'export PLAYWRIGHT_BROWSERS_PATH={q(state + "/playwright-browsers")}',
    'export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1',
]
if browser:
    lines.append(f'export NOTION_BROWSER_EXECUTABLE={q(browser)}')
Path(state, 'activate.sh').write_text('\n'.join(lines) + '\n')
print('Ready: source ' + q(state + '/activate.sh'))
PY
