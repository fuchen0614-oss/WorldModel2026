#!/usr/bin/env bash
# plan-b-pvt · stage GreenEarthNet train+val to local disk, then train from it.
#
# Copies the tracks the trainer reads (train + val_chopped) from the shared CPFS
# ($DATA_GEN) to a local disk ($LOCAL_STAGE, default /tmp), then launches
# scripts/train_plan_b_ctx.sh pointed at the local copy. Reused across runs:
# if a track is already fully staged (same .nc count), its rsync is skipped, so
# the first B0 pays the copy once and every later B1-B4 run starts instantly.
#
# Usage (server; all training env-vars pass through to train_plan_b_ctx.sh):
#   conda activate WorldModel
#   export DATA_GEN=/csy-mix02/cog8/zjliu17/Agent/TrainData/GreenEarthNet
#   OUTPUT_DIR=checkpoints/plan_b_b0 nohup bash scripts/stage_and_train_plan_b.sh >/dev/null 2>&1 &
#   tail -f $OUTPUT_DIR/train.log   # (staging progress prints to stdout->/dev/null; see stage.log)
set -euo pipefail

SRC="${DATA_GEN:?set DATA_GEN to the shared GreenEarthNet root}"
LOCAL_STAGE="${LOCAL_STAGE:-/tmp/${USER}_gen_stage}"
STAGE_TRACKS="${STAGE_TRACKS:-train val_chopped}"
MIN_FREE_GB="${MIN_FREE_GB:-260}"
OUTPUT_DIR="${OUTPUT_DIR:-checkpoints/plan_b_b0}"
STAGE_LOG="${STAGE_LOG:-$OUTPUT_DIR/stage.log}"
mkdir -p "$OUTPUT_DIR" "$LOCAL_STAGE"

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$STAGE_LOG"; }

# free-space guard on the target filesystem
avail_gb=$(df -BG --output=avail "$LOCAL_STAGE" 2>/dev/null | tail -1 | tr -dc '0-9' || echo 0)
log "stage target=$LOCAL_STAGE  free=${avail_gb}G  (need >= ${MIN_FREE_GB}G)"
if [ "${avail_gb:-0}" -lt "$MIN_FREE_GB" ]; then
  log "ERROR: not enough local free space (${avail_gb}G < ${MIN_FREE_GB}G). Set MIN_FREE_GB lower or free space."
  exit 1
fi

for t in $STAGE_TRACKS; do
  src_n=$(find "$SRC/$t" -name '*.nc' 2>/dev/null | wc -l)
  loc_n=$(find "$LOCAL_STAGE/$t" -name '*.nc' 2>/dev/null | wc -l || echo 0)
  if [ "$src_n" -gt 0 ] && [ "$src_n" -eq "$loc_n" ]; then
    log "SKIP $t: already staged ($loc_n == $src_n .nc)"
    continue
  fi
  log "staging $t: src=$src_n local=$loc_n -> copying ..."
  mkdir -p "$LOCAL_STAGE/$t"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --info=progress2 "$SRC/$t/" "$LOCAL_STAGE/$t/" 2>&1 | tee -a "$STAGE_LOG"
  else
    log "rsync not found; falling back to cp -a"
    cp -a "$SRC/$t/." "$LOCAL_STAGE/$t/"
  fi
  new_n=$(find "$LOCAL_STAGE/$t" -name '*.nc' 2>/dev/null | wc -l)
  log "staged $t: local now=$new_n"
  [ "$new_n" -eq "$src_n" ] || { log "ERROR: $t count mismatch (src=$src_n local=$new_n)"; exit 1; }
done

log "=== all tracks staged to $LOCAL_STAGE; launching training from local disk ==="
DATA_GEN="$LOCAL_STAGE" bash scripts/train_plan_b_ctx.sh
