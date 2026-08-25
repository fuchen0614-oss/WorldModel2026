#!/usr/bin/env bash
# M6: safe, single-instance GPU idle watcher for the TerraState 11,904 -> 14,880 resume.
#
# What it does .......... read-only nvidia-smi polling until ALL 8 GPUs are stably idle, then
#                        writes m6_gpu_ready.json and exits.
# What it never does .... launch training; kill/pause/renice/migrate any PID; sudo; change
#                        MIG/clock/power/persistence; accept a subset of GPUs; lower the bar.
#
# Idle (must hold for EVERY one of the 8 GPUs, 10 consecutive times):
#     memory.used < 1024 MiB   AND   utilization.gpu < 5 %
# 10 consecutive passes at 60 s == >= 10 minutes of uninterrupted idleness.
#
# Any doubt counts as NOT idle and resets the streak to 0: nvidia-smi non-zero exit, timeout,
# an unparseable row, or a GPU count other than 8. Never optimistically assume availability.
#
# Foreign compute processes are RECORDED for the report and never acted upon.
#
# Usage:  gpu_watcher.sh [--once]
# Exit :  0 ready / already ready · 1 fatal · 3 another instance holds the lock
#         · 4 deadline reached · 5 (--once) not idle right now

set -uo pipefail

OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK="$OPS/.gpu_watcher.lock"
JSONL="$OPS/m6_watcher.jsonl"
READY="$OPS/m6_gpu_ready.json"
TIMEOUT_F="$OPS/m6_watcher_timeout.json"

EXPECT_GPUS="${EXPECT_GPUS:-8}"
MEM_MAX_MIB="${MEM_MAX_MIB:-1024}"
UTIL_MAX_PCT="${UTIL_MAX_PCT:-5}"
NEED_STREAK="${NEED_STREAK:-10}"
INTERVAL_S="${INTERVAL_S:-60}"
SMI_TIMEOUT="${SMI_TIMEOUT:-20}"     # guard against a hung nvidia-smi (never block forever)
MAX_HOURS="${MAX_HOURS:-72}"         # bounded so this process can never leak indefinitely

ONCE=0
[ "${1:-}" = "--once" ] && ONCE=1

ts_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say()    { printf '%s %s\n' "$(ts_now)" "$*"; }

# ---- shutdown: reap ONLY my own sleep child -------------------------------------------------
# Without this, terminating the watcher leaves its `sleep` child orphaned (PPID 1) for up to
# one interval. It holds no lock and exits on its own, but an untracked process of mine is not
# acceptable: I may only manage processes I created and whose PID I recorded. So the sleep runs
# in the background with its PID captured, and this trap signals that PID and nothing else --
# never a process group, never a foreign PID.
SLEEP_PID=""
on_signal() {
  local sig="$1"
  say "signal $sig received -- shutting down; reaping only my own sleep child ${SLEEP_PID:-none}"
  if [ -n "$SLEEP_PID" ] && kill -0 "$SLEEP_PID" 2>/dev/null; then
    kill -TERM "$SLEEP_PID" 2>/dev/null
  fi
  say "watcher stopped without launching anything"
  exit 143
}
trap 'on_signal TERM' TERM
trap 'on_signal INT'  INT
trap 'on_signal HUP'  HUP

# ---- single instance ----------------------------------------------------------------------
# flock on a file inside MY OWN ops dir: never a shared or system-wide lock path, and no
# foreign lock is ever inspected, waited on, or removed.
#
# fd 9 MUST NOT leak into children. bash has no CLOEXEC for redirections, so any child that
# can outlive this shell (`sleep`, a hung `nvidia-smi`) would keep the lock held after the
# watcher dies and would then refuse a legitimate restart for up to a full poll interval.
# Every such child is therefore spawned with `9>&-`. (Verified by self-test F.)
exec 9>"$LOCK" || { say "FATAL cannot open lock $LOCK"; exit 1; }
if ! flock -n 9; then
  say "another watcher instance already holds $LOCK -- exiting (single-instance rule)"
  exit 3
fi
printf '%s pid=%s pgid=%s argv=%s\n' "$(ts_now)" "$$" \
  "$(ps -o pgid= -p $$ | tr -d ' ')" "${*:-<none>}" >> "$OPS/m6_watcher.pid"

# ---- idempotent: an existing READY record is not rewritten ---------------------------------
if [ -f "$READY" ]; then
  say "READY already recorded at $READY -- nothing to do (idempotent)"
  say "NOTE M7 must still re-verify occupancy immediately before launching."
  exit 0
