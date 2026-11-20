import sys,json,os,time,hashlib,argparse,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--variant');a=ap.parse_args();R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());O=R/a.variant;O.mkdir(exist_ok=False);sys.path.insert(0,P['code'])
import numpy as np,torch,pandas as pd,xarray as xr
from train import terrastate_v2_common as t
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset as Dataset
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray);torch.set_num_threads(1)
def put(name,obj):
 p=O/(name+'.tmp');p.write_text(json.dumps(obj,allow_nan=False,default=str));p.replace(O/name)
J=P['models'][a.variant];raw=Path(J['checkpoint']).read_bytes();assert hashlib.sha256(raw).hexdigest()==J['sha256'];ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False);assert (ck['variant'],ck['arm'],ck['args']['seed'])==(a.variant,'C1',42)
m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),contract_cfg=ck['contract_cfg']);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval()
put('architecture.json',{'checkpoint':J,'config':ck['contract_cfg'],'args':ck['args'],'epoch':ck.get('epoch'),'step':ck.get('step'),'parameters':sum(p.numel() for p in m.parameters()),'representation':str(m),'tensor_shapes':{k:list(v.shape) for k,v in m.state_dict().items()}});del raw,ck
root=Path(P['data_root']);split=root/'ood-t_chopped';ds=Dataset(str(split),dl_cloudmask=True);idx={str(Path(f).relative_to(root)):i for i,f in enumerate(ds.filepaths)}
man=json.loads((R/'matched_normal_manifest.json').read_text());hot=json.loads((R/'hotdry_manifest.json').read_text());pairs=sorted((k,v['control_path']) for k,v in man['audit']['pairs_extreme_to_control'].items());assert len(pairs)==84 and len(set(c for e,c in pairs))==45;assert len(set(re.search(r'_(\d{2}[A-Z]{3})_',e).group(1) for e,c in pairs))==31
for row in hot['files']+man['files']:
 p=root/row['path'];assert row['path'] in idx and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
def data(path):return t.to_device_with_ids(t.collate_with_ids([ds[idx[path]]]),torch.device('cuda:0'))
def parts(d):
 b,z=m._prior_state(d);g,u=m._geo_weather(d);return b,z,g,u
def losses(d,donor_weather):
 b,z,g,u=parts(d);B,H,W=b.shape[0],b.shape[-2],b.shape[-1];assert u.shape[-1]==26
 donor=u.clone();donor[:,:,:24]=donor_weather[:,:,:24];mean=u.clone();mean[:,:,:24]=0
 assert torch.equal(donor[:,:,24:],u[:,:,24:]) and torch.equal(mean[:,:,24:],u[:,:,24:])
 target=d['dynamic'][0][:,m.context_len:m.context_len+m.target_len,0:1];mask=(d['dynamic_mask'][0][:,m.context_len:m.context_len+m.target_len]<1)&((d['landcover']>=m.lc_min)&(d['landcover']<=m.lc_max)).unsqueeze(1);n=int(mask.sum());assert n>0;out={}
 for name,forcing in [('actual',u),('donor',donor),('mean',mean)]:
  pred=b+m.alpha*m._direct_residual(z,forcing,g,B,H,W);assert pred.shape==target.shape and torch.isfinite(pred[mask]).all();out[name]=float(((pred-target).square()*mask).sum()/mask.sum());assert np.isfinite(out[name])
 return out,u
rows=[];start=time.time()
for i,(ep,cp) in enumerate(pairs):
 with torch.no_grad():
  E,C=data(ep),data(cp);_,uc=m._geo_weather(C);le,ue=losses(E,uc);lc,_=losses(C,ue)
 row={'extreme':ep,'control':cp,'tile':re.search(r'_(\d{2}[A-Z]{3})_',ep).group(1),'loss_e':le,'loss_c':lc,'weather_differs':bool((ue[:,:,:24]-uc[:,:,:24]).abs().max()>0)};rows.append(row)
 put('per_pair.json',rows);put('progress.json',{'done':i+1,'total':84,'seconds':time.time()-start,'time':time.time()})
 if i==0:put('protocol_PASS.json',{'status':'PASS','data_sha_verified':True,'pairs':84,'donors':45,'geo_groups':31,'fixed_base_prediction':True,'receiver_season_preserved':True,'intervention':'24 weather channels of state branch only; baseline retains factual future weather','checkpoint_sha256':J['sha256']})
put('result.json',{'status':'PASS','variant':a.variant,'pairs':84,'seconds':time.time()-start,'checkpoint_sha256':J['sha256'],'per_pair_sha256':hashlib.sha256((O/'per_pair.json').read_bytes()).hexdigest()});print('PASS',a.variant,flush=True)
