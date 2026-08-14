# TerraState Phase-I B4 教师与精度锚点

- 文件：`checkpoint_best.pt`
- 来源：私有 release `b4-phase1-best`
- 原始名：`checkpoint_best.pt.part-000`（实际为完整单文件，不是缺失分片）
- 大小：28,846,423 B
- SHA-256：`2c5d084236716d84d1ed11289248a501a7cb906675a32ccb8fd73e1f2a26881c`
- metadata：`step=13000`，`arch=ObsWorldB4`，`val_loss=0.0218854040466249`
- 角色：TerraState-V2 的冻结 KD teacher / Phase-I full-weather accuracy anchor。

已在 Plan-B canonical implementation 中构建 `ObsWorldB4` 并严格加载全部 255 个
state entries：missing=0，unexpected=0，参数量 7,180,897，`|gate|=0.11598`。
该权重不是 TerraState-V2 最终权重，不得用于替代 boundary80 或 14,880-step 文件。
