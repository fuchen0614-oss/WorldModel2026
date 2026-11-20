import os,json,time,subprocess,traceback,hashlib,msvcrt,gzip,base64
from pathlib import Path
W=Path(__file__).resolve().parent;R=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展');O=R/'03_关键实验结果/BD_原稿全表复刻_20261115';C=O/'E1_20min_collector';C.mkdir(exist_ok=True)
lock=(C/'collector.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
wrapper=R.parent/'releases/spanworld_v2/efficiency_v1_20261113/c0r_prepared/handoff_909D_916B_20261113/completion_chains_20261114/ssh_task.py'
analysis_python=Path(r'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe')
def state(x):
 p=C/'state.tmp';p.write_text(json.dumps({'pid':os.getpid(),'time':time.time(),'interval_seconds':600,'priority':'D then B','scope':'BD E1 evidence collection, gated statistics and A50/A51+A08 publication',**x},ensure_ascii=False,indent=2),encoding='utf-8');p.replace(C/'state.json')
state({'status':'starting'})
while True:
 cycle_start=time.monotonic()
 try:
  report=C/'remote_latest.json';env=dict(os.environ,PYTHONUTF8='1')
  started=time.time();q=subprocess.run([os.sys.executable,str(wrapper),'909',str(W/'bd_e1_collect_remote.py'),str(report)],cwd=W.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=400)
  assert report.stat().st_mtime>=started-2,'stale SSH receipt'
  outer=json.loads(report.read_text(encoding='utf-8-sig'));assert outer['exit']==0,outer.get('stderr','SSH failed');s=json.loads(outer['stdout'])
  for key,obj in s['outputs'].items():
   raw=gzip.decompress(base64.b64decode(obj.pop('gzip_base64')));assert hashlib.sha256(raw).hexdigest()==obj['result']['csv_sha256']
   d=C/key;d.mkdir(parents=True,exist_ok=True);p=d/'paired_per_horizon.csv'
   if p.exists():assert p.read_bytes()==raw
   else:p.write_bytes(raw)
   (d/'receipt.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
  (C/'snapshot.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
  q=subprocess.run([str(analysis_python),str(W/'bd_e1_statistics.py')],env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
  (C/'statistics_latest.log').write_text(q.stdout+q.stderr,encoding='utf-8');assert q.returncode==0,q.stderr[-2500:]
  publication=json.loads(q.stdout);done=publication['complete']
  inference_done=s['state']['status']=='complete' and len(s['outputs'])==8
  blocked=s['state']['status']=='failed' or not s['controller_alive'] and not inference_done
  recovery=None
  if blocked and not s['controller_alive'] and s['state']['status']!='failed':
   history=C/'recovery_attempts.json';attempts=json.loads(history.read_text(encoding='utf-8')) if history.exists() else []
   if len(attempts)<2:
    rp=C/('recovery_'+str(len(attempts)+1)+'.json');attempts.append({'time':time.time(),'receipt':str(rp)})
    history.write_text(json.dumps(attempts,indent=2),encoding='utf-8')
    subprocess.run([os.sys.executable,str(wrapper),'909',str(W/'e1_resume_deploy.py'),str(rp)],cwd=W.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=400)
    recovery=json.loads(rp.read_text(encoding='utf-8-sig'))
    if recovery['exit']==0:
     rr=json.loads(recovery['stdout']);blocked=rr['exit'] is not None
  state({'status':'complete_published' if done else 'blocked' if blocked else 'running','remote_state':s['state'],'recovery':recovery,'collected_splits':list(s['outputs']),'published':publication['published'],'inspection_stopped':done or blocked,'remaining':'E1 complete; A1/F1/H1 still separate pending work' if done else 'finish E1 inference and gated publication'})
  if done or blocked:break
 except Exception:state({'status':'connection_or_collection_error_retry_next_cycle','error':traceback.format_exc(),'inspection_stopped':False})
 time.sleep(max(1,600-(time.monotonic()-cycle_start)))
