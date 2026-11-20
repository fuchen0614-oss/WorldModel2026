from pathlib import Path
import json,time,hashlib,gzip,base64,os
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/BD_E1_seed42_20261115_01')
P=json.loads((R/'plan.json').read_text());S=json.loads((R/'state.json').read_text())
o={'time':time.time(),'runtime':str(R),'state':S,'plan':P,'progress':{},'outputs':{},'controller_alive':Path('/proc/'+str(S['pid'])).exists()}
for v in ['D','B']:
 for s in P['splits']:
  d=R/v/s
  for n in ['progress.json','protocol_PASS.json']:
   if (d/n).exists():o['progress'][v+'/'+s+'/'+n]=json.loads((d/n).read_text())
  ep=R/(v+'_'+s+'_exit.json')
  if ep.exists() and (d/'result.json').exists():
   e=json.loads(ep.read_text());a=json.loads((d/'result.json').read_text())
   assert e['exit']==0 and a['status']=='PASS'
   raw=(d/'paired_per_horizon.csv').read_bytes();assert hashlib.sha256(raw).hexdigest()==a['csv_sha256']
   o['outputs'][v+'/'+s]={'exit':e,'result':a,'path':str(d/'paired_per_horizon.csv'),'gzip_base64':base64.b64encode(gzip.compress(raw)).decode()}
if S['status']=='failed':
 o['log_tails']={p.name:p.read_text(errors='replace')[-2000:] for p in R.glob('*.log')}
print(json.dumps(o))
