import argparse,json,time,hashlib,math,os,sys
os.environ.setdefault("OMP_NUM_THREADS","1")
os.environ.setdefault("MKL_NUM_THREADS","1")
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd,torch,xarray as xr
from train import terrastate_v2_common as t
from train.full_base_policy import wait_for_holder_handoff
from models.terrastate_candidate_c import TerraStateCandidateC
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset as Dataset
from eval.ndvi_prediction_v2 import make_ndvi_prediction_dataset
from eval.greenearthnet_protocol import compute_pixel_metrics,summarize_scores,OFFICIAL_EVALUATOR_COMMIT
def validate_full_base_selection(ck, summary, best_path=None, last=None):
 if ck.get("contract_cfg", {}).get("arch") != "SpanWorldFullBase": return
 if summary.get("training_stage") != "stage2" or summary.get("completion_reason") != "schedule_complete" or summary.get("step") != 74500:
  raise ValueError("full-base standard evaluation requires completed stage2")
 cfg=ck["contract_cfg"]
 for key in ("training_stage", "variant", "factual_path"):
  if key not in summary or ck.get(key) != summary[key] or cfg.get(key) != summary[key]:
   raise ValueError("checkpoint/summary/config mismatch: " + key)
 for key in ("arm", "total_steps"):
  if key not in summary or ck.get(key) != summary[key]:
   raise ValueError("checkpoint/summary mismatch: " + key)
 if ck.get("sha") != summary.get("sha"):
  from train.efficiency_continuation import inherited_best_matches
  if last is None or best_path is None or last.get("sha") != summary.get("sha") or last.get("step") != 74500 or not inherited_best_matches(last,ck,best_path):
   raise ValueError("unverified inherited best selection")
 best=summary.get("best_val_dev_RMSE_LC")
 if not isinstance(best,dict) or set(best) != {"score","epoch","step"} or not math.isfinite(best["score"]):
  raise ValueError("invalid selected best record")
 if ck.get("rmse_best") != best or ck.get("epoch") != best["epoch"] or ck.get("step") != best["step"]:
  raise ValueError("best checkpoint metadata disagrees with completed run")
 if ck.get("args",{}).get("seed") != summary.get("seed"):
  raise ValueError("checkpoint seed mismatch")

ap=argparse.ArgumentParser();ap.add_argument("--run",required=True);ap.add_argument("--out",required=True);ap.add_argument("--device",default="cpu");ap.add_argument("--probe",action="store_true");ap.add_argument("--data-root",required=True);ap.add_argument("--expected-checkpoint-sha256",default="");ap.add_argument("--handoff-dir",default="");ap.add_argument("--handoff-token",default="");ap.add_argument("--handoff-timeout",type=float,default=120)
ap.add_argument("--split",required=True);ap.add_argument("--frozen-checkpoint",required=True);ap.add_argument("--frozen-receipt",required=True);ap.add_argument("--controller",required=True)
a=ap.parse_args();run=Path(a.run);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
if a.probe:raise ValueError("fixed interim evaluation does not use probe bypass")
controller=Path(a.controller);binding=json.loads(Path(a.frozen_receipt).read_text())
torch.set_num_threads(1);torch.set_num_interop_threads(1)
raw=Path(a.frozen_checkpoint).read_bytes();sha=hashlib.sha256(raw).hexdigest()
if sha!=binding["sha256"] or sha!=a.expected_checkpoint_sha256:raise ValueError("frozen checkpoint binding mismatch")
if a.expected_checkpoint_sha256 and sha != a.expected_checkpoint_sha256: raise ValueError("selected checkpoint SHA mismatch")
snap=out/"best_frozen.pt";snap.write_bytes(raw)
if not hasattr(np,"_core"):
 sys.modules.setdefault("numpy._core",np.core)
 sys.modules.setdefault("numpy._core.multiarray",np.core.multiarray)
