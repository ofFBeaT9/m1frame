#!/bin/bash
# Cloud-session setup: Python deps (m1frame MCP server) plus the REA
# reverse-engineering MCP server with Ghidra for native analysis.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# m1frame Python deps (requirements.txt pins mcp<2, which mcp_server.py needs).
pip install -q -r requirements.txt

# REA needs Node >=22.23.4 / >=24.22.1; the image ships an older Node 22.
NODE_VERSION=24.22.2
NODE_DIR=/opt/node24
if [ "$("$NODE_DIR/bin/node" --version 2>/dev/null)" != "v$NODE_VERSION" ]; then
  tmp=$(mktemp -d)
  tarball="node-v$NODE_VERSION-linux-x64.tar.xz"
  curl -fsSL -o "$tmp/$tarball" "https://nodejs.org/dist/v$NODE_VERSION/$tarball"
  curl -fsSL "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" | grep " $tarball\$" > "$tmp/sum"
  (cd "$tmp" && sha256sum -c sum)
  rm -rf "$NODE_DIR" && mkdir -p "$NODE_DIR"
  tar -xJf "$tmp/$tarball" -C "$NODE_DIR" --strip-components=1
  rm -rf "$tmp"
fi
export PATH="$NODE_DIR/bin:$PATH"

if ! command -v rea >/dev/null 2>&1; then
  npm install --global rea-agents@latest
fi

# Ghidra 12.1.x (REA's verified provider) for native decompilation.
GHIDRA_DIR=/opt/ghidra_12.1.4_PUBLIC
GHIDRA_SHA256=ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db
if [ ! -x "$GHIDRA_DIR/support/analyzeHeadless" ]; then
  tmp=$(mktemp -d)
  curl -fsSL -o "$tmp/ghidra.zip" \
    "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip"
  echo "$GHIDRA_SHA256  $tmp/ghidra.zip" | sha256sum -c -
  unzip -q -o "$tmp/ghidra.zip" -d /opt
  rm -rf "$tmp"
fi

export GHIDRA_INSTALL_DIR="$GHIDRA_DIR"
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

# Register REA's MCP server (user scope, ~/.claude.json) and its skill.
(cd ~ && rea setup --client claude_code --yes >/dev/null)

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$NODE_DIR/bin:\$PATH\""
    echo "export GHIDRA_INSTALL_DIR=\"$GHIDRA_DIR\""
    echo "export JAVA_HOME=\"$JAVA_HOME\""
  } >> "$CLAUDE_ENV_FILE"
fi
