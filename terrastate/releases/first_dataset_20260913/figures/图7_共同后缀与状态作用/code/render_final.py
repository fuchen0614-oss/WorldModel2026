#!/usr/bin/env python3
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

FIG=Path(__file__).resolve().parents[1]
BLUE,ORANGE,GREEN,PURPLE,SKY,BLACK="#0072B2","#D55E00","#009E73","#CC79A7","#56B4E9","#24272B"
split_order=["iid","ood_t","ood_s","ood_st"]
split_names={"iid":"IID","ood_t":"OOD-T","ood_s":"OOD-S","ood_st":"OOD-ST"}
split_colors={"iid":BLUE,"ood_t":ORANGE,"ood_s":GREEN,"ood_st":PURPLE}

def read(path):
    with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def save(fig,folder,name,dpi=300):
    p=FIG/folder/name;p.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(p.with_suffix(".png"),dpi=dpi,bbox_inches="tight",pad_inches=.05,facecolor="white")
    fig.savefig(p.with_suffix(".pdf"),bbox_inches="tight",pad_inches=.05,facecolor="white")
    plt.close(fig)

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.0,"axes.titlesize":8.8,
 "axes.labelsize":8.2,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,
 "grid.alpha":.28,"grid.color":"#BFC7D1","legend.frameon":True,"legend.facecolor":"white",
 "legend.edgecolor":"#BFC5CC"})
agg=read(FIG/"data"/"四划分_逐后缀时距聚合.csv")
rec=read(FIG/"data"/"四划分_receiver状态与输出.csv")
t4=[r for r in read(FIG/"data"/"Table4B_state_intervention_corrected.csv")
    if r["scope"]=="full_suffix_1_to_10" and r["estimand"]=="receiver_equal"]
est={r["split"]:r for r in t4}

