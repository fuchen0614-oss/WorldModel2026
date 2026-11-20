import pathlib,json,subprocess
r=pathlib.Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_epoch40_seed42_20261114')
o={'files':{},'ps':subprocess.run(['ps','-eo','pid,args'],capture_output=True,text=True).stdout}
o['ps']='\n'.join(x for x in o['ps'].splitlines() if 'epoch40_seed42' in x)
for p in r.rglob('*'):
 if p.is_file() and p.stat().st_size<250000 and (p.name in ['state.json','controller.py','standard_worker.py'] or '/C1/' in str(p) and p.suffix in ['.json','.log']):
  try:o['files'][str(p)]=p.read_text()[-20000:]
  except Exception as e:o['files'][str(p)]=str(e)
print(json.dumps(o))