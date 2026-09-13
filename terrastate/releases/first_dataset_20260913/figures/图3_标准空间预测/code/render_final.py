#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG=Path(__file__).resolve().parents[1]

def save(fig,name,dpi=300):
    p=FIG/"selected"/name;p.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(p.with_suffix(".png"),dpi=dpi,bbox_inches="tight",pad_inches=.04,facecolor="white")
    fig.savefig(p.with_suffix(".pdf"),bbox_inches="tight",pad_inches=.04,facecolor="white")
    plt.close(fig)

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":7.8,"axes.titlesize":7.8,
                     "axes.labelsize":8.0,"axes.grid":False})

# ---------------------------------------------------------------------------------------------
# Input resolution. The curated release package stores these arrays ONCE under
# `reproduction/` instead of duplicating them inside every figure directory. Prefer the original
# figure-local export when it is present (full source package), otherwise fall back to the
# release root (slim package). Nothing else about the drawing depends on which one is used.
ROOT=FIG.parents[1]                      # .../first_dataset_20260913

def _pick(*cands):
    for c in cands:
        if c.exists():
            return c
    raise SystemExit("input not found; tried:\n  " + "\n  ".join(str(c) for c in cands))

_ARRAYS=_pick(FIG/"data"/"_arrays"/"P42"/"arrays.npz",
              ROOT/"reproduction"/"P42_arrays"/"arrays.npz")
_META=_pick(FIG/"data"/"_arrays"/"P42"/"metadata.json",
            ROOT/"reproduction"/"P42_arrays"/"metadata.json")
_BASELINE=_pick(FIG/"data"/"baseline_predictions"/"P42.npz",
                ROOT/"reproduction"/"P42_official_baselines.npz")
z=np.load(_ARRAYS)
b=np.load(_BASELINE)
meta=json.loads(_META.read_text(encoding="utf-8"))
gt,c1,pers,valid=z["gt"],z["c1"],z["persistence"],z["valid"]
hs=[]
for start in range(0,20,5):
    coverage=valid[start:start+5].mean(axis=(1,2));hs.append(start+int(np.argmax(coverage)))
sources=[("Ground truth",gt),("Persistence",pers),("ConvLSTM 1M",b["convlstm"]),("SimVP 6M",b["simvp"]),("PredRNN 1M",b["predrnn"]),("Contextformer 6M",b["contextformer"]),("TerraState-C1",c1)]

fig,axes=plt.subplots(len(sources),4,figsize=(7.15,9.25));cm=plt.get_cmap("viridis").copy();cm.set_bad("#777777")
for i,(name,arr) in enumerate(sources):
    for j,h in enumerate(hs):
        ax=axes[i,j];im=ax.imshow(np.where(valid[h]>0,arr[h],np.nan),cmap=cm,vmin=0,vmax=1,interpolation="nearest");ax.set_xticks([]);ax.set_yticks([])
        if j==0:ax.set_ylabel(name,rotation=0,ha="right",va="center",labelpad=8,fontsize=7.6)
        if i==0:ax.set_title(f"window {j+1}\n{meta['target_dates'][h]}",fontsize=7.7)
cax=fig.add_axes([.925,.075,.015,.855]);cb=fig.colorbar(im,cax=cax,ticks=[0,.25,.5,.75,1]);cb.set_label("NDVI\nlow → high",labelpad=5)
fig.text(.18,.965,"A",fontsize=10,fontweight="bold");fig.subplots_adjust(left=.18,right=.90,top=.95,bottom=.035,hspace=.07,wspace=.035)
save(fig,"图3A_P42标准空间预测_最终")

methods=[x for x in sources if x[0]!="Ground truth"]
fig,axes=plt.subplots(len(methods),4,figsize=(7.15,7.95));cm=plt.get_cmap("magma").copy();cm.set_bad("#777777")
for i,(name,arr) in enumerate(methods):
    for j,h in enumerate(hs):
        ax=axes[i,j];err=np.abs(arr[h]-gt[h]);im=ax.imshow(np.where(valid[h]>0,err,np.nan),cmap=cm,vmin=0,vmax=.4,interpolation="nearest");ax.set_xticks([]);ax.set_yticks([])
        if j==0:ax.set_ylabel(name,rotation=0,ha="right",va="center",labelpad=8,fontsize=7.6)
        if i==0:ax.set_title(meta["target_dates"][h],fontsize=7.7)
cax=fig.add_axes([.925,.085,.015,.835]);cb=fig.colorbar(im,cax=cax,ticks=[0,.1,.2,.3,.4],extend="max");cb.set_label("absolute NDVI error\nlow → high",labelpad=5)
fig.text(.18,.958,"B",fontsize=10,fontweight="bold");fig.subplots_adjust(left=.18,right=.90,top=.94,bottom=.035,hspace=.07,wspace=.035)
save(fig,"图3B_P42绝对误差_最终")
