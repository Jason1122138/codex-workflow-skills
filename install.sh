#!/usr/bin/env bash
# Install the minimal public Codex roadmap/program workflow package.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="${CODEX_HOME:-$HOME/.codex}"
WRITE_CONFIG=0

for arg in "$@"; do
  case "$arg" in
    --write-config) WRITE_CONFIG=1 ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: CODEX_HOME=/path/to/.codex $0 [--write-config]" >&2
      exit 2
      ;;
  esac
done

install_skill() {
  local name="$1"
  local src="$ROOT_DIR/skills/$name"
  local dest="$DEST_DIR/skills/$name"
  if [ ! -f "$src/SKILL.md" ]; then
    echo "missing skill: $name" >&2
    exit 1
  fi
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$src"/. "$dest"/
  echo "installed skill: $name"
}

install_file() {
  local src="$1"
  local dest="$2"
  local mode="${3:-644}"
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  chmod "$mode" "$dest"
}

write_config_block() {
  local config="$DEST_DIR/config.toml"
  local begin="# BEGIN codex-workflow-skills hooks"
  local end="# END codex-workflow-skills hooks"
  local tmp
  mkdir -p "$DEST_DIR"
  tmp="$(mktemp)"
  if [ -f "$config" ]; then
    awk -v begin="$begin" -v end="$end" '
      $0 == begin { skip = 1; next }
      $0 == end { skip = 0; next }
      skip != 1 { print }
    ' "$config" > "$tmp"
  else
    : > "$tmp"
  fi
  {
    echo ""
    echo "$begin"
    cat "$ROOT_DIR/hooks/config.toml.snippet"
    echo "$end"
  } >> "$tmp"
  mv "$tmp" "$config"
  echo "updated config: $config"
}

install_skill roadmap
install_skill program
install_skill plan-check
install_file "$ROOT_DIR/hooks/roadmap_hook.py" "$DEST_DIR/hooks/roadmap_hook.py" 755
install_file "$ROOT_DIR/hooks/config.toml.snippet" "$DEST_DIR/hooks/roadmap_hook.config.toml.snippet" 644
mkdir -p "$DEST_DIR/roadmap"
cp -R "$ROOT_DIR/roadmap-assets"/. "$DEST_DIR/roadmap"/

if [ "$WRITE_CONFIG" = "1" ]; then
  write_config_block
else
  echo "pass --write-config to add/update hook entries in $DEST_DIR/config.toml"
fi

echo "done"
