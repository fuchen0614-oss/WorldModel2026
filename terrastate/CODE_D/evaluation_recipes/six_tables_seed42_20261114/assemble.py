import csv,json,hashlib,time,math,shutil,sys
from pathlib import Path
R=Path(sys.argv[1]);P=json.loads((R/'plan.json').read_text());O=R/'tables';O.mkdir(exist_ok=False)
def rows(p):return list(csv.DictReader(Path(p).open()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,r):
 with (O/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(r[0]));w.writeheader();w.writerows(r)
ci=R/'statistics/spatial_ci'
main=rows(ci/'A2_MAIN_DELTA_CI.csv')
for r in main:r['relative_improvement_percent']=100*(float(r['mean_c0r'])-float(r['mean_c1']))/float(r['mean_c0r'])
write('Table1_C1.csv',main)
for src,dst in [('A2_MSE_CI.csv','C1_absolute_MSE_CI.csv'),('A2_DEGRADATION_CI.csv','C2.csv'),('A2_DEGRADATION_MODEL_DIFF_CI.csv','C3.csv'),('A2_ENDPOINT_K10_DELTA_CI.csv','C4.csv')]:shutil.copy2(ci/src,O/dst)
# Eligibility equivalence is checked by stable receiver ID, never dataset index.
manifest=rows(R/'suffix/SAMPLE_MANIFEST.csv');ids={r['dataset_index']:r['receiver_id'] for r in manifest if r['rank']}
new={(ids[r['dataset_index']],int(r['k'])):int(r['n_valid']) for r in rows(R/'suffix/PER_RECEIVER_HORIZON.csv') if r['model']=='C1' and r['path']=='D20'}
old={(r['receiver_id'],int(r['k'])):int(r['n_valid']) for r in rows(R/'legacy_qualification.csv')}
comparable=new==old
previous=rows(R/'legacy_delta.csv');comparison=[]
for n in main:
 o=next(r for r in previous if r['path']==n['path']);op=100*(float(o['mean_c0r'])-float(o['mean_c1']))/float(o['mean_c0r']);np=float(n['relative_improvement_percent'])
 comparison.append(dict(path=n['path'],old_relative_improvement_percent=op,new_relative_improvement_percent=np,change_percentage_points=np-op if comparable else '',qualification_exactly_equal=comparable,scope='each version versus its own matched control; architecture/training/parent/weather baseline changed; not isolated mechanism effect'))
write('old_new_matched_relative.csv',comparison)
(O/'suffix_tables_ready.json').write_text(json.dumps({'status':'PASS','qualification_comparable':comparable,'new_target_keys':len(new),'old_target_keys':len(old),'note':'Single seed42; spatial confidence intervals, not seed SD.'},indent=2))
# Reuse existing official standard jobs. Never launch standard inference here.
deadline=time.monotonic()+12*3600
while not all(Path(p).exists() for p in P['standard_results'].values()):
 if time.monotonic()>deadline:raise TimeoutError('existing standard receipts not complete within 12h')
 (R/'standard_wait.json').write_text(json.dumps({'status':'waiting_existing_standard_receipts','paths':P['standard_results'],'time':time.time()}));time.sleep(60)
standard={};provenance=[];out=[]
for arm,path in P['standard_results'].items():
 d=json.loads(Path(path).read_text());assert d['status']=='PASS' and not d.get('probe',False)
 assert d['checkpoint_sha256']==P['models'][arm]['sha256'] and d['arm']==arm and d['seed']==42
 assert d.get('variant',d.get('model_config',{}).get('variant'))=='D'
 assert len(d['splits'])==4
 for split,v in d['splits'].items():
  assert v['coverage_complete']
  for metric,value in v['metrics'].items():
   assert math.isfinite(value)
   out.append(dict(arm=arm,seed=42,split=split,metric=metric,value=value,checkpoint_sha256=d['checkpoint_sha256']))
 standard[arm]=d;provenance.append(dict(path=path,sha256=sha(path)));shutil.copy2(path,O/(arm+'_standard_receipt.json'))
diff=[]
for split,c1 in standard['C1']['splits'].items():
 c0=standard['C0R']['splits'][split];assert c1['relative_ids_sha256']==c0['relative_ids_sha256'] and c1['count']==c0['count']
 for k,v in c1['metrics'].items():diff.append(dict(split=split,metric=k,C1=v,C0R=c0['metrics'][k],C1_minus_C0R=v-c0['metrics'][k]))
write('B2_B3_standard_all_metrics.csv',out);write('B2_B3_standard_differences.csv',diff)
receipt=dict(status='PASS',seed=42,six_items_complete=True,spatial_ci_not_seed_sd=True,qualification_comparable=comparable,standard_sources=provenance,external_baselines='Reuse A08 existing verified sources; no external reinference; no relabeling as matched ablation',files={p.name:sha(p) for p in O.glob('*.csv')},inference_reused_once=True,manuscript_unmodified=True,figures_generated=False)
(O/'receipt.json').write_text(json.dumps(receipt,indent=2))
