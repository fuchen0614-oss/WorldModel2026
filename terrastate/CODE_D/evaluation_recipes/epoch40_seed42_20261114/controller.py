import os,sys,json,time,subprocess,fcntl,traceback
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());PY=P['python'];lock=(R/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def put(n,v):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
def live(pid):
 try:os.kill(int(pid),0);return True
 except ProcessLookupError:return False
state=dict(status='selection_verification',pid=os.getpid(),children={},time=time.time());active={}
def cpu(script,label):
 env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
 with (R/(label+'.log')).open('ab') as log:
  c=subprocess.Popen([PY,'-B',str(R/script),str(R)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT);rc=c.wait()
 put(label+'_exit.json',dict(pid=c.pid,exit=rc,time=time.time()));assert rc==0,label
try:
 put('state.json',state);cpu('selection.py','selection');P=json.loads((R/'plan.json').read_text())
 state['status']='capacity_gated_parallel_evaluation';put('state.json',state)
 # Only share the pre-authorized 909 cards with their existing training. No signal/holder takeover.
 tasks=[('suffix',str(i),'') for i in range(4)]+[('standard',m,split) for split in ['ood-s_chopped','ood-st_chopped','iid_chopped','ood-t_chopped'] for m in ['C1','C0R','CONSISTENCY','BASELINE']]
 state['status']='running';put('resource_lease.json',dict(status='active',pid=os.getpid(),gpu_uuids=P['gpu_uuids'],guard_recognition_prefix=P['guard_recognition_prefix'],purpose='D40 16 standard splits and4disjoint suffix shards',time=time.time()))
 while tasks or active:
  for slot in range(4):
   if slot in active or not tasks:continue
   free=int(subprocess.check_output(['nvidia-smi','-i',P['gpu_uuids'][slot],'--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
   if free<8192:continue
   kind,arm,split=tasks.pop(0);label=f'standard_{arm}_{split}' if kind=='standard' else 'suffix_'+arm;out=R/'standard'/arm/split if kind=='standard' else R/'suffix_shards'/arm
   if kind=='standard':
    c=P['models'][arm];cmd=[PY,'-B',str(R/'code/eval/eval_fixed40_standard.py'),'--run',str(R/'frozen'),'--out',str(out),'--device','cuda:0','--data-root',P['data_root'],'--expected-checkpoint-sha256',c['sha256'],'--split',split,'--frozen-checkpoint',c['checkpoint'],'--frozen-receipt',str(R/'frozen'/f'{arm}.json'),'--controller',str(out)]
   else:cmd=[PY,'-B',str(R/'suffix_worker.py'),str(R),arm]
   env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuids'][slot],OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
   with (R/(label+'.log')).open('ab') as log:c=subprocess.Popen(cmd,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
   active[slot]=(label,c,kind,arm,out);state['children'][label]=dict(pid=c.pid,uuid=P['gpu_uuids'][slot],slot=slot,kind=kind,arm=arm,command=cmd,status='running',started=time.time())
  for slot,(label,c,kind,arm,out) in list(active.items()):
   x=state['children'][label];check=out/'protocol_check.json'
   if check.exists() and not x.get('protocol_pass'):
    ck=json.loads(check.read_text());assert ck['status']=='PASS' and ck['pid']==c.pid
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
    assert any(line.split(',')[0].strip()==x['uuid'] and int(line.split(',')[1])==c.pid for line in apps.splitlines())
    x.update(protocol_pass=True,protocol_check=ck)
    if kind=='standard':put(str((out/'CONTINUE.json').relative_to(R)),dict(sha256=P['models'][arm]['sha256']))
   if (out/'progress.json').exists():
    try:x['progress']=json.loads((out/'progress.json').read_text())
    except json.JSONDecodeError:pass
   rc=c.poll()
   if rc is not None:
    x.update(status='complete' if rc==0 else 'failed',exit=rc,ended=time.time());put(label+'_exit.json',dict(pid=c.pid,exit=rc,time=time.time()));del active[slot];assert rc==0 and x.get('protocol_pass'),label
  state.update(time=time.time(),pending_tasks=len(tasks));put('state.json',state);time.sleep(2)
 assert len(state['children'])==20 and all(x['exit']==0 for x in state['children'].values())
 put('resource_lease.json',dict(status='released_all_workers_exited',time=time.time()));state['status']='cpu_merge_audit';put('state.json',state)
 for script,label in [('merge.py','merge'),('assemble.py','assemble'),('audit_compare.py','audit_compare')]:cpu(script,label)
 state.update(status='complete',exit=0,receipt=str(R/'tables/receipt.json'),audit=str(R/'audit/REPORT.md'),time=time.time());put('state.json',state)
except BaseException:
 state.update(status='failed',exit=1,error=traceback.format_exc(),time=time.time());put('state.json',state)
 # Preserve/reap existing workers, never kill healthy training or evaluation.
 for slot,(label,c,kind,arm,out) in active.items():
  rc=c.wait();state['children'][label].update(exit=rc,status='complete' if rc==0 else 'failed');put(label+'_exit.json',dict(pid=c.pid,exit=rc,time=time.time()))
 put('resource_lease.json',dict(status='released_after_worker_exit_failure_preserved',time=time.time()));put('state.json',state);raise
