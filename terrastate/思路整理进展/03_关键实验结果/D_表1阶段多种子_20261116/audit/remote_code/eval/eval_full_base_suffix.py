#!/usr/bin/env python3
"""R02-A1 streaming common-suffix evaluator; shared model semantics are untouched."""
import argparse, csv, hashlib, json, time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import xarray
import torch
from torch.utils.data import DataLoader, Subset

PREFIXES = {"A": (10,), "B": (5, 5), "C": (3, 7)}
PATHS = ("D20", "A", "B", "C")
ABS_H = tuple(range(11, 21))
QUALITY_TOL = 1e-5

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def query_plan(prefix):
    if sum(prefix)!=10: raise ValueError(prefix)
    return [(k, 10+k, tuple(prefix), (k,)) for k in range(1,11)]

def masked_stats(pred, target, valid):
    m=valid.bool(); n=int(m.sum().item())
    if n==0: return 0, float("nan"), "no_valid_pixels"
    if not torch.isfinite(target[m]).all().item(): raise RuntimeError("nonfinite_valid_target")
    if not torch.isfinite(pred[m]).all().item(): raise RuntimeError("nonfinite_valid_prediction")
    d=(pred-target)[m]
    return n, float((d*d).sum().item()), ""

def geo_group(name):
    # The frozen manifest has no formal spatial-group mapping; retain the
    # source receiver prefix only as an explicit, non-authoritative field.
    s=Path(str(name)).name.split("_")
    return s[2] if len(s)>=3 and s[0]=="minicube" else "UNCONFIRMED"

def write_csv(p, rows, fields):
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def load_ids(manifest,selector="validation_subsplit.ids",split_prefix="iid_chopped") :
    d=json.loads(Path(manifest).read_text(encoding="utf-8"))
    ids=d
    for key in selector.split("."): ids=ids[key]
    if not isinstance(ids,list) or not all(isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):raise ValueError("manifest IDs invalid or duplicated")
    return [x[len(split_prefix)+1:] if x.startswith(split_prefix+"/") else x for x in ids], d

