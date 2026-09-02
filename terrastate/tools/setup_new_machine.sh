#!/usr/bin/env bash
# One-command setup for a fresh machine. Run it, re-run it if it dies -- every stage
# skips itself when already satisfied, so there is no state to reason about and no
# need to figure out where it stopped.
#
#   bash tools/setup_new_machine.sh [DATA_ROOT]
#
# DATA_ROOT defaults to ../TrainData/EarthNet2021/earthnet2021x relative to the repo.
# Needs ~80 GB free: 69 GB of splits, 0.8 GB of weights, the rest headroom.
#
# Output is deliberately terse -- one line per stage, a PASS/FAIL block at the end.
# If a stage fails it prints exactly what to do about it and stops; nothing later
# runs on a broken foundation.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"        # <repo>/terrastate
cd "$REPO"
DATA_ROOT="${1:-$(cd "$REPO/../.." && pwd)/TrainData/EarthNet2021/earthnet2021x}"
DL="$(cd "$REPO/../.." && pwd)/_downloads"
VENV="$(cd "$REPO/.." && pwd)/.venv-worldmodel"
mkdir -p "$DL"

STAGE=0
ok ()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
skip () { printf '  --   %s (已就绪，跳过)\n' "$*"; }
step () { STAGE=$((STAGE+1)); printf '\n[%d/7] %s\n' "$STAGE" "$*"; }
die ()  { printf '\n  \033[31m失败\033[0m %s\n\n  怎么办：%s\n\n' "$1" "$2"; exit 1; }

# ---------------------------------------------------------------- 1. 前置检查
step "前置检查"
command -v git >/dev/null || die "没有 git" "先装 git"
PY=$(command -v python3) || die "没有 python3" "先装 python3 >= 3.10"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' \
  || die "python 版本低于 3.10" "装一个 >= 3.10 的 python3"
command -v git-lfs >/dev/null || die "没有 git-lfs" \
  "装它，否则权重只是 133 字节的指针文本：apt install git-lfs / conda install -c conda-forge git-lfs"
command -v aria2c >/dev/null || printf '  警告 没有 aria2c，数据下载会退回 curl（慢很多）\n'
FREE=$(df -BG --output=avail "$REPO" | tail -1 | tr -dc '0-9')
[ "${FREE:-0}" -ge 80 ] || die "磁盘只剩 ${FREE}GB" "至少留 80GB"
ok "git / python3 / git-lfs 就绪，磁盘 ${FREE}GB"

# ---------------------------------------------------------------- 2. LFS 权重
step "拉取我们自己的权重（Git LFS，264MB）"
C1=ops/candidate_c_nightly/20260820T155316Z/formal/run_c1_20260822T131006Z/checkpoint_main.pt
if [ -f "$C1" ] && [ "$(stat -c %s "$C1")" -gt 1000000 ]; then
  skip "LFS 权重"
else
  git lfs install --local >/dev/null 2>&1
  git lfs pull || die "git lfs pull 失败" "检查到 github 的网络，或让上一台机器打包传过来"
fi
BAD=0
while read -r want path; do
  [ -f "$path" ] || { printf '  缺失 %s\n' "$path"; BAD=1; continue; }
  got=$(sha256sum "$path" | cut -c1-16)
  [ "$got" = "$want" ] || { printf '  SHA 不符 %s (%s != %s)\n' "$path" "$got" "$want"; BAD=1; }
done <<EOF
474f94340763e9ba $C1
7051e04afc541100 ops/candidate_c_nightly/20260820T155316Z/formal/run_c0r_20260823T063516Z/checkpoint_main.pt
a5d2a0cc28ad7c01 runs/resume11904_to14880/20260818_112933/checkpoint_last.pt
EOF
[ "$BAD" = 0 ] || die "权重校验不通过" "多半是 git-lfs 没装就 clone 了。装好 git-lfs 后跑：git lfs pull"
ok "C1 / C0R / V2 权重校验通过"

# ---------------------------------------------------------------- 3. Python 环境
step "Python 环境"
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c 'import torch,earthnet,xarray,netCDF4,timm,segmentation_models_pytorch,bottleneck' 2>/dev/null; then
  skip "venv"
