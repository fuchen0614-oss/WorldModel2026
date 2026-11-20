"""Bounded-memory paired suffix inference; original model_rows/estimators unchanged."""
import os,sys,json,time,csv,hashlib,traceback
from pathlib import Path
R=Path(sys.argv[1]); cfg=json.loads((R/'plan.json').read_text())
sys.path.insert(0,str(R/'code'))
import xarray
import torch
from eval.eval_full_base_suffix import model_rows,sha256_file,write_csv
from eval.full_base_loader import load_candidate_c_strict
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
torch.set_num_threads(1)
O=R/'suffix';O.mkdir(exist_ok=False)
def put(name,v):
 p=R/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2));t.replace(p)
start=time.time();count=0
try:
 models=[];metas=[]
 for name in ['C0R','C1']:
  c=cfg['models'][name]; m,ck,meta=load_candidate_c_strict(c['checkpoint'],device='cuda:0',expected_sha=c['sha256'])
  assert meta['variant']=='D' and meta['seed']==42 and meta['arm']==name
  assert ck['lineage']['parent_file_sha256']==cfg['parent_sha256'],'different common parent'
  meta.update(model=name,lc_min=m.lc_min,lc_max=m.lc_max,training=dict(meta))
  # Preserve actual checkpoint lineage, rather than infer common parent from name.
  meta['lineage']=ck.get('lineage');meta['contract_cfg']=ck.get('contract_cfg')
  models.append((name,m));metas.append(meta);del ck
 assert len({(m.lc_min,m.lc_max,m.context_len) for _,m in models})==1
 put('weights_verified.json',{'models':metas,'time':time.time()})
 ds=GreenEarthNetContextformerDataset(cfg['data_root'],dl_cloudmask=True)
 index={str(Path(p).relative_to(cfg['data_root'])):j for j,p in enumerate(ds.filepaths)}
 old=list(csv.DictReader((R/'legacy_sample_manifest.csv').open()))
 ids=sorted(r['receiver_id'] for r in old)
 assert len(ids)==2856 and len(set(ids))==2856
 assert set(ids)==set(index),'IID file coverage differs from original manuscript manifest'
 chosen=[];excluded=[];keys=set();nzero=0
 f=(O/'PER_RECEIVER_HORIZON.csv').open('w',newline='');g=(O/'OUTPUT_GAPS.csv').open('w',newline='');w=wg=None
 # Batch one keeps peak predictable while sharing a healthy training GPU.
 for pos,cid in enumerate(ids):
  j=index[cid]; item=ds[j];item['_dataset_index']=j;m=models[0][1];cl=int(m.context_len)
  valid=(item['dynamic_mask'][0][cl+10:cl+20,0]<1.0)&((item['landcover']>=m.lc_min)&(item['landcover']<=m.lc_max))[0]
  if int(valid.sum())==0:
   excluded.append({'rank':'','dataset_index':'','receiver_id':cid,'cube':'','selection':'EXCLUDED:no_valid_target_pixels_suffix_11_20'});continue
  chosen.append({'rank':len(chosen)+1,'dataset_index':j,'receiver_id':cid,'cube':str(item.get('cubename','')),'selection':'stable_id_sorted_full_IID_suffix_total_valid_positive'})
  pair=[]
  for (name,model),meta in zip(models,metas):
   rr,gg,_=model_rows(model,[item],torch.device('cuda:0'),name,meta)
   assert len(rr)==40
   if w is None:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();wg=csv.DictWriter(g,fieldnames=list(gg[0]));wg.writeheader()
   for r in rr:
    key=(j,name,r['path'],r['k']);assert key not in keys;keys.add(key)
   pair.append(rr);w.writerows(rr);wg.writerows(gg)
  assert [r['n_valid'] for r in pair[0]]==[r['n_valid'] for r in pair[1]]
  if any(r['n_valid']==0 for r in pair[0]):nzero+=1
  count+=1;f.flush();g.flush()
  elapsed=time.time()-start
  put('progress.json',dict(pid=os.getpid(),status='running',scanned=pos+1,total_candidates=len(ids),receivers=count,rows=len(keys),elapsed_seconds=elapsed,estimated_remaining_seconds=elapsed/max(1,pos+1)*(len(ids)-pos-1),last_id=cid,time=time.time()))
  if count==1:put('first_sample.json',dict(pid=os.getpid(),receiver_id=cid,rows=80,finite_valid_predictions=True,paired_mask_counts_equal=True,elapsed_seconds=elapsed,peak_allocated=torch.cuda.max_memory_allocated()))
 f.close();g.close()
 assert len(keys)==len(chosen)*80
 write_csv(O/'SAMPLE_MANIFEST.csv',chosen+excluded,['rank','dataset_index','receiver_id','cube','selection'])
 meta=dict(status='COMPLETE',probe=False,n_selected=len(chosen),dataset_total=len(ds),models=metas,prefixes={'A':[10],'B':[5,5],'C':[3,7]},manifest_id_list_sha256=hashlib.sha256('\n'.join(ids).encode()).hexdigest(),manifest_sha256=sha256_file(R/'legacy_sample_manifest.csv'),elapsed_seconds=time.time()-start,qualification='ten target rows present and suffix total n_valid > 0; not every-target positive',receivers_with_some_empty_targets=nzero,quality_gate={'duplicate_keys':0,'missing_or_extra_rows':0,'nonfinite_valid_predictions':0,'mask_count_mismatch':0},future_labels_used_for_scoring_only=True)
 (O/'RUN_METADATA.json').write_text(json.dumps(meta,indent=2))
 put('worker_exit.json',dict(exit=0,status='complete',receivers=count,rows=len(keys),time=time.time()))
except BaseException:
 put('worker_exit.json',dict(exit=1,error=traceback.format_exc(),receivers=count,time=time.time()));raise
