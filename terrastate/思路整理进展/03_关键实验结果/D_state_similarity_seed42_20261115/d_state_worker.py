import json,csv,sys,time,hashlib,io,os
from pathlib import Path
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());sys.path.insert(0,P['code'])
import numpy as np,torch
from train import terrastate_v2_common as t
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset as Dataset
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray);torch.set_num_threads(1)
def put(n,x):
 p=R/(n+'.tmp');p.write_text(json.dumps(x,allow_nan=False,indent=2));p.replace(R/n)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
models={};meta={}
for arm,j in P['models'].items():
 assert sha(j['checkpoint'])==j['sha256'];ck=torch.load(j['checkpoint'],map_location='cpu',weights_only=False)
 assert (ck['variant'],ck['arm'],ck['args']['seed'])==('D',arm,42)
 m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),contract_cfg=ck['contract_cfg']);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval();models[arm]=m
 meta[arm]={'sha256':j['sha256'],'epoch':ck['epoch'],'step':ck['step'],'seed':42,'variant':'D','arm':arm};del ck
assert sha(R/'samples.csv')==P['manifest_sha256'];all_rows=list(csv.DictReader((R/'samples.csv').open()));assert len(all_rows)==2856;rows=[r for r in all_rows if r['selection']=='stable_id_sorted_full_IID_suffix_total_valid_positive'];assert len(rows)==2837;assert sum(r['selection']=='EXCLUDED:no_valid_target_pixels_suffix_11_20' for r in all_rows)==19
ids=[r['receiver_id'] for r in rows];assert len(set(ids))==2837
root=Path(P['data_root'])/'iid_chopped';ds=Dataset(str(root),dl_cloudmask=True);assert len(ds)==2856;idx={str(Path(f).relative_to(root)):i for i,f in enumerate(ds.filepaths)};assert all(x in idx for x in ids)
start=time.time();out=[];fields=['receiver_id','arm','path_days','cosine','state_rmse','latent_tokens','zero_norm_tokens'];summ={}
with (R/'per_sample.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for i,r in enumerate(rows):
  data=t.to_device_with_ids(t.collate_with_ids([ds[idx[r['receiver_id']]]]),torch.device('cuda:0'))
  with torch.inference_mode():
   for arm,m in models.items():
    _,z=m._prior_state(data);geo,u=m._geo_weather(data);before=z.clone();direct=m.segment_state(z,u,geo,(10,));x=direct.flatten(1).double();assert x.shape[-1]==256
    for label,part in [('25+25',(5,5)),('15+35',(3,7))]:
     y=m.segment_state(z,u,geo,part).flatten(1).double();assert x.shape==y.shape and torch.isfinite(x).all() and torch.isfinite(y).all();normx=x.norm(dim=1);normy=y.norm(dim=1);zero=int(((normx<1e-8)|(normy<1e-8)).sum());assert zero==0,'undefined cosine: zero state norm'
     row={'receiver_id':r['receiver_id'],'arm':arm,'path_days':label,'cosine':float(torch.nn.functional.cosine_similarity(x,y,dim=1).mean()),'state_rmse':float((x-y).square().mean().sqrt()),'latent_tokens':len(x),'zero_norm_tokens':zero};w.writerow(row);out.append(row)
    assert torch.equal(z,before)
  if i%25==0 or i==len(rows)-1:
   f.flush();put('progress.json',{'done':i+1,'total':len(rows),'seconds':time.time()-start,'pid':os.getpid(),'time':time.time(),'models':meta})
assert len(out)==2837*4
for arm in models:
 for label in ['25+25','15+35']:
  rr=[r for r in out if r['arm']==arm and r['path_days']==label];assert len(rr)==2837 and {r['receiver_id'] for r in rr}==set(ids)
  summ[arm+'/'+label]={'n':len(rr),'cosine_mean':float(np.mean([r['cosine'] for r in rr])),'state_rmse_mean':float(np.mean([r['state_rmse'] for r in rr]))}
with (R/'summary.csv').open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['path_days','C1_cosine','C0R_cosine','C1_state_rmse','C0R_state_rmse','n'])
 for label in ['25+25','15+35']:
  c=summ['C1/'+label];d=summ['C0R/'+label];w.writerow([label,c['cosine_mean'],d['cosine_mean'],c['state_rmse_mean'],d['state_rmse_mean'],2837])
put('result.json',{'status':'PASS','formal_evaluation':True,'models':meta,'summary':summ,'samples':2837,'split':'iid_chopped','selection':'existing accepted common-suffix sample manifest; no result-dependent selection','aggregation':'cosine across 256 channels per spatial token; mean tokens per sample, then equal-weight sample mean; RMSE descriptive within each model only','manifest_sha256':P['manifest_sha256'],'csv_sha256':sha(R/'per_sample.csv'),'summary_sha256':sha(R/'summary.csv'),'seconds':time.time()-start,'seed_scope':'single paired seed42; not multi-seed evidence'})
print('PASS',flush=True)
