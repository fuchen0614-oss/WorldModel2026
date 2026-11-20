from pathlib import Path
import json,hashlib,shutil
import numpy as np
from f1_stats_pure import _boot,_cluster_boot
R=Path(r'E:\MineProgram\codexwork\CVPRAAAI投稿\WorldModel2026v2\terrastate\思路整理进展');O=R/'03_关键实验结果/BD_原稿全表复刻_20261115';W=Path(__file__).parent
outer=json.loads((W/'bd_f1_collect.json').read_text(encoding='utf-8'));assert outer['exit']==0;S=json.loads(outer['stdout']);assert S['state']['status']=='complete'
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)
def append(v,block,marker):
 for p in [R/f'A{51 if v=="D" else 50}_方案{v}_原稿对应表格结果追加记录_20261115.md',R/'A08_E1主表_同协议重跑结果.md']:
  raw=p.read_bytes();t=raw.decode('utf-8')
  if marker in t:continue
  if p.name.startswith('A08') and v=='B':
   boundary='### 方案D：现有表格完整数据';assert t.count(boundary)==1;new=t.replace(boundary,block+'\n'+boundary,1)
  else:new=t+block
  assert p.read_bytes()==raw;tmp=p.with_suffix('.f1.tmp');tmp.write_text(new,encoding='utf-8',newline='');tmp.replace(p);assert block in p.read_text(encoding='utf-8')
for v in ['D','B']:
 x=S['variants'][v];assert x['exit']['exit']==0 and x['result.json']['status']=='PASS';rows=x['per_pair.json'];assert len(rows)==84 and len(set(r['extreme'] for r in rows))==84 and len(set(r['control'] for r in rows))==45 and len(set(r['tile'] for r in rows))==31
 assert hashlib.sha256(json.dumps(rows,allow_nan=False,default=str).encode()).hexdigest()==x['result.json']['per_pair_sha256']
 d=O/'F1'/v;d.mkdir(parents=True,exist_ok=True);(d/'receipt.json').write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');out=[];stats=[]
 for label,arm,interaction in [('供体−实际 / Donor−actual','donor',False),('均值−实际 / Mean−actual','mean',False),('供体替换：热旱−正常 / Donor effect: hot-dry−normal','donor',True),('均值替换：热旱−正常 / Mean effect: hot-dry−normal','mean',True)]:
  vals=[r['loss_e'][arm]-r['loss_e']['actual']-(r['loss_c'][arm]-r['loss_c']['actual'] if interaction else 0) for r in rows];assert np.isfinite(vals).all()
  ci=[_boot(vals,10000,0),_cluster_boot(vals,[r['tile'] for r in rows],10000,0),_cluster_boot(vals,[r['control'] for r in rows],10000,0)];out.append([label,f'{np.mean(vals):.6f}']+[f'[{b["ci_low"]:.6f}, {b["ci_high"]:.6f}]' for b in ci]);stats.append({'comparison':label,'mean':float(np.mean(vals)),'bootstrap':ci})
 md=table(['比较 / Comparison','ΔMSE','配对 95% CI / Paired','地理组 95% CI / Geographic','供体组 95% CI / Donor-group'],out);(d/'TableF1.md').write_text(md,encoding='utf-8');(d/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
 marker=f'<!-- BD_F1_VERIFIED_{v}_20261115 -->';block='\n\n'+marker+'\n\n#### 附录F1：固定84例热旱天气替换（seed42）\n\n'+md+'\n84对/45独立供体/31地理组；冻结清单及原始数据SHA核对通过；10000次bootstrap，seed0，原统计函数直接复用且在历史结果上精确复现。\n\n**干预范围限制：**沿原代码固定接收样本基础预测与初态，只替换状态分支24维未来天气；新版B/D基础预测本身读取实际未来天气。季节编码保持接收样本自身值。因此本表是新增状态分支的天气干预诊断，不能解释为整模型去除天气，也不能与旧exclusive模型不加说明地合并结论。\n\n权重SHA：`'+x['result.json']['checkpoint_sha256']+'`；逐配对、配置、真实退出与统计证据：`'+str(d)+'`。\n';append(v,block,marker)
 a=x['architecture.json'];cfg=a['config'];assert cfg['use_adaln']==(v=='D');sh=a['tensor_shapes'];assert sh['o_delta.weight']==[16,256]
 specs=[['历史影像；有效性掩膜','10×5×128×128；10×1×128×128'],['历史天气；未来天气','10×24；20×24；另有逐日期2维年周期sin/cos'],['地理输入；预测输出','3×128×128；20×1×128×128'],['历史骨干','Contextformer 6M/PVT；时序Transformer深度3、宽256、8头、MLP扩展比4；基础预测读取未来天气，初态使用context-only路由'],['状态网格','32×32×256；4×4图像块'],['状态投影','LayerNorm → Linear 256→512 → GELU → Linear 512→256 → LayerNorm'],['天气编码','单层GRU：24→128'],['地理编码','4×4平均池化；MLP 3→64→64'],['跨度编码','64维固定正弦/余弦，五天步数'],['条件融合','128+64+64拼接；MLP 256→256→256；季节Linear 2→256加到条件'],['状态残差更新','LayerNorm状态+条件；MLP 512→512→512→256；'+('AdaLN条件投影256→512' if v=='D' else '无AdaLN')],['预测修正读出','Linear 256→16；修正系数1']]
 a1=table(['项目','配置'],specs);(d/'TableA1.md').write_text(a1,encoding='utf-8');marker=f'<!-- BD_A1_VERIFIED_{v}_20261115 -->';append(v,'\n\n'+marker+'\n\n#### 附录A1：实际输入与网络规格\n\n'+a1+'\n实际总参数量：'+str(a['parameters'])+'。与旧稿不同的未来天气基础预测、季节路由及AdaLN已明列。实际加载严格匹配checkpoint，模块表示及张量尺寸见`'+str(d/'receipt.json')+'`中的architecture.json。\n',marker)
 (d/'publication.json').write_text(json.dumps({'status':'PASS','variant':v,'tables':['A1','F1'],'scheme_and_A08_synced':True}),encoding='utf-8');print(v,'A1/F1 published')
