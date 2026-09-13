#!/usr/bin/env python3
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG=Path(__file__).resolve().parents[1]
BLUE,ORANGE="#0072B2","#D55E00"

with (FIG/"data"/"Table7_efficiency_state_reuse.csv").open(encoding="utf-8",newline="") as f:
    rows=list(csv.DictReader(f))
vals={r["item"]:float(r["value"]) for r in rows if r["unit"] in ("ms","x")}

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.2,"axes.titlesize":9.0,
 "axes.labelsize":8.4,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,
 "grid.alpha":.28,"grid.color":"#BFC7D1","legend.frameon":True,"legend.facecolor":"white","legend.edgecolor":"#BFC5CC"})
fig,axes=plt.subplots(1,2,figsize=(7.15,3.35),gridspec_kw={"width_ratios":[1.05,1.2]})

ax=axes[0]
keys=["history_encoding_ms","shared_prefix_ms","suffix_per_branch_ms","save_ms","restore_gpu_ms","restore_cpu_ms"]
labels=["history\nencode","shared\nprefix","suffix /\nbranch","save\nstate","restore\nGPU","restore\nCPU"]
numbers=np.array([vals[k] for k in keys]);colors=[BLUE,BLUE,"#009E73","#A0A0A0","#7F7F7F","#B8B8B8"]
bars=ax.bar(np.arange(len(keys)),numbers,color=colors,width=.80)
for bar,value in zip(bars,numbers):
    ax.text(bar.get_x()+bar.get_width()/2,max(value+.55,1.05),f"{value:.2f}",ha="center",va="bottom",fontsize=6.5,rotation=90 if value<1 else 0)
ax.set_xticks(np.arange(len(keys)),labels);ax.set_ylim(0,39);ax.set_ylabel("measured median latency (ms)");ax.set_title("A. Measured phase costs",loc="left",fontweight="bold");ax.grid(axis="x",visible=False)
ax.tick_params(axis="x",labelsize=7.0)

ax=axes[1]
B=np.array([1,2,4,8]);history=vals["history_encoding_ms"];prefix=vals["shared_prefix_ms"];suffix=vals["suffix_per_branch_ms"]
reuse=history+prefix+B*suffix;reencode=B*(history+prefix+suffix)
ax.plot(B,reuse,color=BLUE,marker="o",lw=1.5,label="reuse history + prefix")
ax.plot(B,reencode,color=ORANGE,marker="s",ls="--",lw=1.5,label="re-encode per branch")
for xx,yy,ratio in zip(B,reencode,reencode/reuse):ax.text(xx,yy+7,f"{ratio:.1f}×",ha="center",fontsize=6.6,color=ORANGE)
ax.set_xticks(B);ax.set_xlim(.65,8.35);ax.set_ylim(20,270);ax.set_xlabel("number of branches B (discrete)");ax.set_ylabel("analytic compute model (ms)");ax.set_title("B. Reuse cost model",loc="left",fontweight="bold")
ax.legend(loc="upper left",fontsize=7.0,framealpha=.95,borderpad=.35)
fig.subplots_adjust(left=.105,right=.985,top=.95,bottom=.18,wspace=.30)
out=FIG/"selected"/"图9_状态复用成本_最终";out.parent.mkdir(parents=True,exist_ok=True)
fig.savefig(out.with_suffix(".png"),dpi=300,bbox_inches="tight",pad_inches=.05,facecolor="white")
fig.savefig(out.with_suffix(".pdf"),bbox_inches="tight",pad_inches=.05,facecolor="white")
plt.close(fig)
