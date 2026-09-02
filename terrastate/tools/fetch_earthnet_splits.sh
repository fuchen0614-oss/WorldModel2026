#!/usr/bin/env bash
# Fetch EarthNet2021x splits from the official MPG-BGC S3 mirror.
#
#   tools/fetch_earthnet_splits.sh <dest-root> [split ...]
#
# Default splits are the four CVPR2024 "chopped" tracks the main table needs plus
# val_chopped. Pass names explicitly to get others (iid, ood, extreme, seasonal,
# train). Resumable: files already at the listed size are skipped, so re-running
# after an interruption only fetches what is missing.
#
# Three things this guards against, all of which bit us before:
#
#   * The listing must be asserted against a known object count. A bash pagination
#     loop that swallows one unparseable page will silently declare a split
#     complete -- we measured ood-s_chopped listed as 4000/10536 and ood-st as
#     0/7024 with no error at all.
#   * Do NOT route through a local proxy. s3.bgc-jena.mpg.de is directly reachable
#     and the proxy only adds failure modes.
#   * Transfer with aria2c, not python. Some conda CA bundles are stale and make
#     python raise CERTIFICATE_VERIFY_FAILED intermittently against this cluster
#     even though the server cert is valid and curl succeeds every time.
#     curl/aria2c use the system bundle.
#
# Concurrency is deliberately modest: 16 parallel workers got throttled into
# 2004 HTTP 503s; 4 concurrent with 2 connections per server is stable.
set -uo pipefail

ENDPOINT="https://s3.bgc-jena.mpg.de:9000"
BUCKET="earthnet"
DEST="${1:?usage: fetch_earthnet_splits.sh <dest-root> [split ...]}"; shift
SPLITS=("$@")
[ ${#SPLITS[@]} -eq 0 ] && SPLITS=(val_chopped ood-t_chopped iid_chopped ood-s_chopped ood-st_chopped)

# Object counts published with the dataset; the listing is checked against these.
declare -A EXPECT=(
  [val_chopped]=952      [ood-t_chopped]=1904  [iid_chopped]=2856
  [ood-s_chopped]=10536  [ood-st_chopped]=7024 [iid]=4205
  [ood]=4202             [extreme]=3972        [seasonal]=3880
  [train]=23816
)

unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
if command -v aria2c >/dev/null; then
  XFER=aria2c
elif command -v curl >/dev/null; then
  XFER=curl
  echo "[warn] 没有 aria2c，改用 curl（较慢，但同样断点续传）。装上 aria2c 会快不少。"
else
  echo "need aria2c or curl"; exit 1
fi

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
LIST="$WORK/objects.tsv"; : > "$LIST"

for split in "${SPLITS[@]}"; do
  token=""; before=$(wc -l < "$LIST")
  while :; do
    url="$ENDPOINT/$BUCKET?list-type=2&prefix=earthnet2021x/$split/&max-keys=1000"
    [ -n "$token" ] && url="$url&continuation-token=$(python3 -c \
        'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$token")"
    xml=$(curl -s --retry 8 --retry-delay 5 --retry-all-errors --max-time 120 "$url") || exit 1
    token=$(printf '%s' "$xml" | python3 -c '
import sys, xml.etree.ElementTree as ET
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
r = ET.fromstring(sys.stdin.read())
out = [c.findtext(NS+"Key") + "\t" + c.findtext(NS+"Size")
       for c in r.findall(NS+"Contents") if c.findtext(NS+"Key").endswith(".nc")]
sys.stderr.write("\n".join(out) + ("\n" if out else ""))
print(r.findtext(NS+"NextContinuationToken") or ""
      if r.findtext(NS+"IsTruncated") == "true" else "")
' 2>>"$LIST") || { echo "[$split] listing failed -- refusing to continue"; exit 1; }
    [ -z "$token" ] && break
  done
  got=$(( $(wc -l < "$LIST") - before )); want="${EXPECT[$split]:-0}"
  if [ "$want" -gt 0 ] && [ "$got" -ne "$want" ]; then
    echo "[$split] listed $got objects, expected $want -- aborting rather than downloading a partial split"
    exit 1
  fi
  echo "[list] $split  $got objects"
done

IN="$WORK/aria2.txt"
python3 - "$LIST" "$IN" "$DEST" "$ENDPOINT/$BUCKET" <<'PY'
import os, sys
listing, out, dest, base = sys.argv[1:5]
todo = skip = tb = 0
with open(out, "w") as w:
    for line in open(listing):
        line = line.rstrip("\n")
        if "\t" not in line:
            continue
        key, size = line.rsplit("\t", 1); size = int(size)
        rel = key.split("/", 1)[1]                    # <split>/<season>/<cube>.nc
        path = os.path.join(dest, rel)
        if os.path.exists(path) and os.path.getsize(path) == size:
            skip += 1
            continue
        w.write(f"{base}/{key}\n  dir={os.path.join(dest, os.path.dirname(rel))}\n"
                f"  out={os.path.basename(rel)}\n")
        todo += 1; tb += size
print(f"[plan] {todo} to fetch ({tb/2**30:.2f} GB); {skip} already complete -> {dest}")
PY

if [ "$XFER" = aria2c ]; then
  exec aria2c -i "$IN" --dir="$DEST" --continue=true --auto-file-renaming=false \
    --max-concurrent-downloads=4 --max-connection-per-server=2 --split=2 \
    --max-tries=10 --retry-wait=10 --timeout=120 --connect-timeout=45 \
    --summary-interval=60 --console-log-level=warn
fi

# curl fallback. The aria2 input file is url / dir= / out= triplets; fold it into
# "url<TAB>path" lines and fetch four at a time. -C - resumes a partial file, which
# matters on links that drop mid-transfer -- just re-run the script until it is quiet.
awk '/^http/{u=$0; next} /dir=/{sub(/^ *dir=/,""); d=$0; next}
     /out=/{sub(/^ *out=/,""); print u"\t"d"/"$0}' "$IN" > "$IN.tsv"
echo "[curl] $(wc -l < "$IN.tsv") 个文件，4 路并发"
export DEST
fetch_one () {
  url="${1%%$'\t'*}"; path="${1#*$'\t'}"
  mkdir -p "$(dirname "$path")"
  curl -sS -C - --retry 12 --retry-delay 5 --retry-all-errors \
       --connect-timeout 45 --max-time 900 -o "$path" "$url" \
    || { echo "[fail] $path"; return 1; }
}
export -f fetch_one
tr '\n' '\0' < "$IN.tsv" | xargs -0 -P 4 -I{} bash -c 'fetch_one "$@"' _ {}
echo "[curl] 本轮结束。若有 [fail]，直接重跑本脚本续传。"
