#!/usr/bin/env bash
# Download + reassemble weights uploaded by upload_weights_via_github.sh.
# Run on ANY machine that can reach github.com (with gh authenticated).
#
# Usage:
#   ./download_weights_via_github.sh <release-tag> <out-dir> [owner/repo]
#
# Example:
#   ./download_weights_via_github.sh weights-direct-p4-ep200 ./restored myorg/obsworld-weights
set -euo pipefail

TAG="${1:?release tag}"
OUT="${2:?output directory}"
REPO="${3:-}"

command -v gh >/dev/null || { echo "gh CLI not found on PATH" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated (run: gh auth login)" >&2; exit 1; }

repo_arg=(); [ -n "$REPO" ] && repo_arg=(--repo "$REPO")
mkdir -p "$OUT"

# 1) fetch all assets of the release
echo "[download] release $TAG -> $OUT"
gh release download "$TAG" "${repo_arg[@]}" --dir "$OUT" --clobber

# 2) verify integrity before reassembly
echo "[verify] sha256"
( cd "$OUT" && sha256sum -c SHA256SUMS.txt )

# 3) reassemble: parts are named "<BASE>.part-000", "<BASE>.part-001", ...
first_part="$(cd "$OUT" && ls *.part-000)"
BASE="${first_part%.part-000}"
echo "[reassemble] $BASE"
cat "$OUT/$BASE".part-* > "$OUT/$BASE"
rm -f "$OUT/$BASE".part-* "$OUT/SHA256SUMS.txt"

# 4) unpack whatever layers were applied on upload
case "$BASE" in
  *.tar.zst) zstd -d -f "$OUT/$BASE" -o "$OUT/${BASE%.zst}"; rm -f "$OUT/$BASE"
             tar -C "$OUT" -xf "$OUT/${BASE%.zst}"; rm -f "$OUT/${BASE%.zst}" ;;
  *.zst)     zstd -d -f "$OUT/$BASE"; rm -f "$OUT/$BASE" ;;
  *.tar)     tar -C "$OUT" -xf "$OUT/$BASE"; rm -f "$OUT/$BASE" ;;
esac

echo "[done] restored into $OUT:"; ls -la "$OUT"
