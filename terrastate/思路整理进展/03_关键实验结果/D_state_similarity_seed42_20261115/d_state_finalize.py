import json,base64,gzip,hashlib,csv,io,statistics,datetime,shutil
from pathlib import Path
r=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展');e=r/'03_关键实验结果/D_state_similarity_seed42_20261115';p=Path('_dqueue_20261114/d_state_latest.json');v=json.loads(p.read_text(encoding='utf-8'));assert v['exit']==0,v.get('stderr');x=json.loads(v['stdout']);state=x['state.json'];status=state['status'];now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M');print('time',now,'status',status,'progress',x.get('progress.json'),'exit',x.get('exit.json'))
shutil.copy2(p,e/'latest_collection.json')
for n in ['state.json','progress.json','exit.json','result.json']:
 if n in x:(e/n).write_text(json.dumps(x[n],ensure_ascii=False,indent=2),encoding='utf-8')
if status=='complete':
 assert x['exit.json']['exit']==0 and x['result.json']['status']=='PASS';res=x['result.json'];raws={n:gzip.decompress(base64.b64decode(b)) for n,b in x['files'].items()}
 for n,k in [('per_sample.csv','csv_sha256'),('summary.csv','summary_sha256')]:assert hashlib.sha256(raws[n]).hexdigest()==res[k]
 manifest=(e/'d_state_build.py').exists();plan=x['plan.json'];src=r/'03_关键实验结果/D_seed42_six_tables_20261114/suffix/SAMPLE_MANIFEST.csv';txt=src.read_text(encoding='utf-8-sig');assert hashlib.sha256(txt.encode()).hexdigest()==res['manifest_sha256'];ids={a['receiver_id'] for a in csv.DictReader(io.StringIO(txt)) if a['selection']=='stable_id_sorted_full_IID_suffix_total_valid_positive'};assert len(ids)==2837
 rows=list(csv.DictReader(io.StringIO(raws['per_sample.csv'].decode())));assert len(rows)==11348
 for arm in ['C1','C0R']:
  for path in ['25+25','15+35']:
   sub=[a for a in rows if a['arm']==arm and a['path_days']==path];assert len(sub)==2837 and {a['receiver_id'] for a in sub}==ids;assert all(int(a['zero_norm_tokens'])==0 for a in sub)
   for field,metric in [('cosine','cosine_mean'),('state_rmse','state_rmse_mean')]:assert abs(statistics.mean(float(a[field]) for a in sub)-res['summary'][arm+'/'+path][metric])<1e-12
 for n,b in raws.items():(e/n).write_bytes(b)
 receipt={'status':'PASS','time':now,'real_exit':0,'paired_samples':2837,'per_sample_rows':11348,'csv_sha_verified':True,'exact_accepted_receiver_set_verified':True,'aggregation_recomputed':True,'models':res['models']};(e/'local_acceptance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
 print('SUMMARY',raws['summary.csv'].decode())
 p=r/'A08_E1主表_同协议重跑结果.md';s=p.read_text(encoding='utf-8');heading='## 2026-11-15 D seed42 状态相似度正式验收'
 if heading not in s:
  s+='\n\n'+heading+'\n\n'+now+'：远端真实exit0；2837个IID样本×2模型×2路径共11348行已完整取回，receiver集合与既有共同后缀清单一致，无重复；SHA及聚合重算通过。单配对seed42，同模型内部比较，不作为物理状态证明或跨模型坐标距离。\n\n|第50天路径|C1余弦|C0R余弦|C1状态RMSE|C0R状态RMSE|\n|---|---:|---:|---:|---:|\n'
  for path in ['25+25','15+35']:
   a=res['summary']['C1/'+path];b=res['summary']['C0R/'+path];s+=f"|{path}|{a['cosine_mean']:.9f}|{b['cosine_mean']:.9f}|{a['state_rmse_mean']:.9f}|{b['state_rmse_mean']:.9f}|\n"
  s+='\n余弦先逐空间token按通道计算，再样本内、样本间等权平均；状态RMSE仅描述各模型内部路径差异。正文与审稿回复未修改，解释及入稿待讨论。\n\n[汇总CSV](03_关键实验结果/D_state_similarity_seed42_20261115/summary.csv)；[本地验收](03_关键实验结果/D_state_similarity_seed42_20261115/local_acceptance.json)。\n';p.write_text(s,encoding='utf-8')
else:print('DETAIL',x.get('log_tail',''), 'alive', x.get('controller_alive'),x.get('worker_alive'))
p=r/'执行交接/统一管理/experiment_index.json';j=json.loads(p.read_text(encoding='utf-8-sig'));entry=j['D_state_similarity_seed42_20261115_01'];entry.update(status='PASS_archived' if status=='complete' else status,updated=now,progress=x.get('progress.json'),latest_evidence=str(e/'latest_collection.json'));p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=r/'执行交接/额度优化_20261026/MANUSCRIPT_STATE.txt';s=p.read_text(encoding='utf-8');s=s.split('\n本次状态核查：')[0];s+='\n本次状态核查：'+now+'，'+('状态分析完成且本地验收PASS，2837样本/11348行，真实exit0；summary.csv/per_sample.csv已取回，A08和统一索引已同步。下一步展示原问、结果解释与正文/回复候选供用户审核，暂未改稿。' if status=='complete' else 'status='+status+'；progress='+str(x.get('progress.json',{}).get('done'))+'/2837。当前回执见证据目录latest_collection.json。')+'\n';p.write_text(s,encoding='utf-8')
