import sys,json,hashlib,math,time,io,os
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());sys.path.insert(0,str(R/'code'))
import xarray,torch,numpy as np
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray)
from train.full_base_policy import lr_factor
torch.set_num_threads(1);out={};(R/'frozen').mkdir(exist_ok=True)
for name,c in P['models'].items():
 p=Path(c['checkpoint']);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();ck=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=False);args=ck['args'];cfg=ck['contract_cfg']
 assert (ck['epoch'],ck['step'],ck['total_steps'],args['seed'],ck['variant'])==(40,29800,74500,42,'D')
 assert ck['lineage']['parent_file_sha256']==ck['sha']['parent_file_sha256']==P['parent_sha256']
 assert ck['arm']==('C1' if name=='CONSISTENCY' else name)
 if name=='CONSISTENCY':assert cfg['endpoint_target']=='detached_direct'
 elif name=='BASELINE':assert ck['arch']=='SpanWorldBaselineOnly'
 else:assert cfg.get('endpoint_target','observed')=='observed'
 s=json.loads((p.parent/'summary.json').read_text());hist=[v for v in s['validation_history'] if v['epoch']<=40];assert [v['epoch'] for v in hist]==list(range(1,41))
 peaks=[1e-5,3e-5] if name=='BASELINE' else [3e-5,1e-5,3e-5]
 for v in hist:
  assert v['step']==v['epoch']*745 and len(v['lr'])==len(peaks)
  assert all(math.isclose(a,b*lr_factor(v['step'],600,74500,'stage2'),rel_tol=1e-10) for a,b in zip(v['lr'],peaks))
 # Training args and recorded topology, no assumption from filename.
 topo={k:ck.get(k) for k in ['world_size','accum','global_batch','per_gpu_batch','runtime_topology']}
 gb=ck.get('global_batch',args.get('global_batch'));assert gb==32,(name,gb,topo)
 dest=R/'frozen'/f'{name}.pt'
 if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
 else:dest.write_bytes(raw);dest.chmod(0o444)
 out[name]=dict(status='PASS',selection_kind='fixed_epoch_040',source=str(p),frozen=str(dest),sha256=sha,epoch=40,step=29800,variant='D',arm=ck['arm'],seed=42,parent_sha=P['parent_sha256'],schedule_steps=74500,global_batch=gb,topology=topo,contract_cfg=cfg,validation_history=hist,source_summary_sha256=hashlib.sha256((p.parent/'summary.json').read_bytes()).hexdigest())
 (R/'frozen'/f'{name}.json').write_text(json.dumps(out[name],indent=2));c.update(checkpoint=str(dest),sha256=sha)
 del ck,raw
(R/'plan.json').write_text(json.dumps(P,indent=2));(R/'selection_receipt.json').write_text(json.dumps(dict(status='PASS',models=out,selection='fixed epoch40/29800 updates of100epoch schedule; post-hoc sensitivity, not best',time=time.time()),indent=2))
print('FIXED40_SELECTION_PASS')
