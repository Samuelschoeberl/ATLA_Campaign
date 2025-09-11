#!/usr/bin/env bash
set -euo pipefail

# spore_append.sh
# Append a LINE to markdown files. Intended for use inside a notes/wiki folder.

LINE=""
TARGET="."
RECURSIVE=0
DRYRUN=0
BACKUP=0
ENSURE_NEWLINE=1

usage(){
  cat <<EOF
Usage: spore_append.sh -l "LINE" [-p PATH] [-R] [-n] [-b] [-h]
  -l LINE    The line to append (required). Quote if it contains spaces or special chars.
  -p PATH    Target directory (default: current directory)
  -R         Recursive (walk subdirectories)
  -n         Dry-run (show what would be done)
  -b         Make a backups/ directory and copy matched files there before modifying
  -h         Show this help

Example:
  spore_append.sh -l '#spore [[GrowthGuide]]' -p ./Mycelium -R
EOF
  exit 0
}

while getopts ":l:p:Rnbh" opt; do
  case "$opt" in
    l) LINE="$OPTARG" ;;
    p) TARGET="$OPTARG" ;;
    R) RECURSIVE=1 ;;
    n) DRYRUN=1 ;;
    b) BACKUP=1 ;;
    h) usage ;;
    :) echo "Missing argument for -$OPTARG" >&2; usage ;;
    \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
  esac
done

if [ -z "$LINE" ]; then
  echo "Error: -l LINE is required" >&2
  usage
fi

if [ ! -e "$TARGET" ]; then
  echo "Error: target path '$TARGET' does not exist" >&2
  exit 2
fi

# Prepare file list (portable, avoids bash-4+ mapfile)
FILES=()

if [ "$RECURSIVE" -eq 1 ]; then
  # find handles spaces safely with -print0; read -d '' into the array
  while IFS= read -r -d '' f; do
    FILES+=("$f")
  done < <(find "$TARGET" -type f -name '*.md' -print0)
else
  # non-recursive: use nullglob to avoid literal pattern when no matches
  shopt -s nullglob
  for f in "$TARGET"/*.md; do
    [ -e "$f" ] || continue
    FILES+=("$f")
  done
  shopt -u nullglob
fi

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "No .md files found in target: $TARGET" >&2
  exit 0
fi

if [ "$BACKUP" -eq 1 ]; then
  mkdir -p backups
  if [ "$DRYRUN" -eq 1 ]; then
    echo "[dry-run] Would copy ${#FILES[@]} files into backups/"
  else
    echo "Backing up ${#FILES[@]} files to backups/"
    cp -p -- "${FILES[@]}" backups/ 2>/dev/null || cp -p "${FILES[@]}" backups/ 2>/dev/null || true
  fi
fi

append_file(){
  local f="$1"
  if [ "$DRYRUN" -eq 1 ]; then
    printf "Would append to %s: %s\n" "$f" "$LINE"
    return
  fi
  # ensure newline at EOF if requested
  if [ "$ENSURE_NEWLINE" -eq 1 ] && [ -s "$f" ]; then
    last=$(tail -c1 "$f" | od -An -t uC | tr -d ' ')
    if [ "$last" != "10" ]; then
      printf '\n' >> "$f"
    fi
  fi
  printf '%s\n' "$LINE" >> "$f"
}

# Iterate and append
for f in "${FILES[@]}"; do
  append_file "$f"
done

echo "Done. (${#FILES[@]} files processed)"
