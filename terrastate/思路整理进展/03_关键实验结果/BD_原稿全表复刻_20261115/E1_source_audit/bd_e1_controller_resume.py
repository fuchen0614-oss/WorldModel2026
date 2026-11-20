import sys,os,json,time,subprocess,fcntl,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());L=(R/'controller.lock').open('a');fcntl.flock(L,fcntl.LOCK_EX|fcntl.LOCK_NB);tasks=[(v,s) for v in ['B','D'] for s in P['splits'] if not (R/v/s/'result.json').exists()];running={};completed=[(v,s) for v in ['B','D'] for s in P['splits'] if (R/v/s/'result.json').exists()];S={'pid':os.getpid(),'status':'starting_first_protocol_gate'}
def put():
 S.update(time=time.time(),running={str(k):{'pid':q.pid,'slot':slot} for k,(q,slot) in running.items()},completed=completed,pending=tasks);p=R/'state.tmp';p.write_text(json.dumps(S));p.replace(R/'state.json')
def launch(job,slot):
 v,s=job;e=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuids'][slot],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1');f=(R/(v+'_'+s+'.log')).open('ab');q=subprocess.Popen([P['python'],str(R/'worker_resume.py'),'--plan',str(R/'plan.json'),'--variant',v,'--split',s],cwd=R,env=e,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);running[job]=(q,slot)
try:
 launch(tasks.pop(0),0);put();gate=False
 while tasks or running:
  for job,(q,slot) in list(running.items()):
   d=R/job[0]/job[1]
   if (d/'protocol_PASS.json').exists():gate=True
   if q.poll() is not None:
    (R/(job[0]+'_'+job[1]+'_exit.json')).write_text(json.dumps({'exit':q.returncode,'pid':q.pid,'time':time.time()}));assert q.returncode==0,(job,q.returncode)
    assert json.loads((d/'result.json').read_text())['status']=='PASS';completed.append(job);del running[job]
  if gate:
   S['status']='running_verified_full_splits';free=subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines();busy={slot for q,slot in running.values()}
   for slot in range(4):
    if tasks and slot not in busy and int(free[slot])>=7000:launch(tasks.pop(0),slot)
  put();time.sleep(10)
 S['status']='complete';put()
except BaseException:S['status']='failed';S['error']=traceback.format_exc();put();raise