ck=torch.load(snap,map_location="cpu",weights_only=False)
assert ck["arm"] in ("C1","C0R","BASELINE")
assert ck.get("contract_cfg"), "checkpoint missing contract_cfg"
cfg=ck["contract_cfg"]
assert binding['status']=='PASS' and binding['selection_kind']=='fixed_epoch_040'
assert (ck['epoch'],ck['step'],ck['variant'],ck['arm'],ck['args']['seed'])==(binding['epoch'],binding['step'],binding['variant'],binding['arm'],binding['seed'])
assert ck['epoch']==40 and ck['step']==29800 and ck['total_steps']==74500
assert ck['sha']['parent_file_sha256']==binding['parent_sha']
classes={TerraStateCandidateC.ARCH:TerraStateCandidateC, SpanWorldFullBase.ARCH:SpanWorldFullBase}
if cfg.get('arch')=='SpanWorldBaselineOnly':
 from models.spanworld_baseline_only import SpanWorldBaselineOnly
 classes[SpanWorldBaselineOnly.ARCH]=SpanWorldBaselineOnly
if cfg.get("arch") not in classes: raise ValueError("unknown checkpoint architecture")
if ck.get("arch") != cfg["arch"]: raise ValueError("checkpoint architecture metadata mismatch")
model_class=classes[cfg["arch"]]
if cfg.get("route_version") != model_class.ROUTE_VERSION: raise ValueError("checkpoint route mismatch")
model=model_class(contextformer6m_hparams(pvt_pretrained=False),contract_cfg=ck["contract_cfg"])
model.load_state_dict(ck["b4_state_dict"],strict=True);model.to(a.device).eval()
root=Path(a.data_root)
all_splits={"iid_chopped":2856,"ood-t_chopped":1904,"ood-s_chopped":10536,"ood-st_chopped":7024}
assert a.split in all_splits;splits={a.split:all_splits[a.split]}
cols=["nnse","rmse","R2","biasabs","rmse_0_5","rmse_5_10","rmse_10_15","rmse_15_20"]
def aggregate(compact):
 lc=compact.groupby("landcover")[cols].mean()
 r={"nse":float(2-1/lc.nnse.mean()),"rmse":float(lc.rmse.mean()),"R2":float(lc.R2.mean()),"biasabs":float(lc.biasabs.mean())}
 for label,code in (("forest",10),("shrub",20),("grass",30),("crop",40)):
  if code in lc.index:
   r.update({f"nse_{label}":float(2-1/lc.loc[code,"nnse"]),f"rmse_{label}":float(lc.loc[code,"rmse"]),f"R2_{label}":float(lc.loc[code,"R2"]),f"biasabs_{label}":float(lc.loc[code,"biasabs"])})
 for k in cols[4:]:r[k]=float(lc[k].mean())
 r["rmse25"]=r["rmse_0_5"]
 assert all(math.isfinite(v) for v in r.values())
 return r
