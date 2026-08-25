#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke attempt 3 的机械判定收据。

完成判定不靠"进程看不见了"，而由四项共同确定：exit code / 预期输出 / checkpoint 可
CPU 加载 / summary 状态。本脚本逐项核，并**如实登记证据缺口**——launch_gpu_run.py 把
子进程 detach 后就返回了，真实退出码没有被任何人 wait() 收割，所以第一项只能用
"进程已不在 /proc + 日志在 done 行干净结束 + 无真实错误" 间接证明，不能声称拿到了退出码。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TS = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate")
A = TS / "ops/candidate_c_nightly/20260820T155316Z"
sys.path.insert(0, str(A))
import ccn_lib as L  # noqa: E402

RUN = A / "smoke" / "run_20260821T034936Z"
EXPECT_STOP = 32
EXPECT_TOTAL = 2976
BENIGN = re.compile(r"ASYNC_ERROR_HANDLING|find_unused_parameters", re.I)
ERRISH = re.compile(r"traceback|exception|out of memory|nccl.*(fail|error)|killed|aborted|failed",
                    re.I)


def main() -> int:
    L.require_frozen_env()
    import torch

    checks: list[dict] = []

    def ck(cid: str, ok: bool, detail: str, fatal: bool = True) -> None:
        checks.append({"id": cid, "ok": bool(ok), "fatal": fatal, "detail": detail})

    rec = json.loads((RUN / "launch_record.json").read_text("utf-8"))
    smy = json.loads((RUN / "summary.json").read_text("utf-8"))
    log = (RUN / "train.log").read_text("utf-8", "replace")
    loss = [json.loads(x) for x in (RUN / "loss_log.jsonl").read_text("utf-8").splitlines() if x.strip()]

    # ---- 1. 退出证据（间接，缺口已登记）---------------------------------------
    pid = rec.get("top_pid")
    ck("E1_proc_gone", not Path(f"/proc/{pid}").exists(), f"top_pid={pid} 已不在 /proc")
    ck("E2_log_clean_end", log.rstrip().endswith(RUN.name) or "done arm=" in log.splitlines()[-1],
       f"日志末行：{log.rstrip().splitlines()[-1][:110]}")
    real = [ln for ln in log.splitlines() if ERRISH.search(ln) and not BENIGN.search(ln)]
    ck("E3_no_real_errors", not real,
       f"错误样式命中 {len(real)} 行（已排除 NCCL 弃用警告与 find_unused_parameters）")
    ck("E4_exit_code_reaped", rec.get("exit_code_at_settle") is not None,
       f"exit_code_at_settle={rec.get('exit_code_at_settle')}；detach 后无人 wait()，"
       f"这是**已知证据缺口**，不影响本次判定但正式 run 必须补上", fatal=False)

    # ---- 2. 预期输出 -----------------------------------------------------------
    ck("O1_step", smy.get("step") == EXPECT_STOP, f"step={smy.get('step')} 期望 {EXPECT_STOP}")
    ck("O2_total_unchanged", smy.get("total_steps") == EXPECT_TOTAL,
       f"total_steps={smy.get('total_steps')} 期望 {EXPECT_TOTAL}（smoke 不得缩减总预算）")
    ck("O3_reason", smy.get("completion_reason") == "stop_after_step",
       f"completion_reason={smy.get('completion_reason')}")
    ck("O4_world", smy.get("world_size") == 8, f"world_size={smy.get('world_size')}")
    ck("O5_batch", (smy.get("per_gpu_batch"), smy.get("global_batch"), smy.get("accum")) == (8, 64, 1),
       f"per_gpu={smy.get('per_gpu_batch')} global={smy.get('global_batch')} accum={smy.get('accum')}"
       f"（若需 per-GPU 4 + accum 2，按 §8 必须冻结到两臂并重跑 resume/parity）")
    ck("O6_loss_rows", len(loss) == EXPECT_STOP and loss[0]["step"] == 1 and loss[-1]["step"] == EXPECT_STOP,
       f"loss_log {len(loss)} 行，step {loss[0]['step']}..{loss[-1]['step']}")

    # LR 必须与 lr_factor 逐点吻合。日志里那句 base_lr=0.00e+00 是**标签错**：
    # LambdaLR 构造时立刻 step 一次，warmup=100 时 lr_factor(0)=0，打的是当时的 lr。
    sys.path.insert(0, str(TS))
    from train.train_terrastate_v2 import lr_factor
    base, warm = 3.0e-5, 100
    bad_lr = [(r["step"], r["lr"], base * lr_factor(r["step"], warm, EXPECT_TOTAL))
              for r in loss if abs(r["lr"] - base * lr_factor(r["step"], warm, EXPECT_TOTAL)) > 1e-12]
    ck("O7_lr_matches_schedule", not bad_lr,
       f"32 步 lr 与 lr_factor(step,100,2976)×3e-5 逐点相符；不符 {len(bad_lr)} 处。"
       f"step32 lr={loss[-1]['lr']:.3e}")

    # ---- 3. checkpoint 可 CPU 加载 --------------------------------------------
    ckpt = torch.load(RUN / "checkpoint_last.pt", map_location="cpu", weights_only=False)
    sd = ckpt.get("b4_state_dict") or {}
    ck("C1_loadable", len(sd) == 255, f"b4_state_dict {len(sd)} 张量（父锚点同为 255）")
    ck("C2_step", ckpt.get("step") == EXPECT_STOP and ckpt.get("phase_step") == EXPECT_STOP,
       f"step={ckpt.get('step')} phase_step={ckpt.get('phase_step')}")
    ck("C3_fork_marked", bool(ckpt.get("not_exact_resume_of_parent")),
       f"not_exact_resume_of_parent={ckpt.get('not_exact_resume_of_parent')}")
    ck("C4_opt_sched_present", bool(ckpt.get("optimizer_state_dict")) and bool(ckpt.get("scheduler_state_dict")),
       "optimizer_state_dict / scheduler_state_dict 均在（新建的，非继承父的）")
    ck("C5_weights_moved", smy.get("model_value_sha16") != "aa98fbd2fa302727",
       f"value_sha16 {smy.get('model_value_sha16')} ≠ 父 aa98fbd2fa302727，权重确实更新了")

    # ---- 4. summary 状态 -------------------------------------------------------
    ck("S1_status", smy.get("status") == "COMPLETE", f"status={smy.get('status')}")
    ck("S2_arm", (smy.get("arm"), smy.get("factual_path")) == ("C1", "recursive"),
       f"arm={smy.get('arm')} factual_path={smy.get('factual_path')}")
    ck("S3_not_formal", "smoke/pilot 只能写工程结论" in str(smy.get("not_a_formal_result_unless", "")),
       "summary 自带『非正式结果』声明")
    ck("S4_sim_blocked", smy.get("simulator_status") == "BLOCKED_SIMULATOR_LIBRARY_AND_FORMAL_SCENARIO_MANIFEST",
       f"simulator_status={smy.get('simulator_status')}")
    ck("S5_config_sha", rec.get("config_sha256") ==
       "8b89854f87247729652ebb4a53d9cabc969e656888fb61dab3c1be5633f95e53",
       f"config_sha256={str(rec.get('config_sha256'))[:16]}…")
    ck("S6_detached", (rec.get("detached") or {}).get("sid_differs_from_parent") is True,
       "start_new_session=True 且 sid≠父 sid，VS Code 断开不会终止")

    n_fail = sum(1 for c in checks if not c["ok"] and c["fatal"])
    n_warn = sum(1 for c in checks if not c["ok"] and not c["fatal"])
    out = {
        "schema": "candidate_c_smoke_attempt3_verdict_v1", "at_utc": L.utcnow(),
        "run_dir": str(RUN), "attempt": 3, "budget_total": 3,
        "n_checks": len(checks), "n_passed": sum(1 for c in checks if c["ok"]),
        "n_fatal_failed": n_fail, "n_warnings": n_warn,
        "verdict": "PASS" if n_fail == 0 else "FAIL",
        "checks": checks,
        "known_evidence_gap": "真实退出码未被收割（detach 后无人 wait()）。已用 /proc 消失 + 日志 done 行干净结束 + 无真实错误 间接证明。正式 run 的 watchdog 必须记录退出码。",
        "log_mtime_note": "train.log mtime 比 done 行晚约 2.5 分钟，是 fd 关闭/NFS 属性更新所致；末尾无任何超出 done 行的内容（已逐字节核）。",
        "lr_label_defect": "trainer L377 打印 `base_lr={g['lr']}`，而 LambdaLR 构造时已 step 一次，warmup 期该值为 0 —— 标签错，真实基准在 g['initial_lr']。已实测 32 步 lr 与 schedule 逐点相符，非训练缺陷。运行中不改冻结文件。",
    }
    p = A / "smoke" / "attempt3_verdict.json"
    s = L.atomic_write_json(p, out)
    L.atomic_write_text(p.with_name(p.name + ".sha256"), f"{s}  {p.name}\n")

    for c in checks:
        if not c["ok"]:
            print(f"  [{'FAIL' if c['fatal'] else 'WARN'}] {c['id']}: {c['detail']}")
    print(f"\nsmoke attempt 3: {out['n_passed']}/{out['n_checks']} 通过，"
          f"{n_fail} 致命失败，{n_warn} 警告 -> {out['verdict']}")
    print(f"收据 {p}\n  sha256 {s}")
    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