fig=plt.figure(figsize=(7.15,7.15))
outer=fig.add_gridspec(2,3,height_ratios=[1.42,1.0],left=.085,right=.985,top=.965,bottom=.08,hspace=.34,wspace=.38)
top=outer[0,:].subgridspec(2,2,hspace=.26,wspace=.16)
paths=[("D20_rmse","D20",BLACK,"-"),("A_rmse","A",GREEN,"--"),("B_rmse","B",SKY,"-."),("donor_rmse","state donor",PURPLE,":")]
for idx,split in enumerate(split_order):
    ax=fig.add_subplot(top[idx//2,idx%2])
    rr=[r for r in agg if r["split"]==split];x=np.array([int(r["suffix_horizon"]) for r in rr])
    for key,label,color,ls in paths:
        y=np.array([float(r[key]) for r in rr])
        ax.plot(x,y,color=color,ls=ls,lw=1.25,alpha=.98,label=label)
    ax.set_xlim(.8,10.2);ax.set_ylim(.142,.246);ax.set_xticks([1,4,7,10])
    ax.set_title(("A. Common-suffix trajectories — " if idx==0 else "")+split_names[split],loc="left",fontweight="bold")
    if idx//2==1: ax.set_xlabel("relative suffix horizon")
    else: ax.tick_params(labelbottom=False)
    if idx%2==0: ax.set_ylabel("pooled RMSE")
    else: ax.tick_params(labelleft=False)
    if idx==0:
        ax.legend(loc="upper left",ncol=2,fontsize=6.2,framealpha=.95,
                  columnspacing=.9,handlelength=2.2,borderpad=.3)

ax=fig.add_subplot(outer[1,0])
summary=[]
for split in split_order:
    vals=np.array([float(r["delta_mse"]) for r in rec if r["split"]==split and r["delta_mse"] not in ("","nan")]);summary.append(vals[np.isfinite(vals)])
for y,split in enumerate(split_order):
    r=est[split];point=float(r["point_delta_mse"]);lo=float(r["ci95_low"]);hi=float(r["ci95_high"])
    ax.errorbar(point,y,xerr=[[point-lo],[hi-point]],fmt="o",color=BLUE,ms=4.5,capsize=3,lw=1.2)
ax.axvline(0,color=BLACK,lw=1);ax.set_yticks(range(4),[split_names[s] for s in split_order]);ax.invert_yaxis()
ax.set_xlabel("ΔMSE: donor − normal A");ax.set_title("B. Receiver-equal estimate",loc="left",fontweight="bold")

ax=fig.add_subplot(outer[1,1])
bp=ax.boxplot(summary,patch_artist=True,widths=.55,whis=(5,95),showmeans=True,showfliers=False,
 meanprops={"marker":"D","markerfacecolor":BLUE,"markeredgecolor":"white","markersize":4},medianprops={"color":ORANGE,"linewidth":1.2})
for patch in bp["boxes"]:patch.set_facecolor("#DDEBF4");patch.set_edgecolor("#5E6C78")
ax.axhline(0,color=BLACK,lw=1);ax.set_xticks(range(1,5),[split_names[s] for s in split_order],rotation=20)
ax.set_ylabel("receiver-level ΔMSE");ax.set_title("C. Receiver distribution",loc="left",fontweight="bold")

ax=fig.add_subplot(outer[1,2])
for split in split_order:
    x=np.array([float(r["state_A_donor_l1"]) for r in rec if r["split"]==split]);y=np.array([float(r["donor_A_output_mae"]) for r in rec if r["split"]==split])
    keep=np.isfinite(x)&np.isfinite(y);x,y=x[keep],y[keep];rho,_=spearmanr(x,y);order=np.argsort(x,kind="mergesort");x,y=x[order],y[order]
    gx=[];gy=[]
    for start in range(0,len(x),10):
        if len(x)-start<5:break
        gx.append(float(np.median(x[start:start+10])));gy.append(float(np.median(y[start:start+10])))
    ax.scatter(gx,gy,s=5.5,alpha=.30,linewidths=0,color=split_colors[split],rasterized=True,label=f"{split_names[split]} ρ={rho:.2f}")
ax.set_xlim(0,1.18);ax.set_ylim(-.002,.095);ax.set_xlabel("state distance L1");ax.set_ylabel("future-output MAE")
ax.set_title("D. State–output association (10:1)",loc="left",fontweight="bold")
ax.legend(loc="upper left",fontsize=6.3,framealpha=.95,borderpad=.3,handletextpad=.35)
save(fig,"selected","图7_共同后缀与状态作用_最终")

# Auditable alternatives: raw receiver cloud and the eight-equal-count summary.
for mode,name,title in [("raw","图7D_原始receiver散点","Raw receiver scatter"),("binned","图7D_8等频分箱中位数与IQR","Eight equal-count bins: median and IQR")]:
    f,a=plt.subplots(figsize=(5.6,4.0))
    for split in split_order:
        x=np.array([float(r["state_A_donor_l1"]) for r in rec if r["split"]==split]);y=np.array([float(r["donor_A_output_mae"]) for r in rec if r["split"]==split])
        keep=np.isfinite(x)&np.isfinite(y);x,y=x[keep],y[keep];rho,_=spearmanr(x,y);c=split_colors[split]
        if mode=="raw":
            a.scatter(x,y,s=4,alpha=.12,linewidths=0,color=c,rasterized=True,label=f"{split_names[split]} ρ={rho:.2f}")
        else:
            edges=np.unique(np.quantile(x,np.linspace(0,1,9)));bins=np.clip(np.digitize(x,edges[1:-1],right=True),0,len(edges)-2)
            xb=[];med=[];q1=[];q3=[]
            for b in range(len(edges)-1):
                m=bins==b
                if m.sum()<5:continue
                xb.append(np.median(x[m]));med.append(np.median(y[m]));q1.append(np.quantile(y[m],.25));q3.append(np.quantile(y[m],.75))
            a.fill_between(xb,q1,q3,color=c,alpha=.08,linewidth=0);a.plot(xb,med,color=c,marker="o",ms=3,lw=1.2,label=f"{split_names[split]} ρ={rho:.2f}")
    a.set_xlabel("state distance L1 (A vs donor)");a.set_ylabel("future-output MAE");a.set_title(title,loc="left",fontweight="bold")
    a.legend(loc="upper left",fontsize=7,framealpha=.95);f.subplots_adjust(left=.14,right=.98,top=.91,bottom=.14)
    save(f,"alternatives",name)
