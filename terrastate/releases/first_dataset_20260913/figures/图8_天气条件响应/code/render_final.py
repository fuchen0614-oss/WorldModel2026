#!/usr/bin/env python3
from pathlib import Path
import csv, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize, ListedColormap

FIG=Path(__file__).resolve().parents[1]
BLUE,ORANGE,GREEN,BLACK="#0072B2","#D55E00","#009E73","#24272B"

def read(path):
    with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def save(fig,name,dpi=300):
    p=FIG/"selected"/name;p.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(p.with_suffix(".png"),dpi=dpi,bbox_inches="tight",pad_inches=.05,facecolor="white")
    fig.savefig(p.with_suffix(".pdf"),bbox_inches="tight",pad_inches=.05,facecolor="white")
    plt.close(fig)
def cmap(name,bad="#777777"):
    c=plt.get_cmap(name).copy();c.set_bad(bad);return c
def traj(a,v):
    return np.array([float(a[h][v[h]>0].mean()) if (v[h]>0).any() else np.nan for h in range(len(a))])

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.0,"axes.titlesize":8.8,
 "axes.labelsize":8.2,"axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,
 "grid.alpha":.28,"grid.color":"#BFC7D1","legend.frameon":True,"legend.facecolor":"white",
 "legend.edgecolor":"#BFC5CC"})
table=read(FIG/"data"/"Table5_weather_response.csv")
effects=[r for r in table if r["section"]=="actual_loss_benefit"]

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

_ARRAYS=_pick(FIG/"data"/"_arrays"/"W02"/"arrays.npz",
              ROOT/"reproduction"/"W02_arrays"/"arrays.npz")
_META=_pick(FIG/"data"/"_arrays"/"W02"/"metadata.json",
            ROOT/"reproduction"/"W02_arrays"/"metadata.json")
z=np.load(_ARRAYS)
meta=json.loads(_META.read_text(encoding="utf-8"))
x=np.arange(1,21)

# Main A/B summary; B keeps all standardized weather inputs in one flat panel.
fig,axes=plt.subplots(1,2,figsize=(7.35,3.15),gridspec_kw={"width_ratios":[1.25,2.15]})
ax=axes[0]
effect_positions=[.64,.36]
for yidx,(r,label) in zip(effect_positions,zip(effects,["actual vs donor","actual vs mean"])):
    val=float(r["value"]);lo=float(r["paired_ci_low"]);hi=float(r["paired_ci_high"])
    ax.errorbar(val,yidx,xerr=[[val-lo],[hi-val]],fmt="o",color=BLUE,ms=4.8,capsize=3,lw=1.25)
    text_y=yidx+(.085 if yidx>.5 else -.085)
    ax.text(.97,text_y,f"{val:.4f} [{lo:.4f}, {hi:.4f}]",transform=ax.get_yaxis_transform(),
            ha="right",va="center",fontsize=5.8,color=BLUE)
ax.axvline(0,color=BLACK,lw=1);ax.set_yticks(effect_positions,["actual vs donor","actual vs mean"]);ax.set_ylim(.18,.82)
ax.set_xlabel("loss benefit (MSE)");ax.set_title("A. Overall effect",loc="left",fontweight="bold");ax.grid(axis="y",visible=False)
ax.text(.98,.04,"n = 84 paired cases",transform=ax.transAxes,ha="right",va="bottom",fontsize=6.2,color="#5E6670")

ax=axes[1]
features=[(4,"rain",BLUE),(5,"mean temperature",ORANGE),(3,"shortwave radiation",GREEN)]
for col,label,color in features:
    ax.plot(x,z["weather_actual"][:,col],color=color,lw=1.45,ls="-")
    ax.plot(x,z["weather_donor"][:,col],color=color,lw=1.3,ls="--")
ax.set_xlim(1,20);ax.set_ylim(-.6,3.25);ax.set_xticks([1,5,10,15,20]);ax.set_xlabel("target step (5-day interval)");ax.set_ylabel("standardized weather (z)")
ax.set_title("B. W02 weather inputs",loc="left",fontweight="bold")
rain=Line2D([0],[0],color=BLUE,lw=1.6,label="rain")
mean_temp=Line2D([0],[0],color=ORANGE,lw=1.6,label="mean temperature")
actual=Line2D([0],[0],color=BLACK,lw=1.5,ls="-",label="actual")
shortwave=Line2D([0],[0],color=GREEN,lw=1.6,label="shortwave radiation")
donor=Line2D([0],[0],color=BLACK,lw=1.4,ls="--",label="donor")
# Matplotlib fills multi-column legends down columns. This order renders as:
# row 1: rain, actual, donor; row 2: mean temperature, shortwave radiation.
ax.legend(handles=[rain,mean_temp,actual,shortwave,donor],loc="upper left",bbox_to_anchor=(.01,.985),
          ncol=3,fontsize=6.15,framealpha=.96,columnspacing=.8,handlelength=1.75,borderpad=.35)
fig.subplots_adjust(left=.105,right=.985,top=.94,bottom=.18,wspace=.27)
save(fig,"图8_天气响应总体与输入过程_最终")

