# Future-State Anchor Ablation — Internal Record

Date: 2026-07-29  
Status: Internal only; not for manuscript inclusion

## Frozen reference: Full TerraState

### Validation

- \(R^2 = 0.49732\)
- RMSE \(= 0.15729\)
- State-removal official \(\Delta R^2 = 0.01121\)
- Paired \(\Delta R^2 = 0.01616\)
- Paired 95% CI \(= [0.00643, 0.02590]\)

### OOD-t

- \(R^2 = 0.56935\)
- RMSE \(= 0.15059\)
- State-removal official \(\Delta R^2 = 0.01997\)
- Paired \(\Delta R^2 = 0.02200\)
- Paired 95% CI \(= [0.01422, 0.03018]\)

## Ablation: w/o future-state anchor

### Validation

- \(R^2 = 0.49723\)
- RMSE \(= 0.15724\)
- State-removal official \(\Delta R^2 = 0.01112\)
- Paired \(\Delta R^2 = 0.01665\)
- Paired 95% CI \(= [0.00680, 0.02670]\)

### OOD-t

- \(R^2 = 0.57353\)
- RMSE \(= 0.14999\)
- State-removal official \(\Delta R^2 = 0.02415\)
- Paired \(\Delta R^2 = 0.02562\)
- Paired 95% CI \(= [0.01722, 0.03402]\)

## Internal conclusion

This ablation does not support the claim that the future-state anchor is necessary for either predictive performance or the load-bearing-state property. It will therefore not be included in the paper as a positive ablation. We will not continue to Q3 for this ablation and will not revise the paper's claims on its basis.

该消融没有支持“future-state anchor 是性能或 load-bearing 性质的必要条件”；因此不作为正向消融写入正文，不继续进行 Q3，也不据此修改论文主张。该文件仅供内部记录。
