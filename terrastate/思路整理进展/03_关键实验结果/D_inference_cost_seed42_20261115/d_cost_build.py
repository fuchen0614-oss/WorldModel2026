from pathlib import Path
import json,base64,gzip,csv
b=Path('_dqueue_20261114');r=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展');p=r/'03_关键实验结果/D_seed42_six_tables_20261114/suffix/SAMPLE_MANIFEST.csv';rows=[x for x in csv.DictReader(p.open(encoding='utf-8-sig')) if x['selection']=='stable_id_sorted_full_IID_suffix_total_valid_positive'];samples=[x['receiver_id'] for x in rows[:8]]
files={n:(b/('d_cost_'+n)).read_text(encoding='utf-8-sig') for n in ['worker.py','controller.py']};blob=base64.b64encode(gzip.compress(json.dumps(files).encode())).decode()
s='BLOB='+repr(blob)+'\nSAMPLES='+repr(samples)+'\n'+r'''
from pathlib import Path
import json,base64,gzip,subprocess,time,os,hashlib
B=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet');R=B/'runtime/D_inference_cost_seed42_20261115_01'
if R.exists():
 print(json.dumps({'existing':True,'runtime':str(R),'state':json.loads((R/'state.json').read_text()) if (R/'state.json').exists() else None}));raise SystemExit
P=json.loads((B/'runtime/D_state_similarity_seed42_20261115_01/plan.json').read_text());P.update(runtime=str(R),samples=SAMPLES,sample_selection='first eight accepted receiver IDs in existing stable IID suffix manifest; selected before timing',scope='D-C1 seed42 best51; matched direct and15+35-then-continuation day55..100 inference cost only; no training or manuscript changes',gpu_candidates=P['gpu_uuids'])
assert Path(P['python']).exists() and Path(P['code']).exists();assert hashlib.sha256(Path(P['models']['C1']['checkpoint']).read_bytes()).hexdigest()==P['models']['C1']['sha256'];R.mkdir()
for n,s in json.loads(gzip.decompress(base64.b64decode(BLOB))).items():(R/n).write_text(s)
P['worker_sha256']=hashlib.sha256((R/'worker.py').read_bytes()).hexdigest();(R/'plan.json').write_text(json.dumps(P,indent=2))
env=dict(os.environ,CUDA_VISIBLE_DEVICES=P['gpu_uuid'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
q=subprocess.run([P['python'],str(R/'worker.py'),'--validate-only'],cwd=R,env=env,capture_output=True,text=True,timeout=120);(R/'numerical_exit.json').write_text(json.dumps({'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr}));assert q.returncode==0,q.stderr[-2500:]
with (R/'controller.log').open('ab') as f:c=subprocess.Popen(['/usr/bin/python3',str(R/'controller.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(R/'launch.json').write_text(json.dumps({'pid':c.pid,'time':time.time()}));time.sleep(3)
o={'runtime':str(R),'controller_pid':c.pid,'controller_exit':c.poll(),'plan':P,'numerical_validation':json.loads((R/'numerical_equivalence.json').read_text())}
for n in ['state.json','progress.json','result.json','exit.json']:
 if (R/n).exists():o[n]=json.loads((R/n).read_text())
print(json.dumps(o))
'''
(b/'d_cost_deploy.py').write_text(s,encoding='utf-8')
