#!/usr/bin/env bash
# m1frame on a Raspberry Pi — always-on remote m1frame for any AI on any device.
#
#   git clone https://github.com/ofFBeaT9/m1frame ~/m1frame
#   bash ~/m1frame/scripts/install_pi.sh            # first install (asks a few questions)
#   bash ~/m1frame/scripts/install_pi.sh --update   # pull the latest m1frame and restart
#
# What it does: installs Python packages in a private venv, writes .env (model key,
# owner password, API token), gives the Pi a public HTTPS address with Tailscale Funnel,
# and runs m1frame as a background service that starts on boot. Safe to re-run.
#
#   bash ~/m1frame/scripts/install_pi.sh --set-key  # add or change the AI provider key later
#
# No API key yet? Answer "n" when asked; everything else installs and runs.
# Non-interactive use: set M1FRAME_PROVIDER (anthropic|openrouter|openai),
# M1FRAME_PROVIDER_KEY (optional), M1FRAME_OWNER_PASSWORD and optionally M1FRAME_PUBLIC_URL.
# Skips: M1FRAME_SKIP_APT=1, M1FRAME_SKIP_TAILSCALE=1, M1FRAME_SKIP_SERVICE=1.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${M1FRAME_PORT:-8765}"
ENV_FILE="$REPO/.env"
SERVICE=m1frame
say()  { printf '\n\033[1;36m▸ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
interactive() { [ -t 0 ]; }

env_get() { # read KEY from .env (single-quoted values written by this script)
  [ -f "$ENV_FILE" ] || return 0
  sed -n "s/^$1='\{0,1\}\([^']*\)'\{0,1\}$/\1/p" "$ENV_FILE" | tail -n1
}
env_set() { # write KEY='value' (replace or append), keep the file private
  local key="$1" val="$2"
  case "$val" in *"'"*|*$'\n'*) die "$key cannot contain a single quote or newline";; esac
  touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
  if grep -q "^$key=" "$ENV_FILE"; then
    local tmp; tmp="$(mktemp)"
    grep -v "^$key=" "$ENV_FILE" > "$tmp" || true
    cat "$tmp" > "$ENV_FILE"; rm -f "$tmp"
  fi
  printf "%s='%s'\n" "$key" "$val" >> "$ENV_FILE"
}
health() { curl -fsS --max-time 5 "$1/health" >/dev/null 2>&1; }

install_service() {
  if [ "${M1FRAME_SKIP_SERVICE:-0}" = 1 ] || ! command -v systemctl >/dev/null 2>&1; then
    warn "No systemd here; start m1frame yourself with:"
    echo "  cd $REPO && .venv/bin/python -m remote"
    return
  fi
  say "Installing the m1frame background service (starts on boot)"
  $SUDO tee /etc/systemd/system/$SERVICE.service >/dev/null <<UNIT
[Unit]
Description=m1frame remote (MCP + /v1 for any AI on any device)
After=network-online.target
Wants=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$REPO
Environment=HOST=127.0.0.1
Environment=PORT=$PORT
Environment=PYTHONUNBUFFERED=1
ExecStart=$REPO/.venv/bin/python -m remote
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now $SERVICE >/dev/null
  $SUDO systemctl restart $SERVICE
}

install_packages() {
  say "Installing m1frame's Python packages (a few minutes on a Pi)"
  [ -x "$REPO/.venv/bin/python" ] || python3 -m venv "$REPO/.venv"
  "$REPO/.venv/bin/python" -m pip install -q --upgrade pip
  "$REPO/.venv/bin/python" -m pip install -q -r "$REPO/requirements.txt"
}

