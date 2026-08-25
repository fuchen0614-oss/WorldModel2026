#!/usr/bin/env python
"""按 pilot_pass_criteria.json 逐条机械判定 128-update pilot。

判据在看到任何 pilot 数字之前就冻结了（registered_before_seeing_results: true），
本脚本只读那份文件、不重写它。P6 已知无法满足——不在这里悄悄放宽，而是单列
为 UNSATISFIABLE_BY_DESIGN 并把裁决权交回用户。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE.parent
TS = ATTEMPT.parents[2]
sys.path.insert(0, str(ATTEMPT))
sys.path.insert(0, str(TS))
import ccn_lib as L


def main() -> int:
    # 解释器身份闸门：与其余入口脚本一致，错解释器 fail closed。
    L.require_frozen_env()

    run = HERE / "run_20260821T040602Z"
    crit = json.loads((HERE / "pilot_pass_criteria.json").read_text("utf-8"))
    summ = json.loads((run / "summary.json").read_text("utf-8"))
    info = json.loads((run / "launch_info.json").read_text("utf-8"))
    loss = [json.loads(x) for x in (run / "loss_log.jsonl").read_text("utf-8").splitlines() if x.strip()]
    log = (run / "train.log").read_text("utf-8", "replace")

    R: list[dict] = []

    def ck(cid: str, ok: bool, detail: str, fatal: bool = True) -> bool:
        R.append({"id": cid, "ok": bool(ok), "fatal": fatal, "detail": detail})
        return bool(ok)

    # ---- P1：跑满 128 ----
    ck("P1_runs_to_128",
       summ["step"] == 128 and len(loss) == 128
       and summ["completion_reason"] == "stop_after_step" and summ["status"] == "COMPLETE",
       f"step={summ['step']} rows={len(loss)} reason={summ['completion_reason']} status={summ['status']}")

    # ---- P2：无 OOM ----
    oom = [ln for ln in log.splitlines() if "out of memory" in ln.lower() or "CUDA out of memory" in ln]
    ck("P2_no_oom", not oom,
       f"per_gpu_batch={summ['per_gpu_batch']} accum={summ['accum']} "
       f"global={summ['global_batch']}; OOM 行={len(oom)}")

    # ---- P3：损失全有限 ----
    fields = ("total", "eo_traj", "eo_endpoint")
    bad = [(r["step"], f, r[f]) for r in loss for f in fields
           if not isinstance(r.get(f), (int, float))
           or r[f] != r[f] or abs(r[f]) == float("inf")]
    ck("P3_no_nan_inf", not bad, f"检查 {len(loss)}×{len(fields)} 个值；非有限={bad[:5]}")

    # ---- P4：不发散（末 20 均值 ≤ 首 20 均值 × 3.0）----
    f20 = sum(r["total"] for r in loss[:20]) / 20
    l20 = sum(r["total"] for r in loss[-20:]) / 20
    ck("P4_no_divergence", l20 <= f20 * 3.0,
       f"首20均值={f20:.6f} 末20均值={l20:.6f} 比值={l20 / f20:.3f} 阈值=3.0")

    # ---- P5：lr 与 schedule 逐点相符 ----
    from train.train_terrastate_v2 import lr_factor
    base, warm, tot = 3.0e-5, 100, 2976
    off = [(r["step"], r["lr"], base * lr_factor(r["step"], warm, tot))
           for r in loss if abs(r["lr"] - base * lr_factor(r["step"], warm, tot)) > 1e-12]
    ck("P5_lr_matches_schedule", not off,
       f"base={base:.1e} warmup={warm} total={tot}；逐点偏差>1e-12 的步={off[:5]}；"
       f"lr(1)={loss[0]['lr']:.3e} lr(128)={loss[-1]['lr']:.3e}")

    # ---- P6：无法满足（设计缺陷，不放宽）----
    R.append({
        "id": "P6_val_dev_computable", "ok": False, "fatal": True,
        "status": "UNSATISFIABLE_BY_DESIGN", "counted_in_pass_fail": False,
        "detail": (
            "trainer 触发条件 train/train_terrastate_candidate_c.py:582 为 "
            "`step % val_interval == 0 or step == total_steps`；val_interval=372、"
            "pilot 停在 128、total_steps=2976，故 128%372!=0 且 128!=2976，"
            f"val 永不触发。summary.best_val_dev_endpoint_mse={summ['best_val_dev_endpoint_mse']} 予以佐证。"),
        "root_cause": "我写判据时的疏忽：P6 与被授权的 ~128 步 pilot 长度 + 冻结的 val_interval=372 三者互斥。",
        "why_not_self_fixed": (
            "val_interval 在 pilot_contract.json 的 must_inherit_unchanged 内；延长到 372 步属于"
            "改训练步数。两者都在用户明示的『立即停止汇报，不得自行调整后继续』范围内。"),
        "partial_evidence_val_path_not_untested": [
            "启动时 val split 已解析加载（validation_subsplit.val_dev.ids，476/952）",
            "data manifest 现场校验通过（train=17c645d92e9dd4c3 val=555d44c0d59ab390）",
            "val 计算路径由 CPU contract 套件覆盖并通过",
            "未被覆盖的仅剩：8-rank GPU 上一次真实 val forward pass",
        ],
        "decision_owner": "user",
    })

    # ---- P7：checkpoint 可 CPU 加载 ----
    # 键名以现场 checkpoint 为准：b4_state_dict / optimizer_state_dict / scheduler_state_dict。
    import torch
    ckpt = torch.load(run / "checkpoint_last.pt", map_location="cpu", weights_only=False)
    sd = ckpt["b4_state_dict"]
    ck("P7_ckpt_loadable",
       len(sd) == 255 and ckpt.get("phase_step") == 128 and ckpt.get("step") == 128
       and isinstance(ckpt.get("optimizer_state_dict"), dict)
       and isinstance(ckpt.get("scheduler_state_dict"), dict)
       and ckpt.get("total_steps") == 2976 and ckpt.get("world_size") == 8,
       f"tensors={len(sd)} phase_step={ckpt.get('phase_step')} step={ckpt.get('step')} "
       f"total_steps={ckpt.get('total_steps')} world_size={ckpt.get('world_size')} "
       f"opt_sd={type(ckpt.get('optimizer_state_dict')).__name__} "
       f"sched_sd={type(ckpt.get('scheduler_state_dict')).__name__} "
       f"rng_states_by_rank={len(ckpt.get('rng_states_by_rank', []))}")

    # ---- P8：参数与正式 C1 逐字一致，无 override ----
    want = {"per_gpu_batch": 8, "global_batch": 64, "accum": 1, "seed": 42,
            "total_steps": 2976, "world_size": 8, "arm": "C1", "factual_path": "recursive"}
    diff = {k: (summ.get(k), v) for k, v in want.items() if summ.get(k) != v}
    lam = summ.get("lambdas", {})
    nz = {k: v for k, v in lam.items() if v != 0.0}
    ov = info.get("overrides", []) or []
    ck("P8_params_unchanged", not diff and not nz and not ov,
       f"不符项={diff} 非零λ={nz} overrides={ov} λ={lam}")

    # ---- P9：无禁用 split ----
    hits = [ln for ln in log.splitlines()
            if ("test" in ln.lower() or "ood" in ln.lower())
            and "val_dev" not in ln and "validation_subsplit" not in ln]
    ck("P9_no_forbidden_split", not hits, f"可疑行={len(hits)}: {hits[:3]}")

    # ---- P10：梯度有限 ----
    # trainer 把 clip_grad_norm_ 的返回值丢弃了（:545），grad_norm 从不落日志，diag 里也没有。
    # 所以按现场可观测量判定，并明确标注这是间接证据：
    #   a) 非有限窗会打 "WARN 非有限 loss 窗口" 并对称跳过更新（:534-541）——零次出现；
    #   b) 跳过路径的 continue 在 rank0 写 loss 行之前，故 128 行 == 128 次真实更新，无静默跳过；
    #   c) checkpoint 里 255 个张量全有限——非有限梯度经 clip+Adam 会污染参数。
    warn_nf = [ln for ln in log.splitlines() if "非有限 loss 窗口" in ln]
    nonfinite_params = [k for k, v in sd.items()
                        if torch.is_tensor(v) and not bool(torch.isfinite(v).all())]
    steps_seen = sorted(r["step"] for r in loss)
    no_silent_skip = steps_seen == list(range(1, 129))
    R.append({"id": "P10_grad_finite",
              "ok": not warn_nf and not nonfinite_params and no_silent_skip,
              "fatal": True, "evidence_kind": "indirect",
              "detail": (f"非有限窗 WARN={len(warn_nf)} 次；loss 行 step 序列连续 1..128={no_silent_skip}"
                         f"（无静默跳过）；checkpoint 非有限张量={len(nonfinite_params)}/{len(sd)}"),
              "caveat": ("grad_norm 本身未被 trainer 记录（clip_grad_norm_ 返回值在 :545 被丢弃），"
                         "本条为间接证据而非直接测量。正式 run 若要直接测量需改 trainer——"
                         "属于改动冻结代码，本轮不做。")})

    # ---- P10 的直接可观测替代：把 grad_norm 缺失单列，供正式 run 决策 ----
    R.append({"id": "OBS_grad_norm_not_logged", "ok": True, "fatal": False,
              "counted_in_pass_fail": False,
              "detail": "已登记的可观测性缺口：正式 C1/C0R 同样不会有 grad_norm 记录。"})

    # ---- 警告（非致命，预注册）----
    W = [{"id": "W1_warmup_dominates", "note":
          f"warmup=100 vs pilot 128 步 → 仅约 28 步接近满 lr（lr(128)={loss[-1]['lr']:.3e} "
          f"= base×{loss[-1]['lr'] / base:.4f}）。短 pilot 的固有代表性局限，未为此改动任何参数。"},
         {"id": "W2_lr_label_defect", "note":
          "trainer 打印的 base_lr 实为 LambdaLR 构造即 step 一次后的当前 lr，warmup 期显示 "
          "0.00e+00；标签缺陷，非训练缺陷，P5 已逐点证明 schedule 正确。"}]

    counted = [r for r in R if r.get("counted_in_pass_fail") is not False]
    fail = [r for r in counted if r["fatal"] and not r["ok"]]
    unsat = [r for r in R if r.get("status") == "UNSATISFIABLE_BY_DESIGN"]
    verdict = ("PASS_EXCEPT_P6_UNSATISFIABLE" if not fail and unsat
               else "PASS" if not fail else "FAIL")

    rec = {"schema": "candidate_c_pilot_verdict_v1", "ts_utc": L.utcnow(),
           "run_dir": str(run), "criteria_file": str(HERE / "pilot_pass_criteria.json"),
           "criteria_sha256": L.sha256_file(HERE / "pilot_pass_criteria.json"),
           "criteria_registered_before_results": crit.get("registered_before_seeing_results"),
           "elapsed_sec": summ["elapsed_sec"], "step": summ["step"],
           "model_value_sha16": summ["model_value_sha16"],
           "n_counted": len(counted), "n_passed": len(counted) - len(fail),
           "n_failed": len(fail), "n_unsatisfiable": len(unsat),
           "checks": R, "warnings": W, "verdict": verdict,
           "blocks_formal_launch": bool(unsat) or bool(fail),
           "not_a_formal_result": "pilot 只是工程闸门，不得写成正式结果，也不用于选模。",
           "criteria_were_not_relaxed_after_seeing_results": True}
    sha = L.atomic_write_json(HERE / "pilot_verdict.json", rec)

    print("=" * 74)
    for r in R:
        tag = ("UNSAT" if r.get("status") == "UNSATISFIABLE_BY_DESIGN"
               else " ok  " if r["ok"] else "FAIL ")
        print(f"[{tag}] {r['id']}\n        {r['detail'][:150]}")
    for w in W:
        print(f"[WARN ] {w['id']}\n        {w['note'][:150]}")
    print("=" * 74)
    print(f"  计入判定 {len(counted) - len(fail)}/{len(counted)} 通过，"
          f"失败 {len(fail)}，设计上无法满足 {len(unsat)}")
    print(f"  verdict={verdict}  blocks_formal_launch={rec['blocks_formal_launch']}")
    print(f"  receipt sha256={sha}")
    print("=" * 74)
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
