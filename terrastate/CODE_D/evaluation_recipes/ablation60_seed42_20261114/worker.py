import os,sys,json,csv,time,hashlib,traceback
from pathlib import Path
R=Path(sys.argv[1]);mode=sys.argv[2];P=json.loads((R/'plan.json').read_text());S=Path(P['six_runtime']);sys.path.insert(0,str(R/'code'))
import xarray
import torch,numpy as np
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray)
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from eval.eval_full_base_suffix import model_rows,write_csv
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
torch.set_num_threads(1)
def put(n,v):
 p=R/n;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
try:
 selected=json.loads((R/'selection_receipt.json').read_text());assert selected['status']=='PASS'
 c=P['models']['CONSISTENCY'];raw=Path(c['checkpoint']).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
 ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False);cfg=ck['contract_cfg']
 assert cfg['endpoint_target']=='detached_direct' and ck['epoch']==51
 m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),cfg);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval();del ck,raw
 ds=GreenEarthNetContextformerDataset(P['data_root'],dl_cloudmask=True);idx={str(Path(fp).relative_to(P['data_root'])):i for i,fp in enumerate(ds.filepaths)}
 meta=dict(checkpoint_sha256=c['sha256'],arm='CONSISTENCY',training_arm='C1',endpoint_target='detached_direct',seed=42,variant='D',probe=False,strict=True)
 if mode=='first_sample':
  one=json.loads((S/'first_sample.json').read_text());cid=one['receiver_id'];it=ds[idx[cid]];it['_dataset_index']=idx[cid]
  rr,gg,_=model_rows(m,[it],torch.device('cuda:0'),'CONSISTENCY',meta)
  ref=[]
  with (S/'suffix/PER_RECEIVER_HORIZON.csv').open() as f:
   for r in csv.DictReader(f):
    if int(r['dataset_index'])==idx[cid] and r['model']=='C1':ref.append(r)
    if len(ref)==40:break
  assert len(rr)==len(ref)==40 and [r['n_valid'] for r in rr]==[int(r['n_valid']) for r in ref]
  put('first_sample_rows.json',{'rows':rr,'gaps':gg})
  put('first_sample.json',dict(status='PASS',pid=os.getpid(),receiver_id=cid,rows=40,mask_equal_existing_C1=True,finite_valid_predictions=True,peak_allocated=torch.cuda.max_memory_allocated(),time=time.time(),retained_for_full_run=True));sys.exit(0)
 assert mode=='remaining'
 manifests=list(csv.DictReader((S/'suffix/SAMPLE_MANIFEST.csv').open()));chosen=[r for r in manifests if r['rank']]
 # Same ID/path/target mask counts, checked against existing C1 sufficient statistics.
 ref={}
 with (S/'suffix/PER_RECEIVER_HORIZON.csv').open() as f:
  for r in csv.DictReader(f):
   if r['model']=='C1':ref[(int(r['dataset_index']),r['path'],int(r['k']))]=int(r['n_valid'])
 first=json.loads((R/'first_sample_rows.json').read_text());firstid=json.loads((R/'first_sample.json').read_text())['receiver_id']
 rows=[];keys=set();start=time.time();out=R/'suffix';out.mkdir(exist_ok=False)
 with (out/'PER_RECEIVER_HORIZON.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(first['rows'][0]));writer.writeheader()
  for n,c in enumerate(chosen):
   cid=c['receiver_id'];j=idx[cid];assert j==int(c['dataset_index'])
   if cid==firstid:rr=first['rows']
   else:
    it=ds[j];it['_dataset_index']=j;rr,_,_=model_rows(m,[it],torch.device('cuda:0'),'CONSISTENCY',meta)
   assert len(rr)==40
   for r in rr:
    k=(int(r['dataset_index']),r['path'],r['k']);assert k not in keys and r['n_valid']==ref[k];keys.add(k)
   writer.writerows(rr);f.flush();elapsed=time.time()-start
   put('progress.json',dict(status='running',pid=os.getpid(),receivers=n+1,total=len(chosen),rows=len(keys),elapsed_seconds=elapsed,estimated_remaining_seconds=elapsed/(n+1)*(len(chosen)-n-1),time=time.time()))
 assert keys==set(ref)
 write_csv(out/'SAMPLE_MANIFEST.csv',manifests,list(manifests[0]))
 put('suffix/RUN_METADATA.json',dict(status='COMPLETE',model=meta,n_selected=len(chosen),sample_manifest_sha256=hashlib.sha256((S/'suffix/SAMPLE_MANIFEST.csv').read_bytes()).hexdigest(),prefixes={'A':[10],'B':[5,5],'C':[3,7]},qualification='identical existing C1/C0R cohort and every path/target valid count',selection_receipt=str(R/'selection_receipt.json')))
 put('worker_exit.json',dict(exit=0,status='complete',receivers=len(chosen),rows=len(keys),time=time.time()))
except SystemExit:raise
except BaseException:
 put(mode+'_error.json',dict(error=traceback.format_exc(),time=time.time()));raise
