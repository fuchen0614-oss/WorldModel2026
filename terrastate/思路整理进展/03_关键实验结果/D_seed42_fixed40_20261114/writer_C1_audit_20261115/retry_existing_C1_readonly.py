import pathlib,json,subprocess,time,os
from datetime import datetime,timezone
R=pathlib.Path(__file__).parent
state=R/'connection_retry_state.json'
remote="""import pathlib,json,datetime
r=pathlib.Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_epoch40_seed42_20261114')
out={'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{}}
for p in r.rglob('*'):
 if p.is_file() and p.name in ['state.json','progress.json','exit.json','receipt.json','acceptance.json','result.json','summary.csv','scientific_judgments.json'] and p.stat().st_size<250000:
  if '/C1/' in str(p) or 'tables' in str(p) or p.name=='state.json':
   try:out['files'][str(p)]=p.read_text()
   except Exception as e:out['files'][str(p)]={'read_error':str(e)}
print(json.dumps(out))
"""
def save(obj):
 obj.update(pid=os.getpid(),time=datetime.now(timezone.utc).isoformat())
 tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(state)
for attempt in range(1,241):
 if (R/'STOP_CONNECTION_RETRY').exists():save({'status':'stopped','attempt':attempt});break
 save({'status':'connecting','attempt':attempt,'interval_seconds':180,'max_attempts':240})
 cmd=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','4090_QianRui_909','python3 -']
 try:
  p=subprocess.run(cmd,input=remote,text=True,encoding='utf-8',capture_output=True,timeout=90)
  rec={'attempt':attempt,'exit':p.returncode,'stderr':p.stderr,'stdout':p.stdout}
  if p.returncode==0:
   payload=json.loads(p.stdout)
   (R/'remote_C1_retrieval.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
   save({'status':'retrieved_pending_validation','attempt':attempt,'result':str(R/'remote_C1_retrieval.json'),'files':len(payload.get('files',{})),'evaluation_launched':False});break
  save({'status':'waiting_retry','attempt':attempt,'last_error':p.stderr[-1200:]})
 except Exception as e:save({'status':'waiting_retry','attempt':attempt,'last_error':str(e)})
 time.sleep(180)
else:save({'status':'retry_limit_reached','attempts':240})
