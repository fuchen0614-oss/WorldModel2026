from pathlib import Path
import json,base64,gzip
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/D_inference_cost_seed42_20261115_01');o={'runtime':str(R)}
for n in ['state.json','progress.json','plan.json','result.json','exit.json','numerical_equivalence.json','numerical_exit.json','launch.json']:
 if (R/n).exists():o[n]=json.loads((R/n).read_text())
s=o.get('state.json',{});o['controller_alive']=Path('/proc/'+str(s.get('pid',0))).exists()
if s.get('status')=='complete':
 assert o['exit.json']['exit']==0 and o['result.json']['status']=='PASS';o['files']={n:base64.b64encode(gzip.compress((R/n).read_bytes())).decode() for n in ['timings.csv','summary.csv']}
if s.get('status')=='failed':o['log_tail']=(R/'worker.log').read_text(errors='replace')[-2000:] if (R/'worker.log').exists() else ''
print(json.dumps(o))
