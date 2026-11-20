import json,csv,hashlib,math,time
from pathlib import Path
import sys
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());S=Path(P['six_runtime']);O=R/'tables';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,rs):
 with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
agg={};ncounts={};sources=[]
manifest=list(csv.DictReader((S/'suffix/SAMPLE_MANIFEST.csv').open()))
receiver_ids={r['dataset_index']:r['receiver_id'] for r in manifest if r['rank']}
for p in [S/'suffix/PER_RECEIVER_HORIZON.csv',R/'suffix/PER_RECEIVER_HORIZON.csv']:
 sources.append(dict(file=str(p),sha256=sha(p)))
 for row in csv.DictReader(p.open()):
  receiver=receiver_ids[row['dataset_index']]
  k=(receiver,row['model'],row['path']);a=agg.setdefault(k,dict(sse=0.,n=0,ks=set()))
  h=int(row['k']);n=int(row['n_valid']);assert h not in a['ks'];a['ks'].add(h);a['n']+=n
  if n:a['sse']+=float(row['sse'])
  nk=(receiver,row['path'],h);ncounts.setdefault(nk,set()).add(n)
assert all(len(v)==1 for v in ncounts.values())
full={k:v['sse']/v['n'] for k,v in agg.items() if v['ks']==set(range(1,11)) and v['n']>0}
models=['C1','C0R','CONSISTENCY'];paths=['C','A','B'];cohort={m:{c for c,mm,p in full if mm==m and p=='D20'} for m in models}
assert all(cohort[m]==cohort['C1'] for m in models)
ids=sorted(cohort['C1']);mean=lambda vals:sum(vals)/len(vals)
sys.path.insert(0,str(S/'paper/legacy'))
from spatial_bootstrap import Target,bootstrap_target,geo_group
groups={i:geo_group(i) for i in ids};cirows=[]
def ci(model,path,metric,values):
 z=bootstrap_target(Target(model+path+metric,ids,values),groups)
 assert not z['degenerate']
 cirows.append(dict(model=model,path=path,metric=metric,n_receivers=len(ids),n_groups=z['n_groups'],mean=mean(values),ci95_low=z['ci_low'],ci95_high=z['ci_high'],ci_crosses_zero=z['ci_low']<=0<=z['ci_high']))
table=[];diff=[]
for m in models:
 d=mean([full[(i,m,'D20')] for i in ids])
 for p in paths:
  vals=[full[(i,m,p)] for i in ids];v=mean(vals)
  table.append(dict(model=m,seed=42,path=p,path_days={'C':'15+35','A':'50','B':'25+25'}[p],primary=p=='C',n_receivers=len(ids),direct_suffix_MSE=d,continuation_MSE=v,degradation_vs_own_direct=v-d,selection_window_epochs=60))
  for metric,values in [('direct_MSE',[full[(i,m,'D20')] for i in ids]),('continued_MSE',vals),('degradation',[full[(i,m,p)]-full[(i,m,'D20')] for i in ids])]:ci(m,p,metric,values)
for p in paths:
 c=next(r for r in table if r['model']=='C1' and r['path']==p)
 for m in ['C0R','CONSISTENCY']:
  r=next(r for r in table if r['model']==m and r['path']==p)
  diff.append(dict(path=p,reference='C1',comparison=m,n_receivers=len(ids),C1_minus_other_direct_MSE=c['direct_suffix_MSE']-r['direct_suffix_MSE'],C1_minus_other_continuation_MSE=c['continuation_MSE']-r['continuation_MSE'],C1_minus_other_degradation=c['degradation_vs_own_direct']-r['degradation_vs_own_direct']))
  for metric,values in [('direct_MSE_diff',[full[(i,'C1','D20')]-full[(i,m,'D20')] for i in ids]),('continued_MSE_diff',[full[(i,'C1',p)]-full[(i,m,p)] for i in ids]),('degradation_diff',[(full[(i,'C1',p)]-full[(i,'C1','D20')])-(full[(i,m,p)]-full[(i,m,'D20')]) for i in ids])]:ci('C1-minus-'+m,p,metric,values)
write('A_suffix.csv',table);write('A_model_differences.csv',diff)
write('A_geographic_CI.csv',cirows)
standard={};b=[]
for name,path in P['standard_results'].items():
 d=json.loads(Path(path).read_text());assert d['status']=='PASS' and d['checkpoint_sha256']==P['models'][name]['sha256'] and d['seed']==42
 assert len(d['splits'])==4 and all(v['coverage_complete'] for v in d['splits'].values())
 standard[name]=d;sources.append(dict(file=path,sha256=sha(path)))
for split,x in standard['C1']['splits'].items():
 y=standard['BASELINE']['splits'][split];assert x['relative_ids_sha256']==y['relative_ids_sha256'] and x['count']==y['count']
 for metric in ['rmse','R2']:
  a=x['metrics'][metric];z=y['metrics'][metric];assert math.isfinite(a) and math.isfinite(z)
  b.append(dict(split=split,metric=metric,C1=a,BASELINE=z,C1_minus_BASELINE=a-z,seed=42,selection_window_epochs=60,baseline_continuation='N/A'))
write('B_standard.csv',b)
judgments={}
for other in ['CONSISTENCY','C0R']:
 rs=[r for r in cirows if r['model']=='C1-minus-'+other and r['metric']=='continued_MSE_diff']
 judgments['C1_vs_'+other]=[{**r,'interpretation':'C1 lower with interval below zero' if r['ci95_high']<0 else ('C1 higher with interval above zero' if r['ci95_low']>0 else 'interval includes zero; advantage unresolved')} for r in rs]
 judgments['multi_path_consistency_vs_'+other]=dict(all_point_differences_negative=all(r['mean']<0 for r in rs),all_intervals_below_zero=all(r['ci95_high']<0 for r in rs))
judgments['state_branch_standard_effect']=[{**r,'interpretation':('C1 lower RMSE' if r['C1_minus_BASELINE']<0 else 'C1 higher RMSE') if r['metric']=='rmse' else ('C1 higher R2' if r['C1_minus_BASELINE']>0 else 'C1 lower R2')} for r in b]
judgments['scope']='Single seed42; geographic intervals do not include training randomness. Revised60epoch validation window, actual100/60 training budgets disclosed.'
(O/'scientific_judgments.json').write_text(json.dumps(judgments,indent=2))
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',A_complete=True,B_complete=True,seed=42,sources=sources,selection_receipt_sha256=sha(R/'selection_receipt.json'),main_path='15+35 to day50; independent targets55..100',rule_revision='user changed ablation selection to validation best within60 epochs after training; not preregistered',training_budget_epochs={'C1':100,'C0R':100,'CONSISTENCY':60,'BASELINE':60},schedule_horizon_epochs=100,C1_C0R_inference_reused=True,baseline_standard_reused=True,figures=False,manuscript_modified=False,time=time.time()),indent=2))