@torch.no_grad()
def model_rows(model, items, device, model_name, ckmeta):
    from train.terrastate_v2_common import collate_with_ids, to_device_with_ids
    data=to_device_with_ids(collate_with_ids(items),device)
    pred, prior, _res, z0, geo, u=model.forecast(data,want_parts=True)
    B,H,W=pred.shape[0],pred.shape[-2],pred.shape[-1]; cl=int(model.context_len)
    states={p:model.segment_state(z0,u,geo,part) for p,part in PREFIXES.items()}
    rows=[]; gaps=[]; per_key={}
    lc_mask=((data["landcover"]>=model.lc_min)&(data["landcover"]<=model.lc_max))
    for k,h,prefix,step in query_plan((10,)):
        outs={"D20":pred[:,h-1,0]}
        for key in ("A","B","C"):
            z=model.segment_state(states[key],u[:,10:10+k],geo,(k,))
            y=prior[:,h-1]+model.alpha*model._decode_state(z,B,H,W)
            outs[key]=y[:,0]
        for bi,item in enumerate(items):
            cube=str(item.get("cubename",item.get("filepath",""))); gid=geo_group(cube)
            targ=data["dynamic"][0][bi,cl+h-1,0]
            valid=(data["dynamic_mask"][0][bi,cl+h-1,0]<1.0)&lc_mask[bi,0]
            stats={name:masked_stats(outs[name][bi],targ,valid) for name in PATHS}
            for name in PATHS:
                n,sse,reason=stats[name]
                if len({v[0] for v in stats.values()}) != 1: raise RuntimeError("model_path_mask_count_mismatch")
                row={"dataset_index":int(item["_dataset_index"]),"cube":cube,"geo_group":gid,"model":model_name,"path":name,"prefix":("D_direct_11_20" if name=="D20" else name),"b":10,"k":k,"absolute_h":h,"n_valid":n,"sse":sse,"mse":(sse/n if n else float("nan")),"nonfinite":False,"exclude_reason":reason,"checkpoint_sha256":ckmeta["checkpoint_sha256"]}
                rows.append(row); per_key[(int(item["_dataset_index"]),name,k)]=(n,sse)
            for a,b,label in (("A","B","A_B"),("A","C","A_C"),("A","D20","A_D20")):
                d=(outs[a][bi]-outs[b][bi])[valid]
                gaps.append({"dataset_index":int(item["_dataset_index"]),"cube":cube,"model":model_name,"k":k,"absolute_h":h,"n_valid":int(d.numel()),"output_mae":(float(d.abs().mean().item()) if d.numel() else float("nan")),"comparison":label})
    return rows,gaps,per_key

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--data-root",required=True); ap.add_argument("--iid-manifest",required=True); ap.add_argument("--c0r",required=True); ap.add_argument("--c1",required=True); ap.add_argument("--out",required=True); ap.add_argument("--device",default="cuda:0"); ap.add_argument("--batch-size",type=int,default=8); ap.add_argument("--max-cubes",type=int,default=2856)
    ap.add_argument('--ids-selector',default='validation_subsplit.ids');ap.add_argument('--split-prefix',default='iid_chopped');ap.add_argument('--probe',action='store_true');ap.add_argument('--c1-sha');ap.add_argument('--c0r-sha');a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
    ids,man=load_ids(a.iid_manifest,a.ids_selector,a.split_prefix)
    from data.greenearthnet_contextformer_dataset import GreenEarthNetContextformerDataset
    from eval.full_base_loader import load_candidate_c_strict
    ds=GreenEarthNetContextformerDataset(a.data_root,dl_cloudmask=True); index={str(Path(fp).relative_to(a.data_root)).replace("\\","/"):i for i,fp in enumerate(ds.filepaths)}
    # Load both models before selection so the qualification uses the actual
    # compatible configured land-cover range, not a duplicated literal.
    device=torch.device(a.device); models=[]; metas=[]
    for name,ck in (("C0R",a.c0r),("C1",a.c1)):
        model,_,meta=load_candidate_c_strict(ck,device=device,probe=a.probe,expected_sha=a.c1_sha if name=='C1' else a.c0r_sha)
        if meta['arm']!=name:raise RuntimeError('input label disagrees with checkpoint arm')
        meta={"checkpoint_sha256":sha256_file(ck),"arm":meta["arm"],"factual_path":meta["factual_path"],"strict":True,"step":meta["step"],"lc_min":int(model.lc_min),"lc_max":int(model.lc_max),"training":meta}
        models.append((name,model)); metas.append({"model":name,**meta})
    if len({(m["training"]["variant"],m["training"]["seed"]) for m in metas})!=1:raise ValueError("paired variant/seed mismatch")
    if len({(m[1].lc_min,m[1].lc_max) for m in models}) != 1: raise RuntimeError("incompatible_landcover_ranges")
    lc_min,lc_max=int(models[0][1].lc_min),int(models[0][1].lc_max)
    chosen=[]; excluded=[]; old32=[]; old32_qual=[]
    for cid in sorted(set(ids)):
        j=index.get(cid)
        if j is None: excluded.append({"id":cid,"reason":"not_found_in_data_root"}); continue
        item=ds[j]; item["_dataset_index"]=j
        cl=int(models[0][1].context_len); y=item["dynamic"][0][cl+10:cl+20,0]; m=item["dynamic_mask"][0][cl+10:cl+20,0]<1.0; lc=item["landcover"]; valid=m&((lc>=lc_min)&(lc<=lc_max))[0]
        old_y=item["dynamic"][0][10:,0]; old_m=item["dynamic_mask"][0][10:]<1.0; old_valid=old_m[:,0]&((lc>=lc_min)&(lc<=lc_max))[0]
        old32.append(cid); old32_qual.append(int(old_valid.sum())>0)
        if int(valid.sum())==0: excluded.append({"id":cid,"reason":"no_valid_target_pixels_suffix_11_20","old_full_suffix_qualifies":int(old_valid.sum())>0}); continue
        chosen.append((cid,j,item))
        if len(chosen)>=a.max_cubes: break
    if len(chosen)<a.max_cubes: print(f"selection_shortfall {len(chosen)}/{a.max_cubes}")
    write_csv(out/"SAMPLE_MANIFEST.csv",[{"rank":r+1,"dataset_index":j,"receiver_id":cid,"cube":str(it.get("cubename",it.get("filepath",""))),"selection":"stable_id_sorted_first32_with_full_suffix_valid"} for r,(cid,j,it) in enumerate(chosen)]+[{"rank":"","dataset_index":"","receiver_id":x["id"],"cube":"","selection":"EXCLUDED:"+x["reason"]} for x in excluded],["rank","dataset_index","receiver_id","cube","selection"])
    start=time.time(); allrows=[]; allgaps=[]; per_model={}
    for name,model in models:
        items=[it for _,_,it in chosen]
        for q in range(0,len(items),a.batch_size):
            ckmeta=next(x for x in metas if x["model"]==name)
            rr,gg,pk=model_rows(model,items[q:q+a.batch_size],device,name,ckmeta)
            allrows+=rr; allgaps+=gg; per_model.update({(name,)+k:v for k,v in pk.items()})
        del model; torch.cuda.empty_cache()
    expected={(int(j),name,path,k) for name,_ in models for _,j,_ in chosen for path in PATHS for k in range(1,11)}
    observed=[(int(r["dataset_index"]),r["model"],r["path"],int(r["k"])) for r in allrows]
    observed_set=set(observed)
    if len(observed)!=len(observed_set): raise RuntimeError("duplicate_key")
    if expected != observed_set: raise RuntimeError(f"missing_or_extra_rows missing={len(expected-observed_set)} extra={len(observed_set-expected)}")
    if any(bool(r.get("nonfinite")) for r in allrows): raise RuntimeError("nonfinite_prediction_flag")
    fields=list(allrows[0]) if allrows else []
    write_csv(out/"PER_RECEIVER_HORIZON.csv",allrows,fields); write_csv(out/"OUTPUT_GAPS.csv",allgaps,list(allgaps[0]) if allgaps else [])
    # compact receiver/path summaries, preserving descriptive per-receiver primary unit
    sums=[]
    for model in ("C0R","C1"):
        for path in PATHS:
            sub=[r for r in allrows if r["model"]==model and r["path"]==path and r["n_valid"]>0]
            by={}
            for r in sub:
                by.setdefault(int(r["dataset_index"]),[0.0,0,0])
                by[int(r["dataset_index"])][0]+=float(r["sse"])
                by[int(r["dataset_index"])][1]+=int(r["n_valid"])
                by[int(r["dataset_index"])][2]+=1
            qualified=[v for v in by.values() if v[1] and v[2]==10]
            vals=[v[0]/v[1] for v in qualified]
            sums.append({"model":model,"path":path,"n_receivers":len(vals),"mean_receiver_full_mse":(sum(vals)/len(vals) if vals else float("nan")),"pooled_mse":(sum(v[0] for v in qualified)/sum(v[1] for v in qualified) if vals else float("nan"))})
    write_csv(out/"SUMMARY.csv",sums,list(sums[0]) if sums else [])
    (out/"RUN_METADATA.json").write_text(json.dumps({"status":"COMPLETE","probe":a.probe,"n_selected":len(chosen),"dataset_total":len(ds),"manifest":str(a.iid_manifest),"manifest_id_list_sha256":hashlib.sha256("\n".join(ids).encode()).hexdigest(),"manifest_file_sha256":sha256_file(a.iid_manifest),"ids_selector":a.ids_selector,"split_prefix":a.split_prefix,"prefixes":{k:list(v) for k,v in PREFIXES.items()},"models":metas,"elapsed_seconds":time.time()-start,"device":str(device),"future_labels_used_for_scoring_only":True,"quality_gate":{"duplicate_keys":0,"missing_or_extra_rows":0,"nonfinite_valid_predictions":0,"mask_count_mismatch":0}},ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
