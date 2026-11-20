"""Full-base strict evaluation loader; incomplete runs only with explicit probe."""
from pathlib import Path
import hashlib,json,sys,math
import xarray,numpy as np,torch
from models.spanworld_full_base import SpanWorldFullBase
from models.encoders.pvt_contextformer_q import contextformer6m_hparams
sys.modules.setdefault('numpy._core',np.core);sys.modules.setdefault('numpy._core.multiarray',np.core.multiarray)
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
def load_candidate_c_strict(ckpt_path,device='cpu',probe=False,expected_sha=None):
 p=Path(ckpt_path);raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if expected_sha and sha!=expected_sha:raise ValueError('checkpoint SHA mismatch')
 ck=torch.load(__import__('io').BytesIO(raw),map_location='cpu',weights_only=False);cfg=ck.get('contract_cfg',{})
 if cfg.get('arch')!='SpanWorldFullBase' or ck.get('arch')!=cfg['arch']:raise ValueError('unsupported architecture: do not relabel missing consistency/baseline implementations')
 if cfg.get('route_version')!=SpanWorldFullBase.ROUTE_VERSION:raise ValueError('route mismatch')
 if ck.get('arm') not in ('C1','C0R'):raise ValueError('unregistered supervision arm')
 if cfg.get('factual_path')!={'C1':'recursive','C0R':'direct'}[ck['arm']]:raise ValueError('arm/path mismatch')
 if not probe:
  if not expected_sha:raise ValueError('formal evaluation requires expected SHA')
  summary=json.loads((p.parent/'summary.json').read_text());last=torch.load(p.parent/'last.pt',map_location='cpu',weights_only=False);validate_full_base_selection(ck,summary,best_path=p,last=last)
 m=SpanWorldFullBase(contextformer6m_hparams(pvt_pretrained=False),cfg);m.load_state_dict(ck['b4_state_dict'],strict=True);m.history_state_only=True;m.to(device).eval()
 return m,ck,{'checkpoint_sha256':sha,'step':ck['step'],'arm':ck['arm'],'factual_path':cfg['factual_path'],'variant':cfg['variant'],'seed':ck.get('args',{}).get('seed'),'probe':probe,'strict':True}
