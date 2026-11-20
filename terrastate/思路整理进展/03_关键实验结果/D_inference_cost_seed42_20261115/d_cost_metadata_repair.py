from pathlib import Path
import json,subprocess,time
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/D_inference_cost_seed42_20261115_01');s=json.loads((R/'state.json').read_text());assert s['status']=='failed';assert not Path('/proc/'+str(s['pid'])).exists();a=R/'attempt_shared_device_metadata_error';a.mkdir()
for n in ['worker.py','worker.log','controller_shared.log','controller.log','state.json','exit.json','progress.json','timings.csv','summary.csv']:
 if (R/n).exists():(a/n).write_bytes((R/n).read_bytes())
p=R/'worker.py';w=p.read_text().replace('torch.cuda.get_device_name()','torch.cuda.get_device_name(0)');p.write_text(w)
for n in ['timings.csv','summary.csv']:(R/n).rename(a/(n+'.preserved'))
with (R/'controller_repair.log').open('ab') as f:q=subprocess.Popen(['/usr/bin/python3',str(R/'controller.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(R/'repair_launch.json').write_text(json.dumps({'pid':q.pid,'time':time.time(),'fix':'explicit device0 for GPU name; original exit1 and files preserved'}));time.sleep(5);print(json.dumps({'pid':q.pid,'state':json.loads((R/'state.json').read_text())}))
