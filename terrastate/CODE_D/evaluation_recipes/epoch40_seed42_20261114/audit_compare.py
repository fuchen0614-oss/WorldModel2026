import json,csv,sys,statistics,hashlib,math
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());O=R/'audit';O.mkdir(exist_ok=False);S=Path(P['D_runtime']);old=Path(P['best_runtime'])
def readcsv(p):return list(csv.DictReader(p.open()))
def write(n,rows):
 with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
sys.path.insert(0,str(S/'paper/legacy'));from spatial_bootstrap import geo_group
new=readcsv(R/'tables/A_model_differences.csv');before=readcsv(old/'tables/A_model_differences.csv');comparison=[]
for tag,rs in [('fixed40',new),('best_within60',before)]:
 for r in rs:
  d=float(r['C1_minus_other_direct_MSE']);g=float(r['C1_minus_other_degradation']);c=float(r['C1_minus_other_continuation_MSE']);assert abs(c-d-g)<1e-12
  comparison.append(dict(selection=tag,path=r['path'],comparison=r['comparison'],continued_difference=c,direct_difference=d,degradation_difference=g,identity_error=c-d-g))
write('decomposition_all_paths_both_selections.csv',comparison)
manifest={r['dataset_index']:r['receiver_id'] for r in readcsv(R/'suffix/SAMPLE_MANIFEST.csv') if r['rank']};agg={};target={};counts={}
for r in readcsv(R/'suffix/PER_RECEIVER_HORIZON.csv'):
 cid=manifest[r['dataset_index']];n=int(r['n_valid']);k=(cid,r['model'],r['path']);a=agg.setdefault(k,[0.,0]);a[0]+=float(r['sse']) if n else 0;a[1]+=n
 target[cid,r['model'],r['path'],int(r['k'])]=(float(r['sse']),n);counts.setdefault((cid,int(r['k'])),set()).add(n)
assert all(len(v)==1 for v in counts.values());full={k:s/n for k,(s,n) in agg.items() if n};ids=sorted(set(manifest.values()));heter=[];time_rows=[]
for other in ['C0R','CONSISTENCY']:
 for path in ['D20','A','B','C']:
  dif={i:full[i,'C1',path]-full[i,other,path] for i in ids};groups={g:[i for i in ids if geo_group(i)==g] for g in sorted(set(geo_group(i) for i in ids))}
  for group,members in [('ALL',ids)]+list(groups.items()):
   ds=[dif[i] for i in members];heter.append(dict(comparison=other,path=path,group=group,n=len(ds),mean_difference=statistics.mean(ds),median_difference=statistics.median(ds),fraction_C1_lower=sum(x<0 for x in ds)/len(ds)))
  for k in range(1,11):
   eligible=[i for i in ids if target[i,'C1',path,k][1]>0];ds=[target[i,'C1',path,k][0]/target[i,'C1',path,k][1]-target[i,other,path,k][0]/target[i,other,path,k][1] for i in eligible]
   time_rows.append(dict(comparison=other,path=path,target_day=50+5*k,n=len(ds),mean_difference=statistics.mean(ds),median_difference=statistics.median(ds),fraction_C1_lower=sum(x<0 for x in ds)/len(ds)))
write('all_geographic_groups_and_receivers.csv',heter);write('all_target_times.csv',time_rows)
# Exact model/config/source audit retained independently from metric ranking.
selection=json.loads((R/'selection_receipt.json').read_text());contracts={m:x['contract_cfg'] for m,x in selection['models'].items()};cfgdiff={m:{k:[contracts['C1'].get(k),c.get(k)] for k in set(c)|set(contracts['C1']) if c.get(k)!=contracts['C1'].get(k)} for m,c in contracts.items()}
stand=readcsv(R/'tables/B_all_models_all_metrics.csv');beststd={}
for m,fn in P['best_standard_results'].items():
 if Path(fn).exists():
  d=json.loads(Path(fn).read_text());expected=json.loads((old/'selection_receipt.json').read_text())['models'][m]['sha256'];assert d['checkpoint_sha256']==expected
  beststd[m]=d
rs=[]
for r in stand:
 m=r['model'];sp=r['split'];metric=r['metric'];v=float(r['value']);oldv=beststd.get(m,{}).get('splits',{}).get(sp,{}).get('metrics',{}).get(metric)
 rs.append(dict(model=m,split=sp,metric=metric,fixed40=v,best60=oldv if oldv is not None else '',difference=v-oldv if oldv is not None else '',available_best=oldv is not None))
write('standard_all_metrics_both_selections.csv',rs)
rank=[]
for a in new:
 b=next(x for x in before if x['path']==a['path'] and x['comparison']==a['comparison']);x=float(a['C1_minus_other_continuation_MSE']);y=float(b['C1_minus_other_continuation_MSE']);rank.append(dict(path=a['path'],comparison=a['comparison'],fixed40_delta=x,best60_delta=y,same_sign=(x<0)==(y<0)))
report=dict(status='PASS_NUMERICAL_AUDIT',selection='post-hoc fixed40 vs post-hoc bestwithin60',rank_stability=rank,contract_differences=cfgdiff,checks=['all20workers actualexit0','exact ID coverage','all three models/path targetmask counts equal','official standard compact reaggregation exact','continuation=direct+degradation exact','all geographic groups retained'],limits=['Equal counts alone do not prove bitwise pixel masks; same data and scoring code checked, no independent fullNetCDF audit','No new training gradient or RNG replay; C1 topology migration not bitwise exact historical trajectory','baseline removal changes endpoint path as well as architecture','missing beststandard model results are missing, not inferred','one unseen path15+35 does not establish all unseen partitions'],protocols={'25+25':'seen','15+35':'unseen','suffix':'receiver equal mean of sumSSE/sumvalid','standard':'official LC aggregation; not interchangeable','bootstrap':'unchanged legacy geographic2000; seed42 not trainingseed uncertainty'})
(O/'audit.json').write_text(json.dumps(report,indent=2));lines=['# D seed42 fixed40 sensitivity audit','', 'Fixed epoch40 / step29800 of the100epoch schedule. Not first40 best, not a standalone40epoch schedule. Prior unfavorable best results retained.','', '## All-path ranking comparison']
for r in rank:lines.append(f"- {r['path']} C1 minus {r['comparison']}: fixed40={r['fixed40_delta']:.9g}; best60={r['best60_delta']:.9g}; same sign={r['same_sign']}")
lines+=['','## Verified and limits',*['- '+x for x in report['checks']],*['- '+x for x in report['limits']],'','Full training-code audit evidence is in training_audit_evidence. Tables preserve every path, group, target and available standard metric. No figures or manuscript edits.'];(O/'REPORT.md').write_text('\n'.join(lines))