results={};started=time.time();handoff_done=False
for split,count in splits.items():
 ds=Dataset(str(root/split),dl_cloudmask=True);assert len(ds)==count,(split,len(ds),count)
 paths=[str(p) for p in ds.filepaths];assert len(set(paths))==count
 listsha=hashlib.sha256("\n".join(paths).encode()).hexdigest()
 groups=[];raw_probe=[];n=4 if a.probe else len(ds);empty=0;seen=[]
 audit=(out/(split+"_coverage.jsonl")).open("x")
 with (out/(split+"_cube_lc.jsonl")).open("x") as file:
  for i in range(n):
   batch=t.collate_with_ids([ds[i]]);data=t.to_device_with_ids(batch,torch.device(a.device))
   with torch.no_grad():pred=model.forecast(data)[:, :, 0].float().cpu().numpy()[0]
   assert np.isfinite(pred).all()
   fp=Path(batch["filepath"][0])
   with xr.open_dataset(fp) as target:
    prediction=make_ndvi_prediction_dataset(target,pred)
    frame=compute_pixel_metrics(target,prediction).reset_index()
   if not handoff_done:
    wait_for_holder_handoff(a.handoff_dir,a.handoff_token,rank=0,step=1,timeout=a.handoff_timeout)
    handoff_done=True
   frame["id"]=str(fp.relative_to(root/split));frame["season"]=fp.parent.name
   sample_id=str(fp.relative_to(root/split))
   seen.append(sample_id)
   audit.write(json.dumps(dict(id=sample_id,empty=bool(frame.empty),checkpoint_sha256=sha))+"\n")
   if frame.empty:empty+=1
   else:
    reduced=frame.assign(R2=frame.r**2,biasabs=frame.bias.abs()).groupby(["id","landcover"],as_index=False)[cols].mean()
    groups.append(reduced);file.write(reduced.to_json(orient="records")+"\n")
    if i<4:raw_probe.append(frame)
   if i==3:
    small=aggregate(pd.concat(groups,ignore_index=True));reference=summarize_scores(pd.concat(raw_probe,ignore_index=True))
    errors={k:abs(v-small[k]) for k,v in reference.items()};assert all(v<1e-10 for v in errors.values()),errors
    prefix=[str(Path(x).relative_to(root/split)) for x in paths[:4]];assert seen==prefix and len(set(seen))==4
    check=dict(status="PASS",pid=os.getpid(),split=split,ids=seen.copy(),expected_prefix=prefix,expected_count=count,checkpoint_sha256=sha,scorer_commit=OFFICIAL_EVALUATOR_COMMIT,metric_abs_errors=errors,peak_cuda_bytes=torch.cuda.max_memory_allocated(),seconds=time.time()-started)
    tmp=out/"protocol_check.tmp";tmp.write_text(json.dumps(check));tmp.replace(out/"protocol_check.json");raw_probe=[]
    deadline=time.monotonic()+300
    while not (controller/"CONTINUE.json").exists():
     if time.monotonic()>deadline:raise TimeoutError("controller protocol acceptance timeout")
     time.sleep(.5)
    assert json.loads((controller/"CONTINUE.json").read_text())["sha256"]==sha
   if i%100==0 or i==3 or i+1==n:
    file.flush();audit.flush();(out/"progress.json").write_text(json.dumps(dict(split=split,done=i+1,total=n,seconds=time.time()-started)))
  audit.close()
  expected_ids=[str(Path(x).relative_to(root/split)) for x in paths[:n]]
  if seen != expected_ids or len(set(seen)) != n: raise ValueError("sample coverage mismatch")
  if not groups: raise ValueError("split has no scored pixels")
  compact=pd.concat(groups,ignore_index=True);assert not compact.duplicated(["id","landcover"]).any()
  metrics=aggregate(compact)
  if a.probe:
   reference=summarize_scores(pd.concat(raw_probe,ignore_index=True))
   for k,v in reference.items():assert abs(v-metrics[k])<1e-10,(k,v,metrics[k])
  results[split]=dict(count=n,empty=empty,coverage_complete=True,checkpoint_sha256=sha,manifest_sha256=listsha,relative_ids_sha256=hashlib.sha256("\n".join(seen).encode()).hexdigest(),metrics=metrics)
  compact.to_csv(out/(split+"_cube_lc.csv"),index=False)
if set(results)!=set(splits) or any(results[k]["count"] != (4 if a.probe else splits[k]) for k in splits): raise ValueError("incomplete split coverage")
receipt=dict(selection_kind="fixed_epoch_040",status="PASS",total_samples=sum(v["count"] for v in results.values()),probe=a.probe,device=a.device,arm=ck["arm"],model_config=model.config(),checkpoint_sha256=sha,best_epoch=ck["epoch"],best_step=ck["step"],scorer_commit=OFFICIAL_EVALUATOR_COMMIT,seconds=time.time()-started,splits=results)
(out/"result.staging.json").write_text(json.dumps(receipt,allow_nan=False,indent=2))
os.replace(out/"result.staging.json",out/"result.json")
print(json.dumps(receipt),flush=True)
