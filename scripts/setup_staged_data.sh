#!/bin/bash
# ===========================================================
# WorldModel Stage1 混合存储数据搬运脚本
# ===========================================================
# 目的: 将网络盘数据复制到运存+本地盘,提速训练
#
# 策略:
#   - S2L2A (842G) → /dev/shm (运存, 1004G 可用)
#   - S1GRD (168G) → /tmp (本地 SSD)
#   - 用软链拼出 data_root 门面目录
#
# 预计时间: ~1.5-2 小时
# ===========================================================

set -e

# 路径定义
SRC=/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1
SHM_ROOT=/dev/shm/zjliu17_ssl4eo
TMP_ROOT=/tmp/zjliu17_ssl4eo

echo "============================================================"
echo "WorldModel Stage1 数据搬运"
echo "============================================================"
echo "原始数据: $SRC"
echo "目标路径:"
echo "  - S2L2A (842G) → /dev/shm (运存)"
echo "  - S1GRD (168G) → /tmp (本地盘)"
echo ""

# 安全检查
if [ ! -d "$SRC/train" ]; then
    echo "❌ 错误: 原始数据不存在: $SRC/train"
    exit 1
fi

echo "当前 /dev/shm 状态:"
df -h /dev/shm
echo ""

SHM_AVAIL=$(df -BG /dev/shm | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$SHM_AVAIL" -lt 850 ]; then
    echo "⚠️  警告: /dev/shm 剩余 ${SHM_AVAIL}G < 850G"
    echo "    S2L2A 需要 842G,空间可能不足"
    echo "    建议检查是否有其他用户占用: ls -lh /dev/shm"
    read -p "    是否继续? (y/N) " confirm
    [ "$confirm" != "y" ] && exit 1
fi

# 检查是否已存在
if [ -d "$SHM_ROOT" ]; then
    echo "⚠️  $SHM_ROOT 已存在"
    du -sh "$SHM_ROOT"
    read -p "    是否删除重建? (y/N) " confirm
    if [ "$confirm" == "y" ]; then
        echo "删除旧数据..."
        rm -rf "$SHM_ROOT"
    else
        echo "取消操作"
        exit 0
    fi
fi

if [ -d "$TMP_ROOT" ]; then
    echo "⚠️  $TMP_ROOT 已存在"
    du -sh "$TMP_ROOT"
    read -p "    是否删除重建? (y/N) " confirm
    if [ "$confirm" == "y" ]; then
        echo "删除旧数据..."
        rm -rf "$TMP_ROOT"
    else
        echo "取消操作"
        exit 0
    fi
fi

echo ""
echo "即将开始复制,预计耗时 1.5-2 小时"
read -p "按 Enter 开始,Ctrl+C 取消... " _

# 创建目录结构
echo ""
echo "[1/4] 创建目录结构..."
mkdir -p "$SHM_ROOT/train"
mkdir -p "$TMP_ROOT/train"

# 复制 S2 到运存 (最耗时)
echo ""
echo "[2/4] 复制 S2L2A → /dev/shm (842G, 预计 ~1 小时)..."
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
rsync -ah --info=progress2 "$SRC/train/S2L2A/" "$SHM_ROOT/train/S2L2A/"
echo "S2 复制完成: $(date '+%Y-%m-%d %H:%M:%S')"

# 复制 S1 到本地盘
echo ""
echo "[3/4] 复制 S1GRD → /tmp (168G, 预计 ~20 分钟)..."
rsync -ah --info=progress2 "$SRC/train/S1GRD/" "$TMP_ROOT/train/S1GRD/"
echo "S1 复制完成: $(date '+%Y-%m-%d %H:%M:%S')"

# 创建软链
echo ""
echo "[4/4] 创建软链..."
ln -sf "$TMP_ROOT/train/S1GRD" "$SHM_ROOT/train/S1GRD"

# 验证
echo ""
echo "============================================================"
echo "✅ 数据搬运完成"
echo "============================================================"
echo "目录结构:"
ls -lh "$SHM_ROOT/train/"
echo ""
echo "空间占用:"
du -sh "$SHM_ROOT"
du -sh "$TMP_ROOT"
echo ""
df -h /dev/shm
echo ""
echo "验证数据完整性:"
S2_COUNT=$(ls "$SHM_ROOT/train/S2L2A/"*.tar 2>/dev/null | wc -l)
S1_COUNT=$(ls "$TMP_ROOT/train/S1GRD/"*.tar 2>/dev/null | wc -l)
echo "  S2 tar 文件数: $S2_COUNT (应为 477)"
echo "  S1 tar 文件数: $S1_COUNT (应为 477)"

if [ "$S2_COUNT" -eq 477 ] && [ "$S1_COUNT" -eq 477 ]; then
    echo "  ✅ 数据完整"
else
    echo "  ⚠️  文件数不对,请检查"
fi

echo ""
echo "配置文件中的 data_root 应指向: $SHM_ROOT"
echo "训练完成后清理: bash scripts/cleanup_staged_data.sh"
echo "============================================================"
