"""E1 aggregation and publication, gated by original-code numerical regression."""
import csv,json,hashlib,io,contextlib,tempfile,math,os
from pathlib import Path
from collections import defaultdict
import numpy as np
R=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展')
O=R/'03_关键实验结果/BD_原稿全表复刻_20261115';C=O/'E1_20min_collector';E=O/'E1_source_audit'
SPLITS=['iid_chopped','ood-t_chopped','ood-s_chopped','ood-st_chopped']
OLD=['iid','ood_t','ood_s','ood_st'];LABEL=['IID','OOD-T','OOD-S','OOD-ST']
COUNTS=[(2066,1214),(1605,884),(6965,3549),(5437,2731)]
GROUPS=[(80,80),(80,80),(878,852),(878,854)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def aggregate(rows):
 sets={'suffix':{},'endpoint':{}};seen=set();ids={};donors={};group_mapping={}
 for r in rows:
  key=r['receiver_id'];k=int(r['k']);assert 1<=k<=10 and (key,k) not in seen;seen.add((key,k))
  ids.setdefault(key,set()).add(k);donors.setdefault(key,r['donor_id']);assert donors[key]==r['donor_id'] and key!=r['donor_id']
  parts=Path(r['cube']).name.split('_');geo=parts[2] if len(parts)>=5 else 'lat='+parts[2]+'_lon='+parts[3]
  # Worker used Path.stem on extensionless cube IDs, truncating decimal longitude.
  # Reconstruct geographic identity from the intact cube exactly as original code.
  group_mapping.setdefault(r['geo_group'],set()).add(geo)
  n=int(r['n_valid']);a=float(r['original_sse']);b=float(r['donor_sse']);assert n>=0 and all(math.isfinite(x) and x>=0 for x in [a,b])
  if not n:assert a==b==0;continue
  for scope in (['suffix','endpoint'] if k==10 else ['suffix']):
   item=sets[scope].setdefault(key,[geo,np.zeros(3)]);assert item[0]==geo;item[1]+=np.array([n,a,b])
 assert all(v==set(range(1,11)) for v in ids.values()) and len(set(donors.values()))==len(ids)
 result={}
 for scope,items in sets.items():
  grouped=defaultdict(lambda:np.zeros(5));deltas=[]
  for geo,v in items.values():
   delta=(v[2]-v[1])/v[0];deltas.append(delta);grouped[geo][:3]+=v;grouped[geo][3]+=delta;grouped[geo][4]+=1
  m=np.array(list(grouped.values()));gm=m[:,3]/m[:,4];rng=np.random.default_rng(20260910);boot=[[],[],[]]
  for _ in range(10):
   ix=rng.integers(0,len(m),size=(200,len(m)));draw=m[ix].sum(axis=1)
   boot[0].extend(draw[:,3]/draw[:,4]);boot[1].extend(gm[ix].mean(axis=1));boot[2].extend((draw[:,2]-draw[:,1])/draw[:,0])
  total=m.sum(axis=0);point=[float(np.mean(deltas)),float(gm.mean()),float((total[2]-total[1])/total[0])]
  result[scope]={'N':len(items),'Groups':len(m),'estimates':point,'ci95':[np.quantile(b,[.025,.975]).tolist() for b in boot],'group_source':'intact cube ID parsed exactly as historical statistics; saved geo_group is not authoritative','truncated_source_labels':sum(len(v)>1 for v in group_mapping.values())}
 return result,donors
def reference_regression(rows,actual):
 # Execute the unchanged historical algorithm against a schema-only conversion.
 # Unused D20/B/MAE columns are aliases/zero; donor-minus-A columns remain exact.
 source=(E/'original_statistics_audit.py').read_text(encoding='utf-8')
 with tempfile.TemporaryDirectory(prefix='e1_reference_') as td:
  root=Path(td)
  for split in OLD:
   d=root/split/'plot_data';d.mkdir(parents=True)
   with (d/'formal_common_suffix_per_cube_horizon.csv').open('w',newline='',encoding='utf-8') as f:
    fields=['dataset_index','suffix_horizon','n_valid','D20_sse','A_sse','B_sse','donor_sse','cube','A_B_output_mae','donor_A_output_mae'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in rows:w.writerow(dict(dataset_index=r['receiver_id'],suffix_horizon=r['k'],n_valid=r['n_valid'],D20_sse=r['original_sse'],A_sse=r['original_sse'],B_sse=r['original_sse'],donor_sse=r['donor_sse'],cube=r['cube'],A_B_output_mae=0,donor_A_output_mae=0))
  original='/data/zs/terrastate_tip_runs/parallel_eval_20260908T075534Z/corrected_mask_recompute_20260910T071500Z/merged'
  assert source.count(original)==1;source=source.replace(original,root.as_posix());out=io.StringIO()
  with contextlib.redirect_stdout(out):exec(compile(source,'historical_statistics','exec'),{'__name__':'__main__'})
  reference=[json.loads(line) for line in out.getvalue().splitlines()]
  for r in reference:
   a=actual[r['scope']];assert a['N']==r['cubes'] and a['Groups']==r['groups'] and r['duplicates']==r['bad_positive_n_rows']==0
   for j,key in enumerate(['donor_cube_delta','donor_geo_equal_delta','donor_pooled_delta']):
    np.testing.assert_allclose(a['estimates'][j],r[key+'_mse'],rtol=0,atol=1e-12)
    ci_key=['donor_cube_delta_ci95','donor_geo_equal_ci95','donor_pooled_delta_ci95'][j]
    np.testing.assert_allclose(a['ci95'][j],r[ci_key],rtol=0,atol=1e-12)
 return {'status':'PASS','historical_code_sha256':sha(E/'original_statistics_audit.py'),'absolute_tolerance':1e-12,'method':'original program on schema-converted actual rows; all three point estimates and CIs'}
def publish(v,md,receipt):
 marker=f'<!-- BD_E1_VERIFIED_{v}_20261115 -->';d=C/v
 block='\n\n'+marker+'\n\n#### 附录E1：冻结匹配的状态替换（seed42）\n\n'+md+'\n正值表示 donor 状态使误差增大。保持 receiver 的历史基准、地理、后续天气及观测掩膜，仅替换第50天状态。三种加权分别计算，2000次地理组配对bootstrap，seed20260910；区间不含训练种子或供体选择不确定性。四split真实exit0、清单/权重SHA、资格/组数及原统计代码数值回归均通过。SSE采用float64累加。\n\n权重SHA：`'+receipt['checkpoint_sha256']+'`；验收、逐样本路径与SHA：`'+str(d/'statistics_acceptance.json')+'`。\n'
 targets=[R/f'A{50 if v=="B" else 51}_方案{v}_原稿对应表格结果追加记录_20261115.md',R/'A08_E1主表_同协议重跑结果.md']
 for p in targets:
  raw=p.read_bytes();text=raw.decode('utf-8')
  if marker in text:assert md in text;continue
  boundary='### 方案D：现有表格完整数据'
  if p==targets[1] and v=='B':assert text.count(boundary)==1;new=text.replace(boundary,block+'\n'+boundary,1)
  else:new=text+block
  assert p.read_bytes()==raw,'concurrent edit; defer publishing';tmp=p.with_suffix('.e1.tmp');tmp.write_text(new,encoding='utf-8',newline='');tmp.replace(p)
  assert md in p.read_text(encoding='utf-8')
 (d/'published.json').write_text(json.dumps({'status':'PASS','targets':[str(p) for p in targets],'table_rows':8,'sha256':{p.name:sha(p) for p in targets}},ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 snapshot=json.loads((C/'snapshot.json').read_text(encoding='utf-8'));P=snapshot['plan'];published=[]
 for v in ['D','B']:
  d=C/v
  if (d/'published.json').exists():published.append(v);continue
  if not all((d/s/'receipt.json').exists() for s in SPLITS):continue
  stats={};evidence={}
  for i,s in enumerate(SPLITS):
   receipt=json.loads((d/s/'receipt.json').read_text(encoding='utf-8'));a=receipt['result'];p=d/s/'paired_per_horizon.csv'
   assert receipt['exit']['exit']==0 and a['status']=='PASS' and a['variant']==v and a['split']==s and sha(p)==a['csv_sha256'] and a['checkpoint_sha256']==P['models'][v]['sha256']
   rows=list(csv.DictReader(p.open(encoding='utf-8')));assert len(rows)==P['matched_counts'][s]*10==a['rows']
   stat,donors=aggregate(rows)
   mf=E/'legacy_export/corrected_mask_recompute_20260910T071500Z/merged'/OLD[i]/'manifests/matched_donor_manifest.csv';assert sha(mf)==P['manifest_sha'][s]
   pairs={r['relative_path']:r['donor_relative_path'] for r in csv.DictReader(mf.open(encoding='utf-8'))};assert pairs==donors
   for j,scope in enumerate(['suffix','endpoint']):assert (stat[scope]['N'],stat[scope]['Groups'])==(COUNTS[i][j],GROUPS[i][j]),(v,s,scope,stat[scope])
   regression=reference_regression(rows,stat);stats[s]=stat;evidence[s]={'source':receipt,'local_csv':str(p),'regression':regression,'manifest_sha256':sha(mf)}
  lines=['| 窗口 / Window | 划分 / Split | N | 地理组 / Groups | 样本等权 / Sample-equal | 地理组等权 / Group-equal | 像素合并 / Pixel-pooled |','|---|---|---|---|---|---|---|']
  for scope,window in [('suffix','55–100 天 / days'),('endpoint','100 天 / day')]:
   for s,label in zip(SPLITS,LABEL):
    a=stats[s][scope];cells=[f'{p:.6f} [{ci[0]:.6f}, {ci[1]:.6f}]' for p,ci in zip(a['estimates'],a['ci95'])];lines.append('| '+' | '.join([window,label,str(a['N']),str(a['Groups'])]+cells)+' |')
  md='\n'.join(lines)+'\n';(d/'TableE1.md').write_text(md,encoding='utf-8')
  accepted={'status':'PASS','variant':v,'seed':42,'checkpoint_sha256':P['models'][v]['sha256'],'statistics':stats,'evidence':evidence,'bootstrap':{'resamples':2000,'seed':20260910,'unit':'paired receiver geographic group','fixed_matching':True},'table_sha256':sha(d/'TableE1.md')}
  (d/'statistics_acceptance.json').write_text(json.dumps(accepted,ensure_ascii=False,indent=2),encoding='utf-8');publish(v,md,accepted);published.append(v)
 print(json.dumps({'published':published,'complete':len(published)==2}))
if __name__=='__main__':main()
