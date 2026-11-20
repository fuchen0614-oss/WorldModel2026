from pathlib import Path
import json,csv,math,hashlib,shutil,subprocess,os,time,fcntl
R=Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/BD_E1_seed42_20261115_01');P=json.loads((R/'plan.json').read_text())
lock=(R/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
for p in Path('/proc').glob('[0-9]*'):
 try:c=(p/'cmdline').read_bytes().decode(errors='replace')
 except OSError:continue
 assert not (str(R) in c and ('worker' in c or 'controller' in c)),(p.name,c)
report={};stamp=str(int(time.time()))
for v in ['B','D']:
 for split in P['splits']:
  d=R/v/split;rp=d/'result.json'
  if rp.exists():
   a=json.loads(rp.read_text());assert a['status']=='PASS';assert json.loads((R/(v+'_'+split+'_exit.json')).read_text())['exit']==0;assert hashlib.sha256((d/'paired_per_horizon.csv').read_bytes()).hexdigest()==a['csv_sha256'];continue
  pairs=list(csv.DictReader((R/'manifests'/(split+'.csv')).open()));f=d/'paired_per_horizon.csv';backup=d/('interrupted_'+stamp+'.csv');shutil.copy2(f,backup)
  rows=list(csv.DictReader(f.open()));fields=list(rows[0]);good=[];counts={'suffix':0,'day100':0}
  for i in range(len(rows)//10):
   chunk=rows[i*10:i*10+10];pair=pairs[i]
   assert all(r['receiver_id']==pair['relative_path'] and r['donor_id']==pair['donor_relative_path'] for r in chunk)
   assert [int(r['k']) for r in chunk]==list(range(1,11))
   for r in chunk:
    assert int(r['n_valid'])>=0 and all(math.isfinite(float(r[k])) and float(r[k])>=0 for k in ['original_sse','donor_sse'])
   counts['suffix']+=int(sum(int(r['n_valid']) for r in chunk)>0);counts['day100']+=int(int(chunk[-1]['n_valid'])>0);good.extend(chunk)
  tmp=d/'resume_data.tmp'
  with tmp.open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(good)
  tmp.replace(f);resume={'complete_pairs':len(good)//10,'counts':counts,'prior_seconds':json.loads((d/'progress.json').read_text())['seconds'],'backup':str(backup),'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest()};(d/'resume.json').write_text(json.dumps(resume));report[v+'/'+split]=resume
for name,content in PAYLOAD.items():(R/name).write_text(content)
shutil.copy2(R/'state.json',R/('state_before_resume_'+stamp+'.json'));lock.close()
log=(R/'controller_resume.log').open('ab');q=subprocess.Popen(['/usr/bin/python3',str(R/'controller_resume.py')],cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(R/'resume_launch.json').write_text(json.dumps({'pid':q.pid,'time':time.time(),'resume':report}))
time.sleep(25);print(json.dumps({'pid':q.pid,'exit':q.poll(),'resume':report,'state':json.loads((R/'state.json').read_text()),'log':(R/'controller_resume.log').read_text()[-1500:]}))
