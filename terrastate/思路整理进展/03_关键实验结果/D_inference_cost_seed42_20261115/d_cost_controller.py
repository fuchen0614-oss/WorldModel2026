import json,subprocess,os,time,fcntl,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());f=(R/'controller.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
def put(s):
 s.update(pid=os.getpid(),time=time.time());p=R/'state.tmp';p.write_text(json.dumps(s));p.replace(R/'state.json')
try:
 start=time.time()
 while True:
  busy=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
  available=[g for g in P['gpu_candidates'] if g not in busy]
  if available:
   P['gpu_uuid']=available[0];(R/'plan.json').write_text(json.dumps(P,indent=2));break
  put({'status':'waiting_for_exclusive_gpu','gpu_uuid':P['gpu_uuid'],'wait_seconds':time.time()-start})
  if time.time()-start>21600:raise RuntimeError('six-hour exclusive GPU wait expired; no other process stopped')
  time.sleep(180)
 env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuid'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 with (R/'worker.log').open('ab') as log:
  q=subprocess.Popen([P['python'],str(R/'worker.py')],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT);put({'status':'running','worker_pid':q.pid});rc=q.wait()
 (R/'exit.json').write_text(json.dumps({'exit':rc,'pid':q.pid,'time':time.time()}));assert rc==0,rc;assert json.loads((R/'result.json').read_text())['status']=='PASS';put({'status':'complete','real_exit':rc})
except BaseException:put({'status':'failed','error':traceback.format_exc()});raise
