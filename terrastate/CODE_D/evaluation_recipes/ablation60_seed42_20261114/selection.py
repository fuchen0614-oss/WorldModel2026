import sys,json,hashlib,math,time
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());sys.path.insert(0,str(R/'code'))
import xarray
import torch
torch.set_num_threads(1)
import numpy as np
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray)
from train.full_base_policy import lr_factor
out={}
for name,c in P['models'].items():
 p=Path(c['checkpoint']);s=json.loads((p.parent/'summary.json').read_text());raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
 ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False)
 assert s['status']=='COMPLETE' and s['seed']==42 and s['variant']=='D' and s['total_steps']==74500
 assert s['step']==(74500 if name in ['C1','C0R'] else 44700)
 hist=[v for v in s['validation_history'] if v['epoch']<=60]
 assert [v['epoch'] for v in hist]==list(range(1,61)),(name,'incomplete validation window')
 assert all(v['status']=='ok' and math.isfinite(v['RMSE_LC']) for v in hist)
 best=min(hist,key=lambda v:(v['RMSE_LC'],v['epoch']))
 assert best['epoch']==c['expected_epoch'] and ck['epoch']==best['epoch'] and ck['step']==best['step']
 assert ck['rmse_best']==dict(epoch=best['epoch'],step=best['step'],score=best['RMSE_LC'])
 assert ck['lineage']['parent_file_sha256']==P['parent_sha256']
 assert ck['args']['seed']==42 and ck['total_steps']==74500
 # Compare every available epoch boundary LR to the same 100ep cosine prefix.
 peaks=[1e-5,3e-5] if name=='BASELINE' else [3e-5,1e-5,3e-5]
 for v in hist:
  assert v['step']==v['epoch']*745 and len(v['lr'])==len(peaks)
  assert all(math.isclose(a,b*lr_factor(v['step'],600,74500,'stage2'),rel_tol=1e-10) for a,b in zip(v['lr'],peaks)),(name,v)
 if name=='CONSISTENCY':assert ck['contract_cfg']['endpoint_target']=='detached_direct' and ck['arm']=='C1'
 if name=='BASELINE':assert ck['arch']=='SpanWorldBaselineOnly'
 out[name]=dict(checkpoint=str(p),sha256=c['sha256'],best_epoch=best['epoch'],best_step=best['step'],validation_RMSE_LC=best['RMSE_LC'],actual_training_updates=s['step'],actual_training_epochs=s['step']//745,selection_window_epochs=60,schedule_horizon_updates=74500,lr_prefix_60_epochs_verified=True,parent_sha256=P['parent_sha256'],summary_sha256=hashlib.sha256((p.parent/'summary.json').read_bytes()).hexdigest(),validation_history_1_60=hist,contract_cfg=ck['contract_cfg'])
 del ck,raw
(R/'selection_receipt.json').write_text(json.dumps(dict(status='PASS',models=out,rule='minimum validation RMSE_LC in epochs1..60, first tie; user revision after training, not preregistered; no test selection',time=time.time()),indent=2))
print('SELECTION_PASS_ALL_FOUR')
