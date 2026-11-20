import os,sys,json,csv,time,hashlib,traceback
from pathlib import Path
R=Path(sys.argv[1]);rank=int(sys.argv[2]);P=json.loads((R/'plan.json').read_text());S=Path(P['D_runtime']);sys.path.insert(0,str(R/'code'))
import xarray,torch,numpy as np
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray)
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
from eval.eval_full_base_suffix import model_rows,write_csv
torch.set_num_threads(1);O=R/'suffix_shards'/str(rank);O.mkdir(parents=True,exist_ok=False)
def put(n,v):
 p=O/n;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
start=time.time()
try:
 models=[];metas=[]
 for arm in ['C0R','C1','CONSISTENCY']:
  c=json.loads((R/'frozen'/f'{arm}.json').read_text());raw=Path(c['frozen']).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256'];ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False)
  assert (ck['arm'],ck['variant'],ck['args']['seed'],ck['epoch'],ck['step'])==(c['arm'],'D',42,40,29800)
  assert ck['lineage']['parent_file_sha256']==P['parent_sha256']
  m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),ck['contract_cfg']);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.cuda().eval()
  models.append((arm,m));metas.append(dict(model=arm,checkpoint_sha256=c['sha256'],training=dict(variant='D',seed=42,arm=arm),selection_kind=c['selection_kind'],epoch=c['epoch'],step=c['step'],strict=True,probe=False));del ck,raw
 ds=GreenEarthNetContextformerDataset(P['data_root']+'/iid_chopped',dl_cloudmask=True);index={str(Path(p).relative_to(P['data_root']+'/iid_chopped')):i for i,p in enumerate(ds.filepaths)}
 original=list(csv.DictReader((S/'legacy_sample_manifest.csv').open()));ids=sorted(r['receiver_id'] for r in original);assert len(ids)==len(set(ids))==2856 and set(ids)==set(index)
 assigned=ids[rank::4];put('ownership.json',dict(rank=rank,ids=assigned,sha256=hashlib.sha256('\n'.join(assigned).encode()).hexdigest()))
 dmanifest=list(csv.DictReader((S/'suffix/SAMPLE_MANIFEST.csv').open()));qual={r['receiver_id']:int(r['dataset_index']) for r in dmanifest if r['rank']}
 expected_counts={}
 for r in csv.DictReader((S/'suffix/PER_RECEIVER_HORIZON.csv').open()):
  if r['model']=='C1' and r['path']=='D20':expected_counts[(int(r['dataset_index']),int(r['k']))]=int(r['n_valid'])
 chosen=[];excluded=[];keys=set()
 with (O/'PER_RECEIVER_HORIZON.csv').open('w',newline='') as f,(O/'OUTPUT_GAPS.csv').open('w',newline='') as g:
  w=wg=None
  for pos,cid in enumerate(assigned):
   j=index[cid];it=ds[j];it['_dataset_index']=j;m=models[0][1];cl=int(m.context_len)
   valid=(it['dynamic_mask'][0][cl+10:cl+20,0]<1)&((it['landcover']>=m.lc_min)&(it['landcover']<=m.lc_max))[0]
   assert (int(valid.sum())>0)==(cid in qual)
   if int(valid.sum())==0:excluded.append(cid);continue
   assert qual[cid]==j
   chosen.append(dict(rank=len(chosen)+1,dataset_index=j,receiver_id=cid,cube=str(it.get('cubename','')),selection='stable_id_sorted_full_IID_suffix_total_valid_positive'))
   for (arm,model),meta in zip(models,metas):
    rr,gg,_=model_rows(model,[it],torch.device('cuda:0'),arm,meta);assert len(rr)==40
    for r in rr:
     key=(j,arm,r['path'],r['k']);assert key not in keys;keys.add(key);assert r['n_valid']==expected_counts[(j,r['k'])]
    if w is None:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();wg=csv.DictWriter(g,fieldnames=list(gg[0]));wg.writeheader()
    w.writerows(rr);wg.writerows(gg)
   f.flush();g.flush();elapsed=time.time()-start
   put('progress.json',dict(pid=os.getpid(),scanned=pos+1,total=len(assigned),receivers=len(chosen),rows=len(keys),seconds=elapsed,time=time.time()))
   if len(chosen)==1:put('protocol_check.json',dict(status='PASS',pid=os.getpid(),rank=rank,first_id=cid,rows=120,paired_masks_match_D=True,unique_keys=True,finite_valid_predictions=True,peak_cuda_bytes=torch.cuda.max_memory_allocated(),models=metas,time=time.time()))
 assert set(r['receiver_id'] for r in chosen)==set(assigned)&set(qual)
 write_csv(O/'SAMPLE_MANIFEST.csv',chosen,list(chosen[0]))
 put('result.json',dict(status='PASS',rank=rank,assigned=assigned,excluded=excluded,selected=len(chosen),rows=len(keys),models=metas,seconds=time.time()-start))
except BaseException:
 put('error.json',dict(error=traceback.format_exc(),time=time.time()));raise
