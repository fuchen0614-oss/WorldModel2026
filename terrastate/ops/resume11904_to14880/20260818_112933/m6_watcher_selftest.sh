#!/usr/bin/env bash
# M6 self-test for gpu_watcher.sh. Runs in an ISOLATED copy dir so the real watcher log,
# lock and READY file are never touched. Read-only w.r.t. GPUs; signals only PIDs it creates.
#
#   A busy detection resets the streak        D stale streak discarded
#   B streak resume + valid READY             E deadline bound, exits without launching
#   C idempotent (READY not rewritten)        F flock: refuse while held, acquire after release
#   G TERM leaves no orphan and no lock holder, immediate restart works
#
# Exit 0 = all pass.
set -uo pipefail
OPS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=/csy-opt/cog8/zjliu17/miniconda3/envs/WorldModel/bin/python
T="$OPS/m6_selftest"
rm -rf "$T"; mkdir -p "$T"; cp "$OPS/gpu_watcher.sh" "$T/"
cd "$T" || exit 1
PASS=0; FAIL=0
ok(){ echo "  PASS $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1"; FAIL=$((FAIL+1)); }
last(){ $PY -c "
import json,sys
print(json.loads(open('m6_watcher.jsonl').read().strip().split(chr(10))[-1])[sys.argv[1]])" "$1"; }

echo "=== A: busy detection resets streak ==="
MEM_MAX_MIB=1 ./gpu_watcher.sh --once >a.log 2>&1; rc=$?
[ "$rc" -eq 5 ] && [ "$(last idle)" = "False" ] && [ "$(last streak)" = "0" ] \
  && ok "A busy -> rc=5, idle=false, streak=0" || no "A rc=$rc idle=$(last idle) streak=$(last streak)"

echo "=== B: streak resume 9->10 writes valid READY ==="
rm -f m6_watcher.jsonl m6_gpu_ready.json
$PY -c "
import json,time
print(json.dumps({'poll':9,'utc':'x','epoch':int(time.time())-30,'idle':True,'streak':9,
 'need':10,'n_gpu':8,'n_compute_apps':0,'reason':'','gpus':[],'compute_apps':[]}))" >m6_watcher.jsonl
./gpu_watcher.sh --once >b.log 2>&1; rc=$?
if [ "$rc" -eq 0 ] && [ -f m6_gpu_ready.json ] && $PY -c "
import json,sys; d=json.load(open('m6_gpu_ready.json'))
sys.exit(0 if (d['ready'] and d['consecutive_idle']==10 and d['n_gpu']==8
               and d['bar']['mem_used_mib_lt']==1024 and d['bar']['util_pct_lt']==5) else 1)"; then
  ok "B streak resumed, READY valid (10 consecutive, 8 GPUs, bar intact)"
else no "B rc=$rc"; fi

echo "=== C: idempotent, READY not rewritten ==="
b4=$(md5sum m6_gpu_ready.json | cut -d' ' -f1)
./gpu_watcher.sh --once >c.log 2>&1; rc=$?
[ "$rc" -eq 0 ] && [ "$b4" = "$(md5sum m6_gpu_ready.json | cut -d' ' -f1)" ] \
  && grep -q "M7 must still re-verify" c.log && ok "C READY untouched, re-verify note emitted" || no "C rc=$rc"

echo "=== D: stale streak discarded, no premature READY ==="
rm -f m6_gpu_ready.json m6_watcher.jsonl
$PY -c "
import json,time
print(json.dumps({'poll':9,'utc':'x','epoch':int(time.time())-100000,'idle':True,'streak':9,
 'need':10,'n_gpu':8,'n_compute_apps':0,'reason':'','gpus':[],'compute_apps':[]}))" >m6_watcher.jsonl
./gpu_watcher.sh --once >d.log 2>&1
grep -q "discarding stale streak=9" d.log && [ "$(last streak)" = "1" ] && [ ! -f m6_gpu_ready.json ] \
  && ok "D stale discarded, streak=1, no READY" || no "D streak=$(last streak) ready=$([ -f m6_gpu_ready.json ] && echo yes || echo no)"

echo "=== E: deadline bound ==="
rm -f m6_watcher.jsonl
MAX_HOURS=0 ./gpu_watcher.sh >e.log 2>&1; rc=$?
[ "$rc" -eq 4 ] && $PY -c "
import json,sys; d=json.load(open('m6_watcher_timeout.json'))
sys.exit(0 if d['deadline_reached'] else 1)" && ok "E rc=4, timeout record, nothing launched" || no "E rc=$rc"

echo "=== F: flock refuse-while-held then acquire-after-release ==="
rm -f m6_watcher.jsonl m6_gpu_ready.json m6_watcher_timeout.json
INTERVAL_S=120 nohup ./gpu_watcher.sh >f_holder.log 2>&1 &
H=$!; HPGID=$(ps -o pgid= -p $H | tr -d ' '); sleep 4
holders=$(fuser .gpu_watcher.lock 2>/dev/null | tr -s ' ' | wc -w)
./gpu_watcher.sh --once >f_second.log 2>&1; rc2=$?
kill -TERM $H 2>/dev/null; sleep 2
kill -0 $H 2>/dev/null && kill -KILL $H 2>/dev/null
wait $H 2>/dev/null
sleep 1
./gpu_watcher.sh --once >f_third.log 2>&1; rc3=$?
[ "$rc2" -eq 3 ] && [ "$rc3" -eq 0 ] && [ "$holders" -eq 1 ] \
  && ok "F refused while held (3), acquired after release (0), single fd-9 holder" \
  || no "F rc2=$rc2 rc3=$rc3 holders=$holders"

echo "=== G: TERM leaves no orphan, no lock holder, restart works ==="
rm -f m6_watcher.jsonl m6_gpu_ready.json
INTERVAL_S=120 nohup ./gpu_watcher.sh >g_holder.log 2>&1 &
H=$!
sleep 4
kill -TERM $H 2>/dev/null; sleep 2
wait $H 2>/dev/null
sleep 1
# PID-SPECIFIC, deliberately not a PGID scan: this driver is non-interactive, so job control is
# off and the backgrounded holder shares the DRIVER's PGID. A `$2==pgid && /sleep/` scan would
# therefore also match the driver's own `sleep 4`/`sleep 2` and any earlier test's children --
# that false positive is exactly what made an earlier revision of this test fail while the
# watcher was in fact reaping correctly. Only the exact PID the watcher recorded is evidence.
rpid=$(grep -o "sleep child [0-9]*" g_holder.log | tail -1 | awk '{print $3}')
if [ -n "$rpid" ] && kill -0 "$rpid" 2>/dev/null; then orph=1; else orph=0; fi
kids=$(ps -o pid= --ppid "$H" 2>/dev/null | grep -c . || true)
lockheld=$(fuser .gpu_watcher.lock 2>/dev/null | tr -s ' ' | wc -w)
./gpu_watcher.sh --once >g_restart.log 2>&1; rc=$?
if grep -q "reaping only my own sleep child" g_holder.log \
   && [ -n "$rpid" ] && [ "$orph" -eq 0 ] && [ "$kids" -eq 0 ] \
   && [ "$lockheld" -eq 0 ] && [ "$rc" -eq 0 ]; then
  ok "G reaped its own sleep $rpid, no surviving child, no lock holder, restart rc=0"
else
  no "G rpid=${rpid:-none} sleep_alive=$orph kids=$kids lockheld=$lockheld restart_rc=$rc"
  echo "    --- sleeps alive under $(id -un) at failure time ---"
  ps -u "$(id -un)" -o pid,ppid,pgid,cmd 2>/dev/null | grep -E "sleep [0-9]+" | grep -v grep
fi

echo
echo "M6 SELFTEST: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
