from pathlib import Path
import json,subprocess,os,time,fcntl
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());lock=(R/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);running={};done=[]
for v,slot in [('D',0),('B',1)]:
 f=(R/(v+'.log')).open('ab');env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuids'][slot],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');q=subprocess.Popen([P['python'],str(R/'worker.py'),'--variant',v],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);running[v]=q
while running:
 for v,q in list(running.items()):
  if q.poll() is not None:
   (R/(v+'_exit.json')).write_text(json.dumps({'pid':q.pid,'exit':q.returncode,'time':time.time()}));done.append({'variant':v,'exit':q.returncode});del running[v]
 p=R/'state.tmp';p.write_text(json.dumps({'pid':os.getpid(),'time':time.time(),'running':{v:q.pid for v,q in running.items()},'finished':done,'status':'running' if running else 'complete' if all(d['exit']==0 for d in done) else 'failed'}));p.replace(R/'state.json');time.sleep(5)
