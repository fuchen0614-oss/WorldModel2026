#!/usr/bin/env python3
from pathlib import Path
import csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG = Path(__file__).resolve().parents[1]
BLUE, ORANGE, BLACK = "#0072B2", "#D55E00", "#24272B"

def rows(path):
    with path.open(encoding="utf-8", newline="") as f: return list(csv.DictReader(f))

def save(fig, name):
    out=FIG/"selected"/name; out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out.with_suffix(".png"),dpi=300,bbox_inches="tight",pad_inches=.05,facecolor="white")
    fig.savefig(out.with_suffix(".pdf"),bbox_inches="tight",pad_inches=.05,facecolor="white")
    plt.close(fig)

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.2,"axes.titlesize":9.0,
                     "axes.labelsize":8.4,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.grid":True,"grid.alpha":.30,"grid.color":"#BFC7D1",
                     "legend.frameon":True,"legend.facecolor":"white","legend.edgecolor":"#BFC5CC"})
scheme=rows(FIG/"data"/"Table6A_leaveout_partitions.csv")
boot=json.loads((FIG/"data"/"T3_c0r_vs_c1_paired_bootstrap.json").read_text(encoding="utf-8"))["primary_grouping"]
fig,axes=plt.subplots(1,2,figsize=(7.15,4.0),gridspec_kw={"width_ratios":[1.0,1.55]})

ax=axes[0]
splits=["iid_chopped","ood-t_chopped","ood-s_chopped","ood-st_chopped"]
names=["IID","OOD-T","OOD-S","OOD-ST"]
for y,(s,n) in enumerate(zip(splits,names)):
    v=boot[s]; point=v["delta_c0r_minus_c1"]; lo,hi=v["ci95"]
    ax.errorbar(point,y,xerr=[[point-lo],[hi-point]],fmt="o",color=BLUE,ecolor=BLUE,
                ms=4.6,capsize=3,lw=1.25,zorder=3)
ax.axvline(0,color=BLACK,lw=1)
ax.set_yticks(range(4),names); ax.invert_yaxis()
ax.set_xlabel("paired ΔRMSE (C0R − C1)")
ax.set_title("A. Endpoint-supervision ablation",loc="left",fontweight="bold")
ax.grid(axis="y",visible=False)

ax=axes[1]
combos=[]
for r in scheme:
    if r["combo"] not in combos: combos.append(r["combo"])
ypos={c:i for i,c in enumerate(combos)}
for key,label,marker,color,off in [("dev476","Development","o","#8B9198",-.10),
                                   ("IID2856","IID confirmation","s",BLUE,.10)]:
    rr=[r for r in scheme if r["set"]==key]
    ax.scatter([float(r["ratio"]) for r in rr],[ypos[r["combo"]]+off for r in rr],
               s=25,marker=marker,color=color,label=label,zorder=3)
ax.axvline(1.0,color=BLACK,lw=1)
ax.axvline(1.05,color=ORANGE,lw=1.15,ls="--")
ax.text(1.0495,-.12,"1.05",color=ORANGE,fontsize=7,ha="right",va="center")
ax.set_yticks(range(len(combos)),[c.replace("|"," · ") for c in combos],fontsize=6.8)
ax.set_ylim(len(combos)-.5,-1.65)
ax.set_xlim(.9895,1.0525)
ax.set_xlabel("composed / direct MSE ratio")
ax.set_title("B. C1 segmentation stability",loc="left",fontweight="bold")
ax.legend(loc="upper left",bbox_to_anchor=(.02,.985),ncol=2,fontsize=6.8,
          framealpha=.95,borderpad=.35,columnspacing=1.1,handletextpad=.45)
fig.subplots_adjust(left=.12,right=.985,top=.95,bottom=.14,wspace=.34)
save(fig,"图6_端点监督与分段稳定性_最终")
