#!/usr/bin/env bash
set -euo pipefail

# spore_prune.sh
# Remove a literal LINE from markdown files.
# Uses perl (available on macOS) to safely remove literal strings including special chars.

LINE=""
TARGET="."
RECURSIVE=0
DRYRUN=0
BACKUP=0
#!/usr/bin/env bash
set -euo pipefail

# spore_prune.sh
# Remove a literal LINE from markdown files.
# Uses perl (available on macOS) to safely remove literal strings including special chars.

LINE=""
TARGET="."
RECURSIVE=0
DRYRUN=0
BACKUP=0

usage(){
  cat <<EOF
Usage: spore_prune.sh -l "LINE" [-p PATH] [-R] [-n] [-b] [-h]
  -l LINE    The literal text to remove (required). Quote if it contains spaces or special chars.
  -p PATH    Target directory (default: current directory)
  -R         Recursive (walk subdirectories)
  -n         Dry-run (show files and counts; does not modify)
  -b         Make a backups/ directory and copy matched files there before modifying
  -h         Show this help

Example:
  spore_prune.sh -l '#spore [[GrowthGuide]]' -p './Player Root/Rules/core rules/Stat Shorts' -n
  spore_prune.sh -l '#spore [[GrowthGuide]]' -p ./ -R -b
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

# Collect files
FILES=()
if [ "$RECURSIVE" -eq 1 ]; then
  while IFS= read -r -d '' f; do
    FILES+=("$f")
  done < <(find "$TARGET" -type f -name '*.md' -print0)
else
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

if [ "$DRYRUN" -eq 1 ]; then
  echo "Dry-run: scanning ${#FILES[@]} files for occurrences of: $LINE"
  total=0
  for f in "${FILES[@]}"; do
    # use grep -c to count matching lines (robust numeric output)
    count=$(grep -F -c -- "$LINE" "$f" 2>/dev/null || true)
    count=${count:-0}
    if [ "$count" -gt 0 ]; then
      printf "%s: %d\n" "$f" "$count"
      total=$((total+count))
    fi
  done
  printf "Dry-run summary: %d total occurrences in %d files\n" "$total" "${#FILES[@]}"
  exit 0
fi

# Make backups folder if requested
if [ "$BACKUP" -eq 1 ]; then
  mkdir -p backups
fi

changed=0
for f in "${FILES[@]}"; do
  # use grep -c for reliable numeric counts
  count=$(grep -F -c -- "$LINE" "$f" 2>/dev/null || true)
  count=${count:-0}
  if [ "$count" -eq 0 ]; then
    continue
  fi
  if [ "$BACKUP" -eq 1 ]; then
    cp -p -- "$f" backups/ 2>/dev/null || cp -p "$f" backups/ 2>/dev/null || true
  fi
  # Use perl to remove all literal occurrences, including possible trailing CRLF/newline after them
  perl -0777 -pe "s/\Q$LINE\E(?:\r?\n)?//g" -- "$f" > "$f.tmp" && mv "$f.tmp" "$f"
  printf "Pruned %d occurrences from %s\n" "$count" "$f"
  changed=$((changed+1))
done

printf "Done. %d files modified.\n" "$changed"
