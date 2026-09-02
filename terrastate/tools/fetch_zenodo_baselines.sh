#!/usr/bin/env bash
# Fetch the official GreenEarthNet baseline weights from Zenodo, surviving links
# that drop mid-transfer.
#
#   bash tools/fetch_zenodo_baselines.sh [dest-dir]
#
# Why this is not just a wget: on some networks the connection dies at a random
# point between 200 MB and 900 MB of the 2.3 GB file. A single attempt leaves a
# truncated zip whose central directory is missing, which unzip reports as
# "End-of-central-directory signature not found" -- looks like corruption, is
# actually just an incomplete download. The loop below resumes with `-C -` until
# the size matches, then verifies the SHA before anyone tries to open it.
#
# THIS IS OPTIONAL. These weights are only needed to re-run the E1 baselines, and
# E1 is already complete -- every metrics_en21x.json is committed. Skip it unless
# you specifically intend to re-score the baselines.
set -uo pipefail

DEST="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/_downloads}"
URL=https://zenodo.org/records/10793870/files/model_weights.zip
WANT_SHA=00b7d86ef7aef8f47ff9247dacf3d9f7320b9a750734337f4d7d91f9ef0a5ce1
WANT_SIZE=2452814122
ZIP="$DEST/model_weights.zip"
mkdir -p "$DEST"

unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY

for attempt in $(seq 1 40); do
  have=$(stat -c %s "$ZIP" 2>/dev/null || echo 0)
  if [ "$have" -eq "$WANT_SIZE" ]; then
    got=$(sha256sum "$ZIP" | cut -d' ' -f1)
    if [ "$got" = "$WANT_SHA" ]; then
      echo "[ok] 完整且 SHA 正确：$ZIP"
      exit 0
    fi
    echo "[bad] 大小对但 SHA 不符，删除重下"
    rm -f "$ZIP"; continue
  fi
  pct=$(( have * 100 / WANT_SIZE ))
  echo "[$attempt/40] 续传中… 已有 $((have/1024/1024)) MB / 2339 MB (${pct}%)"
  curl -sS -C - --retry 8 --retry-delay 5 --retry-all-errors \
       --connect-timeout 45 --speed-time 60 --speed-limit 10240 \
       -o "$ZIP" "$URL" || true          # 掉线就进下一轮继续续传
  sleep 3
done

have=$(stat -c %s "$ZIP" 2>/dev/null || echo 0)
cat >&2 <<EOF

[fail] 40 轮之后仍未下完（当前 $((have/1024/1024)) MB / 2339 MB）。

这个文件是**可选**的——它只用于重跑 E1 基线，而 E1 已经全部跑完，
结果 JSON 都在仓库里。没有它同样可以继续所有其他工作。

真要它的话，三条路：
  1. 换台能下的机器下好，scp 过来，放到 $ZIP
  2. 浏览器下载 https://zenodo.org/records/10793870 再传上去
  3. 反复重跑本脚本——每轮都从断点继续，网络时好时坏时最终能下完
校验：sha256sum 应为 $WANT_SHA
EOF
exit 1
