import os,sys,json,csv,time,hashlib,gc,statistics,subprocess,math
from pathlib import Path
VALIDATE_ONLY='--validate-only' in sys.argv
R=Path(__file__).resolve().parent;P=json.loads((R/'plan.json').read_text());sys.path.insert(0,P['code'])
import numpy as np,torch
from train import terrastate_v2_common as t
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset as Dataset
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray);torch.set_num_threads(1)
def put(n,x):
 p=R/(n+'.tmp');p.write_text(json.dumps(x,indent=2,allow_nan=False));p.replace(R/n)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def others():
 s=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
 return [x for x in s.splitlines() if P['gpu_uuid'] in x and int(x.split(',')[1].strip())!=os.getpid()]
j=P['models']['C1'];assert sha(j['checkpoint'])==j['sha256'];ck=torch.load(j['checkpoint'],map_location='cpu',weights_only=False);assert (ck['variant'],ck['arm'],ck['args']['seed'])==('D','C1',42)
m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),contract_cfg=ck['contract_cfg']);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval();meta={'epoch':ck['epoch'],'step':ck['step'],'sha256':j['sha256']};del ck
assert VALIDATE_ONLY or not others(),'GPU shared before timing'
root=Path(P['data_root'])/'iid_chopped';ds=Dataset(str(root),dl_cloudmask=True);index={str(Path(f).relative_to(root)):i for i,f in enumerate(ds.filepaths)};samples=P['samples'];assert len(set(samples))==8 and all(s in index for s in samples)
def prep(data):
 prior,z=m._prior_state(data);g,u=m._geo_weather(data);return {'prior':prior,'z':z,'g':g,'u':u,'shape':(prior.shape[0],prior.shape[-2],prior.shape[-1])}
def query(c,z,offset):
 u=c['u'][:,offset:];N=z.shape[0];weather=m._to_patch(m.weather_enc.all_prefixes(u),N);start=10 if offset==0 else 0;weather=weather[:,start:];L=10
 h=m.time_emb(torch.arange(start+1,start+L+1,device=z.device)).unsqueeze(0).expand(N,L,-1);g=c['g'].unsqueeze(1).expand(N,L,-1);season=m._to_patch(u[:,start:,-2:],N)
 cond=m._cond(weather,g,h,season);zs=m.transition(z.unsqueeze(1).expand(N,L,-1),cond);return c['prior'][:,10:20]+m.alpha*m._unpatchify(m.o_delta(zs),*c['shape'])
def direct(data):
 c=prep(data);return query(c,c['z'],0)
def prepare50(data):
 c=prep(data);c['z50']=m.segment_state(c['z'],c['u'],c['g'],(3,7));return c
def partitioned(data):
 c=prepare50(data);return query(c,c['z50'],10)
def reference(c,z,offset):
 ans=[]
 for k in range(1,11):
  h=10+k if offset==0 else k;u=c['u'] if offset==0 else c['u'][:,10:];zz=m.direct_state(z,u,c['g'],h);ans.append(c['prior'][:,9+k]+m.alpha*m._decode_state(zz,*c['shape']))
 return torch.stack(ans,1)
