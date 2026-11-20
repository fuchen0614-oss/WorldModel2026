import sys,json,csv,hashlib
from pathlib import Path
import pandas as pd
from aggregate_metrics import aggregate,cols
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());S=Path(P['D_runtime']);O=R/'suffix';O.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def rows(p):return list(csv.DictReader(p.open()))
def write(n,rs):
 with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
assigned=[];selected=[];rr=[];gg=[];excluded=[]
for rank in range(4):
 p=R/'suffix_shards'/str(rank);v=read(p/'result.json');assert v['status']=='PASS' and read(R/f'suffix_{rank}_exit.json')['exit']==0
 assigned+=v['assigned'];excluded+=v['excluded'];selected+=rows(p/'SAMPLE_MANIFEST.csv');rr+=rows(p/'PER_RECEIVER_HORIZON.csv');gg+=rows(p/'OUTPUT_GAPS.csv')
assert len(assigned)==len(set(assigned))==2856
orig={r['receiver_id'] for r in rows(S/'suffix/SAMPLE_MANIFEST.csv') if r['rank']};assert {r['receiver_id'] for r in selected}==orig and len(selected)==2837
keys=[(int(r['dataset_index']),r['model'],r['path'],int(r['k'])) for r in rr]
expected={(int(r['dataset_index']),m,p,k) for r in selected for m in ['C0R','C1','CONSISTENCY'] for p in ['D20','A','B','C'] for k in range(1,11)}
assert len(keys)==len(set(keys))==2837*120 and set(keys)==expected
rr.sort(key=lambda r:(int(r['dataset_index']),r['model'],int(r['k']),r['path']));write('PER_RECEIVER_HORIZON.csv',rr);write('OUTPUT_GAPS.csv',gg)
selected.sort(key=lambda r:r['receiver_id'])
for i,r in enumerate(selected):r['rank']=i+1
selected +=[dict(rank='',dataset_index='',receiver_id=cid,cube='',selection='EXCLUDED:no_valid_target_pixels_suffix_11_20') for cid in sorted(excluded)]
write('SAMPLE_MANIFEST.csv',selected)
(O/'RUN_METADATA.json').write_text(json.dumps(dict(status='COMPLETE',n_selected=2837,models=read(R/'suffix_shards/0/protocol_check.json')['models'],prefixes={'A':[10],'B':[5,5],'C':[3,7]},qualification='same legacy cohort, ten rows and totalvalid>0',selection_kind='fixed_epoch_040',independent_suffix_targets=True,duplicate_keys=0),indent=2))
counts={'iid_chopped':2856,'ood-t_chopped':1904,'ood-s_chopped':10536,'ood-st_chopped':7024}
for arm in ['C1','C0R','CONSISTENCY','BASELINE']:
 splits={};audits={}
 for split,count in counts.items():
  out=R/'standard'/arm/split;assert read(R/f'standard_{arm}_{split}_exit.json')['exit']==0
  d=read(out/'result.json');v=d['splits'][split];assert d['status']=='PASS' and d['selection_kind']=='fixed_epoch_040' and d['checkpoint_sha256']==P['models'][arm]['sha256']
  ids=sorted(str(p.relative_to(Path(P['data_root'])/split)) for p in (Path(P['data_root'])/split).glob('**/*.nc'))
  cov=[json.loads(line) for line in (out/(split+'_coverage.jsonl')).read_text().splitlines()]
  assert [r['id'] for r in cov]==ids and len(set(ids))==count and v['count']==count and v['coverage_complete']
  assert hashlib.sha256('\n'.join(ids).encode()).hexdigest()==v['relative_ids_sha256']
  df=pd.read_csv(out/(split+'_cube_lc.csv'),dtype={k:('float64' if k=='R2' else 'float32') for k in cols},float_precision='round_trip')
  assert not df.duplicated(['id','landcover']).any() and set(df.id)=={r['id'] for r in cov if not r['empty']}
  assert aggregate(df)==v['metrics'];splits[split]=v;audits[split]=dict(real_exit=0,coverage_exact=True,reaggregation_exact=True)
 (R/'standard'/arm/'result.json').write_text(json.dumps(dict(status='PASS',selection_kind='fixed_epoch_040',checkpoint_sha256=P['models'][arm]['sha256'],epoch=40,step=29800,arm=arm,variant='D',seed=42,total_samples=22320,splits=splits,acceptance=audits,scorer_commit=d['scorer_commit']),indent=2))
(R/'merge_acceptance.json').write_text(json.dumps(dict(status='PASS',receivers=2837,rows=len(rr),standard_samples=89300 if False else 89280,exact_ID_coverage=True,all_20_real_exits_zero=True),indent=2))
