import math
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