fi

# ---- resumable: recover the streak only if the last poll is recent -------------------------
STREAK=0
if [ -s "$JSONL" ]; then
  last_line="$(tail -n 1 "$JSONL")"
  last_streak="$(printf '%s' "$last_line" | sed -n 's/.*"streak":[ ]*\([0-9]*\).*/\1/p')"
  last_epoch="$(printf '%s' "$last_line" | sed -n 's/.*"epoch":[ ]*\([0-9]*\).*/\1/p')"
  now_epoch="$(date -u +%s)"
  if [ -n "$last_streak" ] && [ -n "$last_epoch" ]; then
    gap=$(( now_epoch - last_epoch ))
    # A streak only means "uninterrupted", so it may be carried over solely across a gap
    # shorter than one poll window plus slack. Anything longer is unobserved time -> restart.
    if [ "$gap" -le $(( INTERVAL_S * 3 )) ]; then
      STREAK="$last_streak"
      say "resuming with streak=$STREAK (last poll ${gap}s ago)"
    else
      say "discarding stale streak=$last_streak (last poll ${gap}s ago > $(( INTERVAL_S * 3 ))s): unobserved time is not idle time"
    fi
  fi
fi

say "watcher start pid=$$ need=${NEED_STREAK}x${INTERVAL_S}s gpus=$EXPECT_GPUS mem<${MEM_MAX_MIB}MiB util<${UTIL_MAX_PCT}% deadline=${MAX_HOURS}h"

DEADLINE=$(( $(date -u +%s) + MAX_HOURS * 3600 ))
POLL=0

