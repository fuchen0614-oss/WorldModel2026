import os,sys,json,time,subprocess,fcntl,traceback
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());S=Path(P['six_runtime']);PY=P['python'];lk=(R/'controller.lock').open('a');fcntl.flock(lk,fcntl.LOCK_EX|fcntl.LOCK_NB)
env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuid'],OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
def put(n,v):
 p=R/n;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def call(script,args,label):
 cmd=[PY,'-B',str(R/script),str(R)]+args
 with (R/(label+'.log')).open('ab') as f:
  p=subprocess.Popen(cmd,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
  put('state.json',dict(status=label,pid=os.getpid(),child_pid=p.pid,command=cmd,time=time.time()));rc=p.wait()
 put(label+'_exit.json',dict(pid=p.pid,exit=rc,time=time.time()))
 if rc:raise RuntimeError(label+' exit '+str(rc))
try:
 put('resource_lease.json',dict(status='registered',pid=os.getpid(),gpu_uuid=P['gpu_uuid'],guard_recognition_prefix=P['guard_recognition_prefix'],time=time.time()))
 call('selection.py',[],'selection_preflight')
 call('worker.py',['first_sample'],'first_sample')
 put('state.json',dict(status='queued_after_six_suffix_worker',pid=os.getpid(),first_sample_pass=True,first_sample=str(R/'first_sample.json'),waiting_for=str(S/'worker_exit.json'),time=time.time()))
 deadline=time.monotonic()+12*3600
 while not (S/'worker_exit.json').exists():
  if time.monotonic()>deadline:raise TimeoutError('six suffix prerequisite did not complete')
  time.sleep(30)
 x=json.loads((S/'worker_exit.json').read_text());assert x['exit']==0,'six suffix failed; preserve original failure'
 # Receipt is written immediately before process exit; wait for actual worker exit too.
 initial=json.loads((S/'first_sample.json').read_text());pid=initial['pid']
 while Path('/proc',str(pid)).exists():
  if time.monotonic()>deadline:raise TimeoutError('six suffix worker has not exited')
  time.sleep(2)
 call('worker.py',['remaining'],'consistency_suffix')
 call('assemble.py',[],'assemble_AB')
 put('state.json',dict(status='complete',exit=0,pid=os.getpid(),receipt=str(R/'tables/receipt.json'),time=time.time()))
 put('resource_lease.json',dict(status='released_after_worker_exit',gpu_uuid=P['gpu_uuid'],time=time.time()))
except BaseException:
 put('state.json',dict(status='failed',exit=1,pid=os.getpid(),error=traceback.format_exc(),time=time.time()));raise