# W02 spatial and trajectory detail with independent, explicitly labelled scales.
gt,v=z["gt"],z["valid"]
pa,pd,pm=z["pred_actual"],z["pred_donor"],z["pred_mean"]
vf=v.mean(axis=(1,2));h=len(vf)-1-int(np.argmax(vf[::-1]));valid=v[h]>0
fig=plt.figure(figsize=(8.25,7.25))
outer=fig.add_gridspec(3,1,height_ratios=[1,1,1.15],left=.055,right=.985,top=.965,bottom=.075,hspace=.56)
top=outer[0].subgridspec(1,4,wspace=.08);mid=outer[1].subgridspec(1,4,wspace=.08);bottom=outer[2].subgridspec(1,2,wspace=.34)
top_axes=[];last_nd=None
for j,(title,arr) in enumerate([("A. Ground truth",gt[h]),("actual weather",pa[h]),("donor weather",pd[h]),("mean weather",pm[h])]):
    a=fig.add_subplot(top[0,j]);top_axes.append(a);last_nd=a.imshow(np.where(valid,arr,np.nan),cmap=cmap("viridis"),vmin=0,vmax=1,interpolation="nearest")
    a.set_title(title);a.set_xticks([]);a.set_yticks([]);a.grid(False)
mid_axes=[]
err=np.abs(pa[h]-gt[h]);diff_d=pd[h]-pa[h];diff_m=pm[h]-pa[h]
for j,(title,arr,cm,lo,hi) in enumerate([("B. |actual − truth|",err,"magma",0,.4),("donor − actual",diff_d,"coolwarm",-.4,.4),("mean − actual",diff_m,"coolwarm",-.4,.4)]):
    a=fig.add_subplot(mid[0,j]);mid_axes.append(a);im=a.imshow(np.where(valid,arr,np.nan),cmap=cmap(cm),vmin=lo,vmax=hi,interpolation="nearest")
    if j==0:err_im=im
    else:diff_im=im
    a.set_title(title);a.set_xticks([]);a.set_yticks([]);a.grid(False)
a=fig.add_subplot(mid[0,3]);a.imshow(valid.astype(int),cmap=ListedColormap(["#8B8F94","#FFFFFF"]),vmin=0,vmax=1,interpolation="nearest")
a.set_title("valid mask");a.set_xticks([]);a.set_yticks([]);a.grid(False)

tg,ta,td,tm=traj(gt,v),traj(pa,v),traj(pd,v),traj(pm,v)
a1=fig.add_subplot(bottom[0,0]);a1.plot(x,tg,color=BLACK,lw=1.6,label="truth");a1.plot(x,ta,color=BLUE,lw=1.35,label="actual");a1.plot(x,td,color=ORANGE,lw=1.25,ls="--",label="donor");a1.plot(x,tm,color=GREEN,lw=1.25,ls=":",label="mean")
a1.set_xlim(1,20);a1.set_ylim(0,1);a1.set_xticks([1,5,10,15,20]);a1.set_xlabel("target step (5-day interval)");a1.set_ylabel("spatial-mean NDVI");a1.set_title("C. Output trajectories",loc="left",fontweight="bold");a1.legend(loc="upper right",ncol=2,fontsize=6.7,framealpha=.95)
a2=fig.add_subplot(bottom[0,1])
for name,arr,color,ls in [("actual",pa,BLUE,"-"),("donor",pd,ORANGE,"--"),("mean",pm,GREEN,":")]:
    rm=np.array([float(np.sqrt(np.mean((arr[k][v[k]>0]-gt[k][v[k]>0])**2))) if (v[k]>0).any() else np.nan for k in range(20)])
    a2.plot(x,rm,color=color,ls=ls,lw=1.3,label=name)
a2.set_xlim(1,20);a2.set_xticks([1,5,10,15,20]);a2.set_xlabel("target step (5-day interval)");a2.set_ylabel("RMSE vs observed truth",labelpad=7);a2.set_title("D. Factual error",loc="left",fontweight="bold");a2.legend(loc="upper left",fontsize=6.7,framealpha=.95)

fig.canvas.draw()
tp0,tp3=top_axes[0].get_position(),top_axes[-1].get_position()
mp0,mp1,mp2=mid_axes[0].get_position(),mid_axes[1].get_position(),mid_axes[2].get_position()
c1=fig.add_axes([tp0.x0,tp0.y0-.040,tp3.x1-tp0.x0,.012])
cb=fig.colorbar(last_nd,cax=c1,ticks=[0,.5,1],orientation="horizontal");cb.set_label("NDVI: low → high",fontsize=6.5,labelpad=1);cb.ax.tick_params(labelsize=6,pad=1)
c2=fig.add_axes([mp0.x0,mp0.y0-.040,mp0.width,.012])
cb=fig.colorbar(err_im,cax=c2,ticks=[0,.2,.4],extend="max",orientation="horizontal");cb.set_label("|error|: low → high",fontsize=6.5,labelpad=1);cb.ax.tick_params(labelsize=6,pad=1)
c3=fig.add_axes([mp1.x0,mp1.y0-.040,mp2.x1-mp1.x0,.012])
cb=fig.colorbar(diff_im,cax=c3,ticks=[-.4,0,.4],orientation="horizontal");cb.set_label("signed Δ: blue < 0 < red",fontsize=6.5,labelpad=1);cb.ax.tick_params(labelsize=6,pad=1)
save(fig,"图8_W02空间与轨迹_最终")
