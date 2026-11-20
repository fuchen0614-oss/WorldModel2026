from pathlib import Path
import numpy as np,io,json,hashlib,base64,zipfile
base=Path('/oss-chengjuntao/makerdata/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/figure_candidates')
roots=[base/'D_figure3_P42_20261116_candidates_v1/raw/cases',base/'D_figure3_P42_20261116_npz_v3/raw/cases']
G1={'new_Q98':'river/linear geometry','new_Q95':'heterogeneous field mosaic','new_Q50':'dense mixed fields','Q90':'low-contrast broad fields'}
records=[];all_frames=[];buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
 for p in [c for root in roots for c in sorted(root.iterdir())]:
  m=json.loads((p/'metadata.json').read_text());raw=(p/'arrays.npz').read_bytes();h=hashlib.sha256(raw).hexdigest();assert h==m['arrays_sha256']
  with np.load(io.BytesIO(raw)) as a:arr={k:a[k].copy() for k in a.files}
  coverage=arr['valid'].mean(axis=(1,2));g1steps=[]
  if p.name in G1:
   for lo,hi in [(0,10),(10,20)]:
    i=max(range(lo,hi),key=lambda k:(float(coverage[k]),-k))
    if coverage[i]>=.4:g1steps.append(i)
  eligible=[]
  for i in range(10,20):
   mask=arr['valid'][i].astype(bool);n=int(mask.sum())
   if not n:continue
   gt=arr['gt'][i].astype(float);v={k:float(np.mean((arr[k][i if k.endswith('direct') else i-10].astype(float)[mask]-gt[mask])**2)) for k in ['C1_direct','C1_continued','C0R_direct','C0R_continued']}
   row=dict(case=p.name,index=i,day=(i+1)*5,date=m['dates'][i],coverage=float(coverage[i]),valid_pixels=n,**v,degradation=v['C1_continued']-v['C1_direct'],relative_degradation=(v['C1_continued']-v['C1_direct'])/max(v['C1_direct'],1e-12),paired_delta=v['C1_continued']-v['C0R_continued']);all_frames.append(row)
   if coverage[i]>=.4 and row['degradation']>0:eligible.append(row)
  picked=[]
  if eligible:
   # retain coverage-first and median-severity examples, not only worst failures
   first=max(eligible,key=lambda r:(r['coverage'],-r['day']));ordered=sorted(eligible,key=lambda r:(r['relative_degradation'],r['day']));middle=ordered[len(ordered)//2];picked=sorted({first['index'],middle['index']})
  rec=dict(case=p.name,metadata=m,source_full_sha256=h,G1_indices=g1steps,G1_structure_reason=G1.get(p.name),G1_date_rule='highest valid coverage in each half of forecast; earliest tie; fixed before PredRNN inference',G2_indices=picked,G2_date_rule='among C1 self-degradation and coverage>=.40: max-coverage earliest tie and median relative-degradation; deduplicated',G2_eligible_frames=len(eligible));records.append(rec)
  for group,steps in [('G1',g1steps),('G2',picked)]:
   for i in steps:
    frame=dict(gt=arr['gt'][i],valid=arr['valid'][i],C1_direct=arr['C1_direct'][i])
    if group=='G2':frame.update(C1_continued=arr['C1_continued'][i-10],C0R_direct=arr['C0R_direct'][i],C0R_continued=arr['C0R_continued'][i-10])
    b=io.BytesIO();np.savez_compressed(b,**frame);blob=b.getvalue();name=p.name+'/'+group+'_day'+str((i+1)*5)+'.npz';z.writestr(name,blob);rec.setdefault('subsets',{})[name]=hashlib.sha256(blob).hexdigest()
 z.writestr('manifest.json',json.dumps(records));z.writestr('all_G2_frames.json',json.dumps(all_frames))
print('PACKAGE:'+base64.b64encode(buf.getvalue()).decode(),flush=True)
