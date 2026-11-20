import json,base64,gzip
from pathlib import Path
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/D_state_similarity_seed42_20261115_01');o={'runtime':str(R)}
for n in ['state.json','progress.json','exit.json','result.json','plan.json','launch.json']:
 if (R/n).exists():o[n]=json.loads((R/n).read_text())
s=o.get('state.json',{});o['controller_alive']=Path('/proc/'+str(s.get('pid',0))).exists();o['worker_alive']=Path('/proc/'+str(s.get('worker_pid',0))).exists()
if s.get('status')=='complete':
 assert o['exit.json']['exit']==0 and o['result.json']['status']=='PASS'
 o['files']={n:base64.b64encode(gzip.compress((R/n).read_bytes())).decode() for n in ['per_sample.csv','summary.csv']}
if s.get('status')=='failed':o['log_tail']=(R/'worker.log').read_text(errors='replace')[-2500:]
print(json.dumps(o))
