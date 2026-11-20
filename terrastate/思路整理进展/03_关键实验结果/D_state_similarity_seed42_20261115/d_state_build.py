import json,base64,gzip,hashlib
from pathlib import Path
base=Path('_dqueue_20261114');research=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展')
samples=(research/'03_关键实验结果/D_seed42_six_tables_20261114/suffix/SAMPLE_MANIFEST.csv').read_text(encoding='utf-8-sig')
files={'worker.py':(base/'d_state_worker.py').read_text(encoding='utf-8-sig'),'controller.py':(base/'d_state_controller.py').read_text(encoding='utf-8-sig'),'samples.csv':samples}
blob=base64.b64encode(gzip.compress(json.dumps(files).encode())).decode()
script='PAYLOAD='+repr(blob)+'\n'+r'''
import json,base64,gzip,hashlib,subprocess,time
from pathlib import Path
B=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet');R=B/'runtime/D_state_similarity_seed42_20261115_01'
if R.exists():
 print(json.dumps({'existing':True,'runtime':str(R),'state':json.loads((R/'state.json').read_text()) if (R/'state.json').exists() else None}));raise SystemExit
old=B/'runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_six_tables_seed42_20261114'
candidates=[old.parent/'old/best_frozen.pt']
expected='3557ac4b2a14b542effe22262bbae169cec081a0eb45dc8f07401e11c76f1b5b'
found=[p for p in candidates if hashlib.sha256(p.read_bytes()).hexdigest()==expected]
assert len(found)==1,{'candidates':[str(p) for p in candidates],'matches':len(found)}
P=json.loads((B/'runtime/BD_E1_seed42_20261115_01/plan.json').read_text());P['models']={'C1':P['models']['D'],'C0R':{'checkpoint':str(found[0]),'sha256':expected}}
for j in P['models'].values():assert hashlib.sha256(Path(j['checkpoint']).read_bytes()).hexdigest()==j['sha256']
P['runtime']=str(R);P['gpu_uuid']=P['gpu_uuids'][3];P['scope']='D seed42 paired internal state analysis; day50; existing IID suffix manifest; no training, manuscript changes or plots'
R.mkdir();files=json.loads(gzip.decompress(base64.b64decode(PAYLOAD)))
for n,s in files.items():(R/n).write_text(s)
P['manifest_sha256']=hashlib.sha256((R/'samples.csv').read_bytes()).hexdigest();P['code_hashes']={n:hashlib.sha256((Path(P['code'])/n).read_bytes()).hexdigest() for n in ['models/spanworld_full_base.py','models/plan_b_b4.py']};(R/'plan.json').write_text(json.dumps(P,indent=2))
with (R/'controller.log').open('ab') as f:q=subprocess.Popen(['/usr/bin/python3',str(R/'controller.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(R/'launch.json').write_text(json.dumps({'pid':q.pid,'time':time.time()}));time.sleep(20)
o={'runtime':str(R),'pid':q.pid,'controller_exit':q.poll(),'plan':P}
for n in ['state.json','progress.json','exit.json','result.json']:
 if (R/n).exists():o[n]=json.loads((R/n).read_text())
o['log_tail']=(R/'worker.log').read_text(errors='replace')[-1800:] if (R/'worker.log').exists() else '';print(json.dumps(o))
'''
(base/'d_state_deploy.py').write_text(script,encoding='utf-8')
print('deployment prepared')
