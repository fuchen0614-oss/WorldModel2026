from pathlib import Path
import json,csv,io,subprocess,time,os,traceback
R=Path('E:\\MineProgram\\codexwork\\CVPRAAAI投稿\\WorldModel2026v2\\terrastate\\思路整理进展'); A=Path(__file__).parent; D=A.parent
remote="import pathlib,json\np=pathlib.Path('/shared/smartbot/chengjuntao/maker/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/runtime/spanworld_D_multiseed_909_D_C0R_s97_20261114_01/eval_code_epoch40_seed42_20261114/C1_missing_fixed40_20261115')\no={}\nfor n in ['state.json','result.json','acceptance.json','summary.csv','iid_chopped/exit.json','ood-t_chopped/exit.json']:\n if (p/n).exists():o[n]=(p/n).read_text()\nprint(json.dumps(o))\n"
state=A/'finalizer_state.json'
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
try:
 for attempt in range(1,10):
  put(state,{'status':'fetching','pid':os.getpid(),'attempt':attempt})
  q=subprocess.run(['ssh','-F','C:\\Users\\32084\\Documents\\CVPRAAAI投稿2\\_harness_supervision_20261023\\eo_chain_20261112\\ssh_serial_audit.conf','-o','ConnectTimeout=120','gpu909-audit','python3 -'],input=remote,text=True,encoding='utf-8',capture_output=True,timeout=360)
  put(A/'completion_fetch.json',{'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr})
  if q.returncode==0:
   data=json.loads(q.stdout);st=json.loads(data.get('state.json','{}'))
   if st.get('status')=='failed':raise RuntimeError(st.get('error'))
   if st.get('status')=='complete':break
   put(state,{'status':'waiting_completion','pid':os.getpid(),'attempt':attempt,'remote':st})
  else:put(state,{'status':'waiting_connection','pid':os.getpid(),'attempt':attempt,'stderr':q.stderr})
  time.sleep(1800 if attempt==1 else 10800)
 else:raise RuntimeError('bounded retrieval limit; inspect existing task without rerun')
 result=json.loads(data['result.json']);acc=json.loads(data['acceptance.json'])
 assert result['status']==acc['status']=='PASS' and result['arm']=='C1' and result['epoch']==40 and result['step']==29800
 assert all(v==0 for v in acc['new_workers'].values()) and result['total_samples']==22320
 dest=D/'C1_standard';dest.mkdir(exist_ok=True)
 for name,content in data.items():
  f=dest/name;f.parent.mkdir(exist_ok=True,parents=True);f.write_text(content,encoding='utf-8')
 base=json.loads((D/'baseline_standard/result.json').read_text(encoding='utf-8'));rows=[]
 for split in ['iid_chopped','ood-t_chopped','ood-s_chopped','ood-st_chopped']:
  c=result['splits'][split];b=base['splits'][split]
  assert c['count']==b['count'] and c['coverage_complete'] and b['coverage_complete']
  assert c['relative_ids_sha256']==b['relative_ids_sha256']
  rows.append(dict(split=split,C1_RMSE=c['metrics']['rmse'],BASELINE_RMSE=b['metrics']['rmse'],delta_RMSE=c['metrics']['rmse']-b['metrics']['rmse'],C1_R2=c['metrics']['R2'],BASELINE_R2=b['metrics']['R2'],delta_R2=c['metrics']['R2']-b['metrics']['R2'],seed=42,epoch=40,C1_SHA=result['checkpoint_sha256'],BASELINE_SHA=base['checkpoint_sha256']))
 buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);(D/'B_standard_fixed40.csv').write_text(buf.getvalue(),encoding='utf-8')
 lines=['| Split | C1 RMSE | Base RMSE | C1 R2 | Base R2 |','|---|---:|---:|---:|---:|']
 for x in rows:lines.append('| '+x['split']+' | '+' | '.join(f"{x[k]:.9f}" for k in ['C1_RMSE','BASELINE_RMSE','C1_R2','BASELINE_R2'])+' |')
 report='# D fixed40 ablation B: verified\n\n'+ '\n'.join(lines)+'\n\nSeed42, epoch40/step29800; shared coverage verified. IID/OOD-T new worker exit0; OOD-S/ST reuse with exact coverage/aggregation verification. No baseline reevaluation.\n'
 (D/'B_RESULTS.md').write_text(report,encoding='utf-8')
 idx=R/'执行交接/统一管理/experiment_index.json';j=json.loads(idx.read_text(encoding='utf-8'));j['D_C1_fixed40_writer_audit_20261115'].update(status='complete',table_B=str(D/'B_standard_fixed40.csv'),receipt=str(dest/'acceptance.json'));put(idx,j)
 p=R/'A08_E1主表_同协议重跑结果.md';t=p.read_bytes().decode('utf-8');marker='<!-- D_FIXED40_B_COMPLETE_20261115 -->'
 if marker not in t:
  t+='\n\n## D固定40轮消融B已验收（2026-11-15）\n'+marker+'\n\n'+ '\n'.join(lines)+'\n\n[完整CSV](03_关键实验结果/D_seed42_fixed40_20261114/B_standard_fixed40.csv)；[验收](03_关键实验结果/D_seed42_fixed40_20261114/C1_standard/acceptance.json)。IID/OOD-T增量补齐exit0，OOD-S/ST复用并核对覆盖/聚合；基础框架未重做。seed42单种子，不声称跨种子结论。\n';p.write_bytes(t.encode('utf-8'))
 put(state,{'status':'complete','pid':os.getpid(),'table_B':str(D/'B_standard_fixed40.csv')})
except BaseException:put(state,{'status':'failed','pid':os.getpid(),'error':traceback.format_exc()});raise
