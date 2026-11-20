import os,sys,json,time,subprocess,fcntl,traceback
from pathlib import Path
R=Path(sys.argv[1]);lock=(R/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
P=json.loads((R/'plan.json').read_text());PY=P['python']
def put(n,v):
 p=R/n;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def call(cmd,label):
 with (R/(label+'.log')).open('ab') as log:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=R,env=env)
  put('state.json',dict(status=label,pid=os.getpid(),child_pid=p.pid,command=cmd,time=time.time()))
  rc=p.wait()
 put(label+'_exit.json',dict(exit=rc,pid=p.pid,time=time.time()))
 if rc:raise RuntimeError(label+' exit '+str(rc))
env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuid'],OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
try:
 put('resource_lease.json',dict(status='active',gpu_uuid=P['gpu_uuid'],owner_pid=os.getpid(),guard_recognition_prefix=P['guard_recognition_prefix'],purpose='seed42 paired suffix; no standard reinference',time=time.time()))
 call([PY,'-B',str(R/'worker.py'),str(R)],'suffix_inference')
 put('resource_lease.json',dict(status='gpu_worker_exited',gpu_uuid=P['gpu_uuid'],time=time.time()))
 call([PY,'-B',str(R/'paper/code/suffix_statistics.py'),'--suffix-dir',str(R/'suffix'),'--out',str(R/'statistics'),'--bootstrap'],'statistics')
 call([PY,'-B',str(R/'assemble.py'),str(R)],'assemble_tables')
 put('state.json',dict(status='complete',exit=0,pid=os.getpid(),receipt=str(R/'tables/receipt.json'),time=time.time()))
except BaseException:
 put('state.json',dict(status='failed',exit=1,pid=os.getpid(),error=traceback.format_exc(),time=time.time()));raise
