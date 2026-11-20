import sys,os,time,json,subprocess,fcntl,traceback,hashlib,shutil
from pathlib import Path
X=Path(__file__).resolve().parent;P=json.loads((X/'plan.json').read_text());R=Path(P['source_root'])
sys.path.insert(0,P['common']);from queue_common import *
lock=(X/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
S=dict(status='starting',controller=ident(os.getpid()),children={},reused=P['reused'],time=time.time());children={}
def publish():S['time']=time.time();put(X/'state.json',S)
try:
 for split,slot in [('iid_chopped',0),('ood-t_chopped',1)]:
  assert free_mib()[P['uuids'][slot]]>=4096
  dst=X/split;cmd=list(P['command'])
  for k,v in [('--out',str(dst)),('--split',split),('--controller',str(dst))]:cmd[cmd.index(k)+1]=v
  env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['uuids'][slot],OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
  with (X/(split+'.log')).open('ab') as f:q=subprocess.Popen(cmd,cwd=X,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  children[split]=q;S['children'][split]=dict(pid=q.pid,status='running',gpu_uuid=P['uuids'][slot]);publish()
 while any(q.poll() is None for q in children.values()):
  for split,q in children.items():
   dst=X/split;v=S['children'][split]
   if (dst/'protocol_check.json').exists() and not v.get('protocol_pass'):
    c=read(dst/'protocol_check.json');assert c['status']=='PASS' and c['checkpoint_sha256']==P['sha256'];assert (v['gpu_uuid'],q.pid) in apps()
    put(dst/'CONTINUE.json',dict(sha256=P['sha256'],time=time.time()));v['protocol_pass']=True
   if (dst/'progress.json').exists():v['progress']=read(dst/'progress.json')
   if q.poll() is not None and v['status']=='running':
    v.update(status='exited',exit=q.returncode);put(dst/'exit.json',dict(exit=q.returncode,pid=q.pid,time=time.time()))
  S['status']='evaluating';publish();time.sleep(10)
 for split,q in children.items():
  put(X/split/'exit.json',dict(exit=q.returncode,pid=q.pid,time=time.time()));assert q.returncode==0,(split,q.returncode)
  S['children'][split].update(status='exited',exit=q.returncode)
 import pandas as pd,numpy as np
 sys.path.insert(0,str(R/'recovery_v1/continuation'));from aggregate_metrics import aggregate,cols
 outputs={**P['reused'],'iid_chopped':str(X/'iid_chopped'),'ood-t_chopped':str(X/'ood-t_chopped')};results={};audits={};rows=[]
 for split,d in outputs.items():
  d=Path(d);v=read(d/'result.json');a=v['splits'][split];count=P['counts'][split]
  assert v['status']=='PASS' and v['selection_kind']=='fixed_epoch_040' and v['checkpoint_sha256']==P['sha256'] and v['best_epoch']==40 and v['best_step']==29800
  ids=[str(p.relative_to(Path(P['data_root'])/split)) for p in sorted((Path(P['data_root'])/split).glob('**/*.nc'))]
  coverage=[json.loads(line) for line in (d/(split+'_coverage.jsonl')).read_text().splitlines()]
  assert len(ids)==count and len(set(ids))==count and [v['id'] for v in coverage]==ids
  assert all(v['checkpoint_sha256']==P['sha256'] for v in coverage) and a['count']==count and a['coverage_complete']
  f=d/(split+'_cube_lc.csv');c=pd.read_csv(f,dtype={k:('float64' if k=='R2' else 'float32') for k in cols},float_precision='round_trip')
  assert not c.duplicated(['id','landcover']).any() and set(c.id)=={v['id'] for v in coverage if not v['empty']}
  assert aggregate(c)==a['metrics'];results[split]=a;audits[split]=dict(source=str(d),csv_sha256=sha(f),coverage_exact=True,aggregation_exact=True,reused=split in P['reused'])
  rows.append(dict(split=split,**a['metrics']))
 put(X/'result.json',dict(status='PASS',selection_kind='fixed_epoch_040',checkpoint_sha256=P['sha256'],epoch=40,step=29800,seed=42,arm='C1',source_variant='D',applicable_comparisons=['B','D'],config_equivalence=P['equivalence'],total_samples=22320,splits=results,acceptance=audits,time=time.time()))
 pd.DataFrame(rows).to_csv(X/'summary.csv',index=False);put(X/'acceptance.json',dict(status='PASS',new_workers={k:q.returncode for k,q in children.items()},reused_splits=list(P['reused']),full_coverage=True,time=time.time()))
 S['status']='complete';publish()
except BaseException:
 S.update(status='failed',error=traceback.format_exc());publish()
 # Existing training owns retention; do not start holders over active training/evaluation.
 raise
