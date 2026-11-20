import pathlib,json,subprocess
r=pathlib.Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_epoch40_seed42_20261114')
o={'plan':json.loads((r/'baseline_B_fixed40_completion_20261114/plan.json').read_text()),'gpu':subprocess.run(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader'],capture_output=True,text=True).stdout,'ps':subprocess.run(['ps','-eo','pid,args'],capture_output=True,text=True).stdout,'files':{}}
o['ps']='\n'.join(x for x in o['ps'].splitlines() if 'eval_fixed40' in x or 'controller.py' in x or 'keeper' in x)
for name in ['frozen/C1.json','recovery_v1/continuation/state.json']:
 p=r/name
 if p.exists():o['files'][name]=p.read_text()
print(json.dumps(o))