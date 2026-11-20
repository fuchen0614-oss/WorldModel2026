import argparse,json,sys,os,csv,time,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--plan');ap.add_argument('--variant');ap.add_argument('--split');a=ap.parse_args();P=json.loads(Path(a.plan).read_text());R=Path(P['runtime']);O=R/a.variant/a.split;O.mkdir(parents=True,exist_ok=True);sys.path.insert(0,P['code'])
import numpy as np,torch,pandas as pd,xarray as xr
from train import terrastate_v2_common as t
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset as Dataset
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray);torch.set_num_threads(1)
def put(n,x):
 p=O/(n+'.tmp');p.write_text(json.dumps(x,allow_nan=False));p.replace(O/n)
J=P['models'][a.variant];raw=Path(J['checkpoint']).read_bytes();assert hashlib.sha256(raw).hexdigest()==J['sha256'];ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False);assert(ck['variant'],ck['arm'],ck['args']['seed'])==(a.variant,'C1',42);m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),contract_cfg=ck['contract_cfg']);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval();del ck,raw
root=Path(P['data_root'])/a.split;ds=Dataset(str(root),dl_cloudmask=True);assert len(ds)==P['splits'][a.split];index={str(Path(f).relative_to(root)):i for i,f in enumerate(ds.filepaths)};mf=R/'manifests'/(a.split+'.csv');assert hashlib.sha256(mf.read_bytes()).hexdigest()==P['manifest_sha'][a.split];pairs=list(csv.DictReader(mf.open()));assert len(pairs)==P['matched_counts'][a.split];assert len(set(r['relative_path'] for r in pairs))==len(pairs)==len(set(r['donor_relative_path'] for r in pairs));assert all(r['relative_path']!=r['donor_relative_path'] and r['relative_path'] in index and r['donor_relative_path'] in index for r in pairs)
def prepare(data):
 prior,z=m._prior_state(data);geo,u=m._geo_weather(data);return prior,m.segment_state(z,u,geo,(10,)),geo,u
fields=['receiver_id','donor_id','cube','geo_group','k','n_valid','original_sse','donor_sse'];start=time.time();counts={'suffix':0,'day100':0}
resume=json.loads((O/'resume.json').read_text());skip=resume['complete_pairs'];counts=resume['counts'];start-=resume['prior_seconds']
with (O/'paired_per_horizon.csv').open('a',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);
 for i,r in enumerate(pairs):
  if i<skip:continue
  ri=ds[index[r['relative_path']]];di=ds[index[r['donor_relative_path']]];data=t.to_device_with_ids(t.collate_with_ids([ri]),torch.device('cuda:0'));dd=t.to_device_with_ids(t.collate_with_ids([di]),torch.device('cuda:0'));cube=str(ri['cubename']);parts=Path(cube).stem.split('_');group=parts[2] if parts[0]=='minicube' and len(parts)>=5 else (f'lat={parts[2]}_lon={parts[3]}' if parts[0]=='minicube' and len(parts)>=4 else parts[0]);total=0;last=0
  with torch.no_grad():
   prior,z,geo,u=prepare(data);_,dz,_,_=prepare(dd);saved=z.clone();donor_saved=dz.clone();B,H,W=prior.shape[0],prior.shape[-2],prior.shape[-1]
   for k in range(1,11):
    pred=prior[:,9+k]+m.alpha*m._decode_state(m.segment_state(z,u[:,10:10+k],geo,(k,)),B,H,W);alt=prior[:,9+k]+m.alpha*m._decode_state(m.segment_state(dz,u[:,10:10+k],geo,(k,)),B,H,W);target=data['dynamic'][0][:,m.context_len+9+k,0:1];mask=(data['dynamic_mask'][0][:,m.context_len+9+k]<1)&(data['landcover']>=m.lc_min)&(data['landcover']<=m.lc_max);assert mask.shape==target.shape==pred.shape;yv=target[mask].double();pv=pred[mask].double();av=alt[mask].double();assert torch.isfinite(yv).all() and torch.isfinite(pv).all() and torch.isfinite(av).all();n=yv.numel();total+=n;last=n
    w.writerow(dict(receiver_id=r['relative_path'],donor_id=r['donor_relative_path'],cube=cube,geo_group=group,k=k,n_valid=n,original_sse=float((pv-yv).square().sum()),donor_sse=float((av-yv).square().sum())))
   assert torch.equal(z,saved) and torch.equal(dz,donor_saved)
  counts['suffix']+=int(total>0);counts['day100']+=int(last>0)
  if i==skip:put('protocol_PASS.json',{'status':'PASS','checkpoint_sha256':J['sha256'],'manifest_sha256':P['manifest_sha'][a.split],'all_paths_mapped':True,'only_state_replaced':True,'prefix_steps':[10],'receiver_prior_geo_weather_held_fixed':True,'states_unmodified':True,'scoring':'same valid target pixels; float64 SSE; no standard-accuracy rerun'})
  if i%25==0 or i==len(pairs)-1:f.flush();put('progress.json',{'done':i+1,'total':len(pairs),'seconds':time.time()-start,'eligible_counts':counts,'time':time.time()})
assert counts==P['expected_counts'][a.split],(counts,P['expected_counts'][a.split]);put('result.json',{'status':'PASS','variant':a.variant,'split':a.split,'pairs':len(pairs),'counts':counts,'rows':len(pairs)*10,'checkpoint_sha256':J['sha256'],'csv_sha256':hashlib.sha256((O/'paired_per_horizon.csv').read_bytes()).hexdigest(),'seconds':time.time()-start});print('PASS',a.variant,a.split,flush=True)
