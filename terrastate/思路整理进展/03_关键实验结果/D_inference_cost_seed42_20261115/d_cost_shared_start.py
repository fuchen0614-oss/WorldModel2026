import json,os,signal,time,subprocess,hashlib
from pathlib import Path
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/D_inference_cost_seed42_20261115_01');s=json.loads((R/'state.json').read_text())
if s['status'] in ['running','complete']:
 print(json.dumps({'existing':s,'action':'preserved active/completed task'}));raise SystemExit
assert s['status']=='waiting_for_exclusive_gpu',s
pid=s['pid'];proc=Path('/proc/'+str(pid)+'/cmdline')
if proc.exists():
 cmd=proc.read_bytes();assert str(R/'controller.py').encode() in cmd;os.kill(pid,signal.SIGTERM);time.sleep(1)
assert not any(str(R/'worker.py') in line for line in subprocess.check_output(['ps','-eo','args'],text=True).splitlines()),'existing worker: do not duplicate'
a=R/'exclusive_wait_before_shared';a.mkdir(exist_ok=False)
for n in ['state.json','controller.py','worker.py','plan.json','launch.json']:(a/n).write_bytes((R/n).read_bytes())
p=R/'worker.py';w=p.read_text();w=w.replace("assert VALIDATE_ONLY or not others(),'GPU shared before timing'","sharing=[{'stage':'start','other_compute_processes':others()}]").replace("assert VALIDATE_ONLY or not others(),'GPU shared before sample'","sharing.append({'stage':'sample_start','sample_index':si,'other_compute_processes':others()})").replace("assert not others(),'GPU sharing detected during timing'","sharing.append({'stage':'mode_end','sample_index':si,'mode':mode,'other_compute_processes':others()})").replace("'gpu_exclusive_checks':'no other compute PID at each sample start and after every mode'","'gpu_environment':'shared GPU; latency is descriptive under concurrent load, not isolated hardware latency','sharing_snapshots':sharing")
p.write_text(w)
p=R/'controller.py';w=p.read_text();a1=w.index(' while True:');b=w.index(' env=dict',a1);w=w[:a1]+w[b:];p.write_text(w)
p=R/'plan.json';P=json.loads(p.read_text());P['measurement_environment']='shared_GPU_user_authorized';P['worker_sha256']=hashlib.sha256((R/'worker.py').read_bytes()).hexdigest();p.write_text(json.dumps(P,indent=2))
with (R/'controller_shared.log').open('ab') as f:q=subprocess.Popen(['/usr/bin/python3',str(R/'controller.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(R/'launch_shared.json').write_text(json.dumps({'pid':q.pid,'time':time.time(),'replaces_wait_controller':pid}));time.sleep(20)
o={'controller_pid':q.pid,'controller_exit':q.poll(),'state':json.loads((R/'state.json').read_text())}
for n in ['progress.json','exit.json','result.json']:
 if (R/n).exists():o[n]=json.loads((R/n).read_text())
o['log_tail']=(R/'worker.log').read_text(errors='replace')[-1500:] if (R/'worker.log').exists() else '';print(json.dumps(o))
