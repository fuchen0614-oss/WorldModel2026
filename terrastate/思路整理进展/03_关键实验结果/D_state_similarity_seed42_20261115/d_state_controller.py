import json,time,subprocess,os,fcntl,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());lock=(R/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def put(x):
 x.update(pid=os.getpid(),time=time.time());p=R/'state.tmp';p.write_text(json.dumps(x));p.replace(R/'state.json')
try:
 put({'status':'waiting_for_memory','run_id':R.name});start=time.time()
 while True:
  free=int(subprocess.check_output(['nvidia-smi','-i',P['gpu_uuid'],'--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
  if free>=10000:break
  if time.time()-start>43200:raise RuntimeError('bounded resource wait expired')
  time.sleep(60)
 env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuid'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 with (R/'worker.log').open('ab') as f:
  q=subprocess.Popen([P['python'],str(R/'worker.py')],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
  put({'status':'running','worker_pid':q.pid,'run_id':R.name});rc=q.wait()
 (R/'exit.json').write_text(json.dumps({'exit':rc,'worker_pid':q.pid,'time':time.time()}));assert rc==0,rc;assert json.loads((R/'result.json').read_text())['status']=='PASS';put({'status':'complete','real_exit':rc})
except BaseException:put({'status':'failed','error':traceback.format_exc()});raise
