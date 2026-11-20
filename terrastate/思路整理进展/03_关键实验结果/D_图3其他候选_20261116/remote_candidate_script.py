P={'python': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/envs/SpanWorld/bin/python', 'gpu_uuid': 'GPU-a0f1ac63-09d2-121e-0a8c-e07289f945cf', 'guard_recognition_prefix': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code', 'data_root': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/migration_data/stage2_dc_eval_20261113_01/iid_chopped', 'parent_sha256': '438e8d93505827ce2a1b7ffaef78b64e46e5d65920cf79af25305af5b72e10fb', 'models': {'C1': {'checkpoint': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/weights/retrained_spanworld/spanworld_D909_fast4x8_20261113_01/D/formal/best_val.pt', 'sha256': 'a7afea7307f87c282df02485f9107fccccc88119ed37e9c023d7280d61b08fdb'}, 'C0R': {'checkpoint': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/weights/retrained_spanworld/spanworld_C0R_selected_seed42_20261113_01/D/formal/best_val.pt', 'sha256': '3557ac4b2a14b542effe22262bbae169cec081a0eb45dc8f07401e11c76f1b5b'}}, 'standard_results': {'C1': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/evaluation/spanworld_D909_fast4x8_20261113_01/D/result.json', 'C0R': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/old/result.json'}, 'source_runtime': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_six_tables_seed42_20261114/suffix', 'code': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_B51_six_tables_seed42_20261114/code', 'oss': '/oss-chengjuntao/makerdata/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/figure_candidates/D_figure3_P42_20261116/raw', 'runtime': '/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/D_figure3_P42_20261116'}
PATHS={'C1': ['/oss-chengjuntao/makerdata/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/weights/retrained_spanworld/spanworld_D909_fast4x8_20261113_01/D/formal/best_val.pt'], 'C0R': ['/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/weights/retrained_spanworld/spanworld_C0R_selected_seed42_20261113_01/D/formal/best_val.pt']}
from pathlib import Path
import os,json,subprocess,hashlib,time,shutil
old=Path(P['runtime']);R=old.with_name(old.name+'_candidates_v1');O=Path(P['oss']).parent.with_name(Path(P['oss']).parent.name+'_candidates_v1')/'raw'
def emit(d):print(json.dumps(d),flush=True)
if R.exists():
 emit(dict(status='EXISTING_NO_REDISPATCH',launch=json.loads((R/'launch.json').read_text()) if (R/'launch.json').exists() else None,state=json.loads((O/'state.json').read_text()) if (O/'state.json').exists() else None));raise SystemExit(0)
active=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  cmd=p.read_bytes().replace(bytes([0]),b' ').decode(errors='replace')
  if str(old/'worker.py') in cmd or str(R/'worker.py') in cmd:active.append(dict(pid=int(p.parent.name),cmd=cmd))
 except OSError:pass
if active:emit(dict(status='ACTIVE_NO_REDISPATCH',active=active));raise SystemExit(0)
verified={}
for arm,candidates in PATHS.items():
 for name in candidates:
  p=Path(name)
  if p.is_file():
   h=hashlib.sha256(p.read_bytes()).hexdigest()
   if h==P['models'][arm]['sha256']:P['models'][arm]['checkpoint']=str(p);verified[arm]=dict(path=str(p),sha256=h);break
 assert arm in verified,('MISSING_VERIFIED_WEIGHT',arm,candidates)
R.mkdir();P.update(runtime=str(R),oss=str(O))
for name in ['worker.py','historical_cases.json','select_cases.py']:shutil.copy2(old/name,R/name)
worker=(R/'worker.py').read_text();worker=worker.replace("np.savez_compressed(dest/'arrays.npz',**arr)","buffer=__import__('io').BytesIO();np.savez_compressed(buffer,**arr);blob=buffer.getvalue();(dest/'arrays.npz').write_bytes(blob);assert sha(dest/'arrays.npz')==hashlib.sha256(blob).hexdigest();np.load(__import__('io').BytesIO((dest/'arrays.npz').read_bytes())).close()");worker=worker.replace("cases=[c for c in cases if c['id']=='P42'];assert len(cases)==1", "cases=[c for c in cases if c['id']!='P42'];assert len({c['receiver_id'] for c in cases})==len(cases)")
worker=worker.replace("  checks=[]", "  if float(valid[19].mean())<.4:unavailable.append(dict(id=c['id'],receiver_id=c['receiver_id'],day=100,coverage=float(valid[19].mean()),reason='day100 valid coverage below .40'));put('excluded_day100.json',unavailable);continue\n  checks=[]")
compile(worker,'candidate_worker','exec');(R/'worker.py').write_text(worker);

(R/'plan.json').write_text(json.dumps(P));(R/'verified_weights.json').write_text(json.dumps(verified))
cards=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True);gpu,free=max([tuple(map(int,r.split(','))) for r in cards.splitlines()],key=lambda x:x[1]);assert free>=6500,cards
f=(R/'worker.log').open('ab');p=subprocess.Popen([P['python'],'-u',str(R/'worker.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='1'))
launch=dict(pid=p.pid,gpu=gpu,runtime=str(R),output=str(O),time=time.time(),verified_weights=verified);(R/'launch.json').write_text(json.dumps(launch));emit(dict(event='LAUNCHED',**launch))
try:code=p.wait(timeout=600)
except subprocess.TimeoutExpired:emit(dict(event='STILL_RUNNING',pid=p.pid,output=str(O)));raise SystemExit(0)
result=dict(event='FINISHED',business_exit=code,launch=launch,receipt=json.loads((O/'receipt.json').read_text()) if (O/'receipt.json').exists() else None,log_tail=(R/'worker.log').read_text(errors='replace')[-3500:]);(R/'supervisor_exit.json').write_text(json.dumps(result));emit(result)

if code==0:
 (R/"pack_day100.py").write_text("from pathlib import Path\nimport numpy as np,io,json,hashlib,base64,zipfile,sys\nroot=Path(sys.argv[1]);buf=io.BytesIO();records=[]\nwith zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:\n for p in sorted((root/'cases').iterdir()):\n  meta=json.loads((p/'metadata.json').read_text());full=(p/'arrays.npz').read_bytes();h=hashlib.sha256(full).hexdigest();assert h==meta['arrays_sha256']\n  ix={'gt':19,'valid':19,'C1_direct':19,'C0R_direct':19,'C1_continued':9,'C0R_continued':9}\n  with np.load(io.BytesIO(full)) as a:frames={k:a[k][i].copy() for k,i in ix.items()}\n  assert frames['valid'].mean()>=.4\n  b=io.BytesIO();np.savez_compressed(b,**frames);blob=b.getvalue();name=p.name;rec=dict(case=name,metadata=meta,source_full_sha256=h,subset_sha256=hashlib.sha256(blob).hexdigest(),indices=ix)\n  z.writestr(name+'/frames.npz',blob);z.writestr(name+'/metadata.json',json.dumps(rec));records.append(name)\n for name in ['selection.json','case_manifest.json','excluded_day100.json','receipt.json']:\n  if (root/name).exists():z.writestr(name,(root/name).read_bytes())\nprint('PACKAGE:'+base64.b64encode(buf.getvalue()).decode(),flush=True)\n")
 subprocess.run([P["python"],str(R/"pack_day100.py"),str(O)],check=True)