ask_provider() { # "$1" = force: skip the "do you have a key" question. Returns 1 if no key.
  local PROVIDER="${M1FRAME_PROVIDER:-}" KEY="${M1FRAME_PROVIDER_KEY:-}" BACKEND KEYVAR have pick
  if [ -z "$KEY" ] && interactive && [ "${1:-}" != force ]; then
    read -rp "Do you have an AI provider API key now? You can add one later. [y/N]: " have
    case "$have" in [yY]*) ;; *) return 1 ;; esac
  fi
  if [ -z "$KEY" ] && ! interactive; then return 1; fi
  if [ -z "$PROVIDER" ] && interactive; then
    echo "Which AI provider should m1frame think with?"
    echo "  1) Anthropic (Claude)   2) OpenRouter (200+ models, some free)   3) OpenAI"
    read -rp "Choose 1-3 [1]: " pick
    case "${pick:-1}" in 2) PROVIDER=openrouter;; 3) PROVIDER=openai;; *) PROVIDER=anthropic;; esac
  fi
  case "${PROVIDER:-anthropic}" in
    anthropic)  BACKEND=claude;     KEYVAR=ANTHROPIC_API_KEY ;;
    openrouter) BACKEND=openrouter; KEYVAR=OPENROUTER_API_KEY ;;
    openai)     BACKEND=openai;     KEYVAR=OPENAI_API_KEY ;;
    *) die "M1FRAME_PROVIDER must be anthropic, openrouter or openai" ;;
  esac
  if [ -z "$KEY" ] && interactive; then read -rsp "Paste your $KEYVAR (hidden): " KEY; echo; fi
  [ -n "$KEY" ] || return 1
  env_set M1FRAME_BACKEND "$BACKEND"
  env_set "$KEYVAR" "$KEY"
  if [ "$BACKEND" = openrouter ]; then
    local free="${M1FRAME_OPENROUTER_FREE:-}"
    if [ -z "$free" ] && interactive; then
      read -rp "Use OpenRouter's free models only (no charges, ~200 requests/day)? [Y/n]: " free
    fi
    case "${free:-y}" in
      [nN]*) ;;
      *) env_set M1FRAME_MODEL "openrouter/free"   # router that picks a currently-free model
         echo "Using free models (openrouter/free). Change later with M1FRAME_MODEL in $ENV_FILE." ;;
    esac
  fi
}

restart_service() {
  if command -v systemctl >/dev/null 2>&1 && [ "${M1FRAME_SKIP_SERVICE:-0}" != 1 ]; then
    $SUDO systemctl restart $SERVICE
  fi
}

# ── add or change the AI key later ────────────────────────────────────────────
if [ "${1:-}" = "--set-key" ]; then
  interactive || [ -n "${M1FRAME_PROVIDER_KEY:-}" ] || die "Run --set-key in a terminal"
  ask_provider force || die "No key entered; nothing changed"
  restart_service
  echo "✓ Key saved. m1frame restarted with backend $(env_get M1FRAME_BACKEND)."
  exit 0
fi

# ── update mode ───────────────────────────────────────────────────────────────
if [ "${1:-}" = "--update" ]; then
  say "Updating m1frame"
  git -C "$REPO" pull --ff-only
  install_packages
  restart_service
  echo "Done. $(git -C "$REPO" log --oneline -1)"
  exit 0
fi

# ── 1. checks ─────────────────────────────────────────────────────────────────
say "Checking this Raspberry Pi"
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64|x86_64) ;;
  armv7l|armv6l) warn "32-bit OS detected ($ARCH). It may work, but 64-bit Raspberry Pi OS is strongly recommended." ;;
  *) warn "Unrecognised architecture $ARCH; continuing." ;;
esac
MEM_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
[ "$MEM_MB" -gt 0 ] && [ "$MEM_MB" -lt 900 ] && warn "Only ${MEM_MB} MB RAM; a Pi 4/5 with 2 GB+ is recommended."
if [ "${M1FRAME_SKIP_APT:-0}" != 1 ] && command -v apt-get >/dev/null 2>&1; then
  say "Installing system packages (python3-venv, git, curl)"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq python3 python3-venv python3-pip git curl >/dev/null
fi
command -v python3 >/dev/null || die "python3 is missing"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
  || die "Python 3.10+ is required (found $(python3 --version))"

# ── 2. python packages ────────────────────────────────────────────────────────
install_packages

# ── 3. settings (.env) ────────────────────────────────────────────────────────
say "Settings"
if [ -z "$(env_get M1FRAME_BACKEND)" ]; then
  ask_provider || true
else
  echo "Keeping provider: $(env_get M1FRAME_BACKEND)"
fi