else
  [ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV" 2>/dev/null \
    || "$PY" -m virtualenv "$VENV" 2>/dev/null \
    || { "$PY" -m pip install -q --user virtualenv && "$PY" -m virtualenv "$VENV"; } \
    || die "建 venv 失败" "python3-venv 没装且 virtualenv 也拿不到；apt install python3-venv 或 pip install --user virtualenv"
  PKGS="torch torchvision numpy>=2 xarray netCDF4 zarr dask[array] pyproj timm einops
        pyyaml tqdm bottleneck segmentation-models-pytorch earthnet==0.3.9 lightning torchmetrics
        matplotlib"
  "$VENV/bin/pip" install -q --disable-pip-version-check $PKGS 2>/dev/null \
   || "$VENV/bin/pip" install -q --disable-pip-version-check \
        -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com $PKGS \
   || die "pip 安装失败" "手动跑一次看报错：$VENV/bin/pip install torch earthnet==0.3.9 ..."
fi
"$VENV/bin/python" - <<'PYEOF' || die "依赖导入失败" "看上面缺哪个包，单独 pip install"
import earthnet, torch
assert earthnet.__version__ == "0.3.9", f"earthnet 必须是 0.3.9（官方 scorer），当前 {earthnet.__version__}"
import xarray, netCDF4, timm, segmentation_models_pytorch, bottleneck, yaml, matplotlib  # noqa
print(f"  OK   torch {torch.__version__}  cuda={torch.cuda.is_available()}  earthnet {earthnet.__version__}")
PYEOF

# ---------------------------------------------------------------- 4. 官方基线权重
step "官方基线权重（Zenodo 2.3GB —— 可选，失败不阻塞后续）"
GEN_CK=checkpoints/greenearthnet_official
if [ -f "$GEN_CK/contextformer/contextformer6M/seed42.ckpt" ]; then
  skip "基线权重"
elif bash tools/fetch_zenodo_baselines.sh "$DL"; then
  for m in contextformer/contextformer6M convlstm/convlstm1M predrnn/predrnn1M simvp/simvp6M; do
    mkdir -p "$GEN_CK/$m"
    unzip -j -o -q "$DL/model_weights.zip" "model_weights/$m/*" -d "$GEN_CK/$m" \
      || die "解压 $m 失败" "删掉 $DL/model_weights.zip 重跑"
  done
  for f in "$GEN_CK"/*/*/seed=*.ckpt; do [ -e "$f" ] && mv "$f" "${f/seed=/seed}"; done
else
  BASELINES_SKIPPED=1
  printf '  \033[33m跳过\033[0m 基线权重没下下来。**这不阻塞任何事** —— 它只用于重跑 E1，\n'
  printf '       而 E1 已全部完成，结果 JSON 都在仓库里。想补时单独跑：\n'
  printf '         bash tools/fetch_zenodo_baselines.sh\n'
fi
if [ -z "${BASELINES_SKIPPED:-}" ]; then
  BAD=0
  while read -r want rel; do
    got=$(sha256sum "$GEN_CK/$rel" 2>/dev/null | cut -c1-16)
    [ "$got" = "$want" ] || { printf '  SHA 不符或缺失 %s\n' "$rel"; BAD=1; }
  done <<'EOF'
ec6706e8a904bba8 contextformer/contextformer6M/seed42.ckpt
c172bd6157976fd0 contextformer/contextformer6M/seed27.ckpt
6d9a36d2e1b34aaf contextformer/contextformer6M/seed97.ckpt
943858aa59fe644b convlstm/convlstm1M/seed42.ckpt
7e84f48934e70b92 predrnn/predrnn1M/seed42.ckpt
8192fe98228cb6fc simvp/simvp6M/seed42.ckpt
EOF
  [ "$BAD" = 0 ] || die "基线权重校验不通过" "删掉 $GEN_CK 和 $DL/model_weights.zip 重跑本脚本"
  ok "12 个基线权重就位（抽查 6 个 SHA 通过）"
fi

# ---------------------------------------------------------------- 5. 上游只读仓库
step "上游代码（只读，不 pip install）"
[ -d "$DL/emp-v0.1.0/earthnet_models_pytorch" ] \
  && skip "earthnet-models-pytorch" \
  || git clone -q --depth 1 --branch v0.1.0 \
       https://github.com/earthnet2021/earthnet-models-pytorch.git "$DL/emp-v0.1.0" \
       || die "clone emp 失败" "网络问题；也可从上一台机器拷 $DL/emp-v0.1.0"
[ -d "$DL/greenearthnet/model_configs" ] \
  && skip "greenearthnet configs" \
  || git clone -q --depth 1 https://github.com/vitusbenson/greenearthnet.git "$DL/greenearthnet" \
       || die "clone greenearthnet 失败" "网络问题；也可从上一台机器拷 $DL/greenearthnet"
ok "上游代码就位（只指 sys.path，绝不 pip install —— 它锁死 torch 1.13.1）"

# ---------------------------------------------------------------- 6. 数据集
step "数据集（5 个 split，约 69GB —— 最耗时的一步）"
count_ok () {                       # 数量全对则返回 0，不必再联网列举
  while read -r n sp; do
    [ "$(find "$DATA_ROOT/$sp" -name '*.nc' 2>/dev/null | wc -l)" = "$n" ] || return 1
  done <<'EOF'
952 val_chopped
1904 ood-t_chopped
2856 iid_chopped
10536 ood-s_chopped
7024 ood-st_chopped
EOF
  return 0
}
if count_ok; then
  skip "数据集"
else
  bash tools/fetch_earthnet_splits.sh "$DATA_ROOT" \
    || die "数据下载失败" "重跑本脚本即可续传；已下好的文件会跳过"
fi
BAD=0
while read -r n sp; do
  got=$(find "$DATA_ROOT/$sp" -name '*.nc' 2>/dev/null | wc -l)
  [ "$got" = "$n" ] || { printf '  %s 数量不对：%s / %s\n' "$sp" "$got" "$n"; BAD=1; }
done <<'EOF'
952 val_chopped
1904 ood-t_chopped
2856 iid_chopped
10536 ood-s_chopped
7024 ood-st_chopped
EOF
[ "$BAD" = 0 ] || die "数据不完整" "重跑本脚本续传。注意别自己另写下载逻辑——分页列举会静默截断"
ok "五个 split 数量全部核对通过"

# ---------------------------------------------------------------- 7. 自检
step "自检：真正加载一次模型"
CFG="$DL/greenearthnet/model_configs" EMP="$DL/emp-v0.1.0" "$VENV/bin/python" - <<'PYEOF' \
  || die "自检失败" "看上面的报错；多半是权重或依赖没装对"
import os, sys
sys.path.insert(0, ".")
from eval.eval_b4_exclusive_contract import load_exclusive
m = load_exclusive("ops/candidate_c_nightly/20260820T155316Z/formal/"
                   "run_c1_20260822T131006Z/checkpoint_main.pt", "cpu")
assert type(m).__name__ == "TerraStateCandidateC", type(m).__name__
sys.path.insert(0, os.environ["EMP"])
ck = "checkpoints/greenearthnet_official/convlstm/convlstm1M/seed42.ckpt"
if os.path.exists(ck):
    from eval.export_emp_baseline_predictions import build_model
    b = build_model(f"{os.environ['CFG']}/convlstm/convlstm1M/seed=42.yaml", ck,
                    os.environ["EMP"])
    print(f"  OK   C1 = {type(m).__name__}；基线 = {type(b).__name__}，两者都 strict=True 加载成功")
else:
    print(f"  OK   C1 = {type(m).__name__} strict=True 加载成功"
          "（基线权重未下载，跳过其加载检查——不影响其他工作）")
PYEOF

cat <<EOF

────────────────────────────────────────────────────────────
安装完成。环境：$VENV/bin/python
             数据：$DATA_ROOT

所有实验（C1 的 Q1/Q2/Q3/Q4 + E1 四 split 主表）在上一台机器上已经全部跑完，
结果 JSON 都在仓库里。所以这里**没有必须补跑的任务**。

想验证环境真的能干活，跑一次汇总（几秒，只读结果文件）：
  cd $REPO && $VENV/bin/python collect_e1_table.py

结果文档：
  思路整理进展/A08_E1主表_同协议重跑结果.md   同协议重跑主表（机械生成）
  思路整理进展/A06_...                        文献数字与自跑数字的分栏对照
  思路整理进展/A04_... §18/§19/§20            C1 的 Q1/Q2、G_abs 诊断、Q3
────────────────────────────────────────────────────────────
EOF
