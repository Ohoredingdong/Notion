#!/usr/bin/env bash
# Pinned official tool; preserves HTTPS verification and verifies its checksum.
set -euo pipefail
actionlint_destination=${1:?Usage: bash scripts/install_actionlint.sh DESTINATION_DIRECTORY}
actionlint_version=1.7.7
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) actionlint_platform=linux_amd64 ;;
  Linux/aarch64) actionlint_platform=linux_arm64 ;;
  Darwin/x86_64) actionlint_platform=darwin_amd64 ;;
  Darwin/arm64) actionlint_platform=darwin_arm64 ;;
  *) echo 'Unsupported actionlint platform' >&2; exit 1 ;;
esac
actionlint_temporary=$(mktemp -d)
trap 'rm -rf "$actionlint_temporary"' EXIT
actionlint_archive="actionlint_${actionlint_version}_${actionlint_platform}.tar.gz"
actionlint_release="https://github.com/rhysd/actionlint/releases/download/v${actionlint_version}"
curl --fail --location --silent --show-error --max-time 90 --output "$actionlint_temporary/$actionlint_archive" "$actionlint_release/$actionlint_archive"
curl --fail --location --silent --show-error --max-time 90 --output "$actionlint_temporary/checksums.txt" "$actionlint_release/actionlint_${actionlint_version}_checksums.txt"
python3 - "$actionlint_temporary" "$actionlint_archive" <<'PY'
import hashlib
from pathlib import Path
import sys
directory, name = Path(sys.argv[1]), sys.argv[2]
matches = [line.split()[0] for line in (directory / 'checksums.txt').read_text().splitlines() if line.split()[-1] == name]
if len(matches) != 1 or hashlib.sha256((directory / name).read_bytes()).hexdigest() != matches[0]:
    raise SystemExit('Official actionlint checksum verification failed')
print('Official actionlint checksum verified')
PY
mkdir -p "$actionlint_destination"
tar -xzf "$actionlint_temporary/$actionlint_archive" -C "$actionlint_destination" actionlint
"$actionlint_destination/actionlint" -version
