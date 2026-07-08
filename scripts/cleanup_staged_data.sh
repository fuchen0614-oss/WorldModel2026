#!/bin/bash
# ============================================================
# 清理混合存储的临时数据副本
# ============================================================
# 删除的是 /dev/shm 和 /tmp 里的【临时副本】。
# 你的原始数据集 /csy-mix02/.../TrainData/SSL4EO-S12-v1.1 一字不动。
#
# 用法:
#   bash scripts/cleanup_staged_data.sh         # 交互确认后删
#   bash scripts/cleanup_staged_data.sh --force  # 直接删(脚本自动调用)
# ============================================================

SHM_DIR=/dev/shm/zjliu17_ssl4eo
TMP_DIR=/tmp/zjliu17_ssl4eo
SRC=/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1

echo "============================================================"
echo "清理混合存储临时副本"
echo "============================================================"
echo "将删除(临时副本):"
echo "  $SHM_DIR  ($(du -sh $SHM_DIR 2>/dev/null | cut -f1 || echo '不存在'))"
echo "  $TMP_DIR  ($(du -sh $TMP_DIR 2>/dev/null | cut -f1 || echo '不存在'))"
echo ""
echo "绝不删除(你的原始数据集,永久保留):"
echo "  $SRC"
echo "============================================================"

# 安全校验:确认要删的不是源数据
for d in "$SHM_DIR" "$TMP_DIR"; do
  case "$d" in
    /csy-mix02/*|/csy-home02/*|"$SRC"*)
      echo "[拒绝] $d 看起来是源/工作目录,绝不删除!"
      exit 1
      ;;
  esac
done

if [ "$1" != "--force" ]; then
  read -p "确认删除以上临时副本? (yes/no): " ans
  if [ "$ans" != "yes" ]; then
    echo "已取消,未删除任何东西。"
    exit 0
  fi
fi

rm -rf "$SHM_DIR"
rm -rf "$TMP_DIR"
rm -f /tmp/_copy_s1.done /tmp/_copy_s2.done /tmp/_copy_s1.log /tmp/_copy_s2.log

echo ""
echo "✓ 已清理临时副本。原始数据集完好:"
echo "  $SRC  ($(ls $SRC/train/S2L2A/*.tar 2>/dev/null | wc -l) 个 S2 shard 仍在)"
echo ""
echo "运存/本地盘已释放:"
df -h /dev/shm /tmp | grep -E "shm|sda3|Filesystem"
