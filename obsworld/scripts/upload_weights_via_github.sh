#!/usr/bin/env bash
# Upload large weights OUT of a locked-down server using GitHub Releases.
# Only needs the same github.com access that `gh`/`git push` use — no Hugging
# Face, no Git LFS quota. Release assets cap at 2GB/file, so we split.
#
# Usage:
#   ./upload_weights_via_github.sh <weights-file-or-dir> <release-tag> [owner/repo]
# Env:
#   PART_SIZE=1900M   # split size, keep < 2GB
#   COMPRESS=1        # zstd-compress before splitting (weights barely shrink; default off)
#   ZSTD_LEVEL=3
#
# Example:
#   ./upload_weights_via_github.sh checkpoints/stage2_direct_p4/checkpoint_epoch200_step_8800.pt weights-direct-p4-ep200 myorg/obsworld-weights
set -euo pipefail

SRC="${1:?path to weights file or dir}"
TAG="${2:?release tag, e.g. weights-direct-p4-ep200}"
REPO="${3:-}"
PART_SIZE="${PART_SIZE:-1900M}"

command -v gh >/dev/null || { echo "gh CLI not found on PATH" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated (run: gh auth login)" >&2; exit 1; }

repo_arg=(); [ -n "$REPO" ] && repo_arg=(--repo "$REPO")
name="$(basename "$SRC")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1) pack: a directory becomes one .tar; a single file is split as-is.
if [ -d "$SRC" ]; then
  echo "[pack] tar directory $SRC"
  tar -C "$(dirname "$SRC")" -cf "$WORK/$name.tar" "$name"
  BASE="$name.tar"; SPLIT_SRC="$WORK/$name.tar"
else
  BASE="$name"; SPLIT_SRC="$SRC"
fi

# 2) optional compression (off by default — trained weights are near-incompressible)
if [ "${COMPRESS:-0}" = "1" ]; then
  echo "[pack] zstd-compress"
  zstd -T0 -"${ZSTD_LEVEL:-3}" "$SPLIT_SRC" -o "$WORK/$BASE.zst"
  BASE="$BASE.zst"; SPLIT_SRC="$WORK/$BASE"
fi

# 3) split into < 2GB parts + checksum
echo "[split] $BASE -> ${PART_SIZE} parts"
( cd "$WORK" && split -b "$PART_SIZE" -d --suffix-length=3 "$SPLIT_SRC" "$BASE.part-" )
( cd "$WORK" && sha256sum "$BASE".part-* > SHA256SUMS.txt )
echo "[split] parts:"; ( cd "$WORK" && ls -la "$BASE".part-* SHA256SUMS.txt )

# 4) create the release (if needed) and upload every part + the checksum file
gh release view "$TAG" "${repo_arg[@]}" >/dev/null 2>&1 \
  || gh release create "$TAG" "${repo_arg[@]}" --title "$TAG" --notes "weights artifact: $BASE"
echo "[upload] pushing assets to release $TAG"
gh release upload "$TAG" "${repo_arg[@]}" --clobber "$WORK/$BASE".part-* "$WORK/SHA256SUMS.txt"

echo "[done] uploaded $BASE ($(cd "$WORK" && ls "$BASE".part-* | wc -l) parts) to release $TAG"
echo "       download with: ./download_weights_via_github.sh $TAG <out-dir> ${REPO}"