while :; do
  POLL=$(( POLL + 1 ))
  NOW_EPOCH="$(date -u +%s)"
  NOW_ISO="$(ts_now)"

  if [ "$NOW_EPOCH" -ge "$DEADLINE" ]; then
    say "DEADLINE ${MAX_HOURS}h reached without ${NEED_STREAK} consecutive idle polls -- exiting without launching"
    printf '{"deadline_reached":true,"utc":"%s","polls":%d,"final_streak":%d,"needed":%d,"note":"GPUs never reached the required stable-idle bar; the bar was NOT lowered and no training was started"}\n' \
      "$NOW_ISO" "$POLL" "$STREAK" "$NEED_STREAK" > "$TIMEOUT_F"
    exit 4
  fi

  # read-only query; -T bounds a hung driver/NFS call
  SMI="$(timeout -k 5 "$SMI_TIMEOUT" nvidia-smi \
        --query-gpu=index,memory.used,utilization.gpu,memory.total,name \
        --format=csv,noheader,nounits 2>&1 9>&-)"
  SMI_RC=$?

  IDLE=1; REASON=""; NGPU=0; GPUJSON=""
  if [ "$SMI_RC" -ne 0 ]; then
    IDLE=0; REASON="nvidia-smi rc=$SMI_RC: $(printf '%s' "$SMI" | head -c 160 | tr '\n"' '  ')"
  else
    while IFS=, read -r idx mem util memtot gname; do
      idx="${idx// /}"; mem="${mem// /}"; util="${util// /}"; memtot="${memtot// /}"
      gname="$(printf '%s' "$gname" | sed 's/^ *//; s/ *$//')"
      [ -z "$idx" ] && continue
      NGPU=$(( NGPU + 1 ))
      # a non-numeric field (e.g. "[N/A]") is uncertainty -> treat as busy
      if ! printf '%s' "$mem"  | grep -qE '^[0-9]+$' || \
         ! printf '%s' "$util" | grep -qE '^[0-9]+$'; then
        IDLE=0; REASON="${REASON}gpu${idx}:unparseable(mem=$mem,util=$util) "
        mem="${mem:-null}"; util="${util:-null}"
      else
        if [ "$mem"  -ge "$MEM_MAX_MIB"  ]; then IDLE=0; REASON="${REASON}gpu${idx}:mem=${mem}MiB "; fi
        if [ "$util" -ge "$UTIL_MAX_PCT" ]; then IDLE=0; REASON="${REASON}gpu${idx}:util=${util}% "; fi
      fi
      GPUJSON="${GPUJSON}${GPUJSON:+,}{\"i\":${idx},\"mem_used_mib\":\"${mem}\",\"util_pct\":\"${util}\",\"mem_total_mib\":\"${memtot}\",\"name\":\"${gname}\"}"
    done <<< "$SMI"
    if [ "$NGPU" -ne "$EXPECT_GPUS" ]; then
      IDLE=0; REASON="${REASON}gpu_count=${NGPU}!=${EXPECT_GPUS} "
    fi
  fi

  # Foreign compute processes: RECORDED ONLY. Never signalled, never renice'd, never migrated.
  PROCS="$(timeout -k 5 "$SMI_TIMEOUT" nvidia-smi \
          --query-compute-apps=pid,used_memory,gpu_uuid --format=csv,noheader,nounits 2>/dev/null 9>&- \
          | sed 's/^ *//; s/ *$//' | grep -v '^$' | head -40)"
  NPROC=0; PROCJSON=""
  if [ -n "$PROCS" ]; then
    while IFS=, read -r ppid pmem puuid; do
      ppid="${ppid// /}"; pmem="${pmem// /}"; puuid="$(printf '%s' "$puuid" | sed 's/^ *//; s/ *$//')"
      [ -z "$ppid" ] && continue
      NPROC=$(( NPROC + 1 ))
      pown="$(ps -o user= -p "$ppid" 2>/dev/null | tr -d ' ')"
      pcmd="$(ps -o comm= -p "$ppid" 2>/dev/null | tr -d ' ')"
      PROCJSON="${PROCJSON}${PROCJSON:+,}{\"pid\":${ppid},\"used_mib\":\"${pmem}\",\"user\":\"${pown:-unknown}\",\"comm\":\"${pcmd:-unknown}\",\"gpu_uuid\":\"${puuid}\"}"
    done <<< "$PROCS"
    IDLE=0
    REASON="${REASON}compute_apps=${NPROC} "
  fi

  if [ "$IDLE" -eq 1 ]; then STREAK=$(( STREAK + 1 )); else STREAK=0; fi

  printf '{"poll":%d,"utc":"%s","epoch":%d,"idle":%s,"streak":%d,"need":%d,"n_gpu":%d,"n_compute_apps":%d,"reason":"%s","gpus":[%s],"compute_apps":[%s]}\n' \
    "$POLL" "$NOW_ISO" "$NOW_EPOCH" "$([ "$IDLE" -eq 1 ] && echo true || echo false)" \
    "$STREAK" "$NEED_STREAK" "$NGPU" "$NPROC" \
    "$(printf '%s' "$REASON" | sed 's/ *$//')" "$GPUJSON" "$PROCJSON" >> "$JSONL"

  if [ "$IDLE" -eq 1 ]; then
    say "poll $POLL: ALL $NGPU GPUs idle -- streak $STREAK/$NEED_STREAK"
  else
    say "poll $POLL: NOT idle (streak reset) -- $REASON"
  fi

  if [ "$STREAK" -ge "$NEED_STREAK" ]; then
    say "STABLE IDLE CONFIRMED: $NEED_STREAK consecutive passes (>= $(( NEED_STREAK * INTERVAL_S / 60 )) min)"
    printf '{"ready":true,"utc":"%s","epoch":%d,"polls":%d,"consecutive_idle":%d,"interval_s":%d,"stable_minutes":%d,"n_gpu":%d,"bar":{"mem_used_mib_lt":%d,"util_pct_lt":%d},"gpus":[%s],"note":"read-only detection; this watcher does NOT launch training. M7 must re-verify occupancy immediately before launch."}\n' \
      "$NOW_ISO" "$NOW_EPOCH" "$POLL" "$STREAK" "$INTERVAL_S" \
      "$(( NEED_STREAK * INTERVAL_S / 60 ))" "$NGPU" "$MEM_MAX_MIB" "$UTIL_MAX_PCT" "$GPUJSON" > "$READY"
    say "wrote $READY"
    exit 0
  fi

  if [ "$ONCE" -eq 1 ]; then
    say "--once: single poll done (idle=$IDLE), no waiting"
    [ "$IDLE" -eq 1 ] && exit 0 || exit 5
  fi

  # 9>&- : do not hand the lock fd to a 60 s child, or an orphaned `sleep` outlives the
  # watcher still holding the flock and blocks the next legitimate start (self-test F).
  # Backgrounded + `wait` so the trap can fire immediately on TERM and reap this exact PID
  # instead of leaving it orphaned for up to one interval.
  sleep "$INTERVAL_S" 9>&- &
  SLEEP_PID=$!
  wait "$SLEEP_PID" 2>/dev/null
  SLEEP_PID=""
done
