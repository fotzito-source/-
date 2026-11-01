#!/bin/bash
# Only for Claude Code cloud containers (not needed on your own machine): Remotion can't download its headless Chrome
# there, and it launches Chrome without a proxy while the container only reaches the internet through $HTTPS_PROXY
# (Google Fonts load at render time). This points Remotion at the preinstalled Playwright headless shell, through a
# small wrapper that swaps Remotion's proxy flags for $HTTPS_PROXY. Run it once after `npm install`.
set -euo pipefail
cd "$(dirname "$0")"
SHELL_BIN=$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)
[ -n "$SHELL_BIN" ] || { echo "No preinstalled headless shell under /opt/pw-browsers"; exit 1; }
VERSION=$(node -e "console.log(require(require('path').resolve('node_modules/@remotion/renderer/dist/browser/get-chrome-download-url.js')).TESTED_VERSION)")
D=node_modules/.remotion/chrome-headless-shell
mkdir -p "$D/linux64/chrome-headless-shell-linux64"
printf '%s' "$VERSION" > "$D/VERSION"
cat > "$D/linux64/chrome-headless-shell-linux64/chrome-headless-shell" <<WRAP
#!/bin/bash
args=()
for a in "\$@"; do
  case "\$a" in
    --no-proxy-server|--proxy-bypass-list=*|--proxy-server=*) continue ;;
  esac
  args+=("\$a")
done
if [ -n "\${HTTPS_PROXY:-}" ]; then exec "$SHELL_BIN" --proxy-server="\$HTTPS_PROXY" "\${args[@]}"; fi
exec "$SHELL_BIN" "\${args[@]}"
WRAP
chmod +x "$D/linux64/chrome-headless-shell-linux64/chrome-headless-shell"
echo "Remotion will render with $SHELL_BIN (Chrome version file: $VERSION)"