if [ -z "$(env_get M1FRAME_OWNER_PASSWORD)" ]; then
  PW="${M1FRAME_OWNER_PASSWORD:-}"
  while [ -z "$PW" ] && interactive; do
    read -rsp "Choose an owner password (12+ characters, asked when an app connects): " PW; echo
    read -rsp "Repeat it: " PW2; echo
    if [ "$PW" != "$PW2" ]; then warn "They don't match."; PW=""; continue; fi
    if [ "${#PW}" -lt 12 ]; then warn "Too short."; PW=""; fi
  done
  [ "${#PW}" -ge 12 ] || die "M1FRAME_OWNER_PASSWORD must be at least 12 characters"
  env_set M1FRAME_OWNER_PASSWORD "$PW"
fi

if [ -z "$(env_get M1FRAME_API_TOKEN)" ]; then
  env_set M1FRAME_API_TOKEN "$("$REPO/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi

# ── 4. public HTTPS address ───────────────────────────────────────────────────
PUBLIC_URL="${M1FRAME_PUBLIC_URL:-$(env_get M1FRAME_PUBLIC_URL)}"
if [ -z "$PUBLIC_URL" ] && [ "${M1FRAME_SKIP_TAILSCALE:-0}" != 1 ]; then
  say "Giving the Pi a public HTTPS address with Tailscale Funnel (free, no domain needed)"
  if ! command -v tailscale >/dev/null 2>&1; then
    curl -fsSL https://tailscale.com/install.sh | $SUDO sh
  fi
  if ! $SUDO tailscale status >/dev/null 2>&1; then
    echo "Sign in to Tailscale in the browser link shown below (create a free account if needed):"
    $SUDO tailscale up
  fi
  DNS="$($SUDO tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
  [ -n "$DNS" ] || die "Could not read this Pi's Tailscale name"
  if ! $SUDO tailscale funnel --bg "$PORT"; then
    warn "Funnel isn't enabled for your Tailscale account yet."
    echo "Open the link above (or https://login.tailscale.com/admin/settings/features),"
    echo "turn on HTTPS and Funnel, then re-run this script."
    exit 1
  fi
  PUBLIC_URL="https://$DNS"
fi
[ -n "$PUBLIC_URL" ] || die "Set M1FRAME_PUBLIC_URL to this Pi's HTTPS address, or allow Tailscale"
env_set M1FRAME_PUBLIC_URL "${PUBLIC_URL%/}"

# ── 5. service ────────────────────────────────────────────────────────────────
install_service

# ── 6. verify ─────────────────────────────────────────────────────────────────
if command -v systemctl >/dev/null 2>&1 && [ "${M1FRAME_SKIP_SERVICE:-0}" != 1 ]; then
  say "Checking it's running"
  for _ in $(seq 1 30); do health "http://127.0.0.1:$PORT" && break; sleep 1; done
  if health "http://127.0.0.1:$PORT"; then echo "✓ m1frame is running on the Pi"
  else warn "Not answering yet. See: journalctl -u $SERVICE -n 50"; fi
  if health "${PUBLIC_URL%/}"; then echo "✓ reachable at ${PUBLIC_URL%/}"
  else warn "Public address not answering yet (Funnel can take a minute). Try ${PUBLIC_URL%/}/health"; fi
fi

cat <<DONE

────────────────────────────────────────────────────────────────
  m1frame is set up on this Pi.

  Connect an AI app (Claude, ChatGPT, Cursor, Claude Code…):
    MCP URL:   ${PUBLIC_URL%/}/mcp
    Sign in on m1frame's page with your owner password.

  Chat apps (Open WebUI, Jan, n8n, openai SDK):
    Base URL:  ${PUBLIC_URL%/}/v1
    API key:   in $ENV_FILE (M1FRAME_API_TOKEN)

$( [ -z "$(env_get M1FRAME_BACKEND)" ] && printf '%s\n' \
"  No AI key yet: tools, recall and connections work now; full runs" \
"  need a key. Add one any time:  bash $REPO/scripts/install_pi.sh --set-key" "" )
  Manage:
    status   systemctl status $SERVICE
    logs     journalctl -u $SERVICE -f
    update   bash $REPO/scripts/install_pi.sh --update
    AI key   bash $REPO/scripts/install_pi.sh --set-key
    sign all apps out   cd $REPO && .venv/bin/python -m remote --revoke-all
────────────────────────────────────────────────────────────────
DONE