start=time.time();records=[];checks=[]
with torch.inference_mode():
 for si,sample in enumerate(samples):
  assert VALIDATE_ONLY or not others(),'GPU shared before sample'
  data=t.to_device_with_ids(t.collate_with_ids([ds[index[sample]]]),torch.device('cuda:0'));assert tuple(data['dynamic'][0].shape[-2:])==(128,128)
  c=prepare50(data)
  for label,z,offset in [('direct',c['z'],0),('partitioned',c['z50'],10)]:
   y=query(c,z,offset);ref=reference(c,z,offset);diff=float((y-ref).abs().max());assert torch.allclose(y,ref,atol=1e-5,rtol=1e-4),(label,diff);checks.append({'sample':sample,'mode':label,'max_abs_diff':diff})
  del y,ref,c,z
  if VALIDATE_ONLY:
   del data
   continue
  modes=['direct_end_to_end','partitioned_end_to_end','cached_continuation','prefix_and_cache_preparation'];modes=modes[si%4:]+modes[:si%4]
  for mode in modes:
   cached=prepare50(data) if mode=='cached_continuation' else None
   fn={'direct_end_to_end':lambda:direct(data),'partitioned_end_to_end':lambda:partitioned(data),'cached_continuation':lambda:query(cached,cached['z50'],10),'prefix_and_cache_preparation':lambda:prepare50(data)}[mode]
   for _ in range(3):o=fn();del o
   torch.cuda.synchronize();gc.collect();torch.cuda.empty_cache()
   for rep in range(10):
    torch.cuda.synchronize();base=torch.cuda.memory_allocated();torch.cuda.reset_peak_memory_stats();ts=time.perf_counter();o=fn();torch.cuda.synchronize();elapsed=time.perf_counter()-ts;peak=torch.cuda.max_memory_allocated();assert elapsed>0 and peak>=base;records.append({'sample':sample,'mode':mode,'repeat':rep,'seconds':elapsed,'peak_allocated_bytes':peak,'baseline_allocated_bytes':base,'incremental_peak_bytes':peak-base});del o
   del cached,fn;gc.collect();torch.cuda.empty_cache();assert not others(),'GPU sharing detected during timing'
  del data
  put('progress.json',{'samples_done':si+1,'samples_total':8,'timings':len(records),'seconds':time.time()-start,'pid':os.getpid()})
if VALIDATE_ONLY:
 put('numerical_equivalence.json',{'status':'PASS','samples':samples,'checks':checks,'timing_valid':False,'reason':'numerical validation only on shared GPU'});print('NUMERICAL_PASS',flush=True);raise SystemExit
summary={}
for mode in ['direct_end_to_end','partitioned_end_to_end','cached_continuation','prefix_and_cache_preparation']:
 rr=[x for x in records if x['mode']==mode];assert len(rr)==80;lat=[x['seconds']*1000 for x in rr];summary[mode]={'n':80,'median_ms':statistics.median(lat),'p25_ms':float(np.percentile(lat,25)),'p75_ms':float(np.percentile(lat,75)),'max_peak_allocated_MiB':max(x['peak_allocated_bytes'] for x in rr)/2**20,'max_incremental_peak_MiB':max(x['incremental_peak_bytes'] for x in rr)/2**20}
with (R/'timings.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
with (R/'summary.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['mode']+list(next(iter(summary.values()))));w.writeheader();w.writerows(dict(mode=k,**v) for k,v in summary.items())
put('result.json',{'status':'PASS','checkpoint':meta,'summary':summary,'equivalence_checks':checks,'samples':samples,'gpu':torch.cuda.get_device_name(),'gpu_uuid':P['gpu_uuid'],'torch':torch.__version__,'cuda':torch.version.cuda,'batch':1,'spatial_shape':[128,128],'dtype':'float32','warmup_per_sample_mode':3,'repeats_per_sample_mode':10,'targets_days':list(range(55,101,5)),'prefix_days':[15,35],'timing_scope':'GPU-resident model inference including history/state encoding, future-conditioned baseline and weather encoding for end-to-end modes; excludes disk I/O and host-to-device transfer','cache_scope':'cached_continuation starts with computed z50, baseline, geo and weather tensors; cache preparation reported separately; cached memory included in peak','direct_optimization':'weather prefixes shared and ten target dates batched; partitioned suffix uses same batching; equivalence checked against independent target queries','gpu_exclusive_checks':'no other compute PID at each sample start and after every mode','timings_sha256':sha(R/'timings.csv'),'summary_sha256':sha(R/'summary.csv'),'total_seconds':time.time()-start})
print('PASS',flush=True)
