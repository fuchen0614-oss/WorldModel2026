import pandas as pd

base = "/csy-mix02/cog8/zjliu17/Agent/TrainData/SSL4EO-S12-v1.1/phi_processed/train/S2L2A"
df = pd.read_parquet(f"{base}/ssl4eos12_shard_000001_phi.parquet")
print("行数:", len(df))
print("列:", list(df.columns))
print()
print(df.head(2).to_string())
print()
for col in df.columns:
    if "cloud" in col.lower():
        s = df[col]
        try:
            print(f"{col}: min={s.min():.4f} max={s.max():.4f} mean={s.mean():.4f}")
        except Exception:
            print(f"{col}: sample={s.iloc[0]}")
