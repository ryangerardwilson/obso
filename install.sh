#!/usr/bin/env bash
set -euo pipefail

APP="obso"
LEGACY_APP="omarchy_branding_safe_overrides"
APP_HOME="$HOME/.${APP}"
INSTALL_DIR="$APP_HOME/bin"
APP_DIR="$APP_HOME/app"
PUBLIC_BIN_DIR="$HOME/.local/bin"
PUBLIC_LAUNCHER="$PUBLIC_BIN_DIR/${APP}"
LEGACY_APP_HOME="$HOME/.${LEGACY_APP}"
LEGACY_PUBLIC_LAUNCHER="$PUBLIC_BIN_DIR/${LEGACY_APP}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
${APP} Installer

Usage: install.sh [options]

Options:
  -h                         Show this help and exit
  -v                         Print the local checkout version
  -u                         Install or refresh from the current checkout
  -n                         Compatibility no-op; shell config is never modified

      --help                 Compatibility alias for -h
      --version              Compatibility alias for -v
      --upgrade              Compatibility alias for -u
      --no-modify-path       Compatibility alias for -n
EOF
}

show_version=false
upgrade=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -v|--version)
      show_version=true
      shift
      ;;
    -u|--upgrade)
      upgrade=true
      shift
      ;;
    -n|--no-modify-path)
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$show_version" == "true" ]]; then
  SOURCE_DIR_ENV="$SOURCE_DIR" python3 - <<'PY'
from os import environ
from pathlib import Path
namespace = {}
exec(Path(environ["SOURCE_DIR_ENV"]).joinpath("_version.py").read_text(encoding="utf-8"), namespace)
print(namespace["__version__"])
PY
  exit 0
fi

if [[ "$upgrade" != "true" ]]; then
  usage
  exit 0
fi

mkdir -p "$APP_DIR" "$INSTALL_DIR" "$PUBLIC_BIN_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.venv' \
  "${SOURCE_DIR}/" "${APP_DIR}/"

cat > "${INSTALL_DIR}/${APP}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec python3 "${APP_DIR}/main.py" "\$@"
EOF
chmod 755 "${INSTALL_DIR}/${APP}"

cat > "${PUBLIC_LAUNCHER}" <<EOF
#!/usr/bin/env bash
# Managed by ${APP} local-bin launcher
set -euo pipefail
exec "${INSTALL_DIR}/${APP}" "\$@"
EOF
chmod 755 "${PUBLIC_LAUNCHER}"

"${PUBLIC_LAUNCHER}" --install-runtime

rm -rf "${LEGACY_APP_HOME}"
rm -f "${LEGACY_PUBLIC_LAUNCHER}"

echo "Installed ${APP} from local checkout"
echo "Launcher: ${PUBLIC_LAUNCHER}"
if [[ ":$PATH:" != *":$PUBLIC_BIN_DIR:"* ]]; then
  echo "Manually add to ~/.bashrc if needed: export PATH=${PUBLIC_BIN_DIR}:\$PATH"
fi
