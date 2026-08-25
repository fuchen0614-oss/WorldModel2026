#!/usr/bin/env python
"""M1 — prove the two *input* artifacts are the exact ones the parent checkpoint recorded.

File-level sha256 is not what the trainer asserts.  `train_terrastate_v2.py` records:

  sha.student_init_sha256 = state_sha(init_ck["b4_state_dict"])
  sha.teacher_sha256      = state_sha(teacher.state_dict())   # AFTER loading q.* into
                                                              # a fresh PVTContextformerQ
so the resume assertions can only pass if these *tensor-content* digests match.  This
script recomputes both from the published objects (read-only) and compares against the
parent checkpoint's `sha` block.

Expected (from checkpoint_boundary80.pt):
  student_init_sha256 = 488052d97c7d1c8a2e805d9838f344daef7ad02e5f185d3025031a5f1c026338
  teacher_sha256      = bbe2c3ee6de540ae6eabeb7798f331388112ad370dbcae9533187344f2f8a302

Also recomputes q_projector_init_sha256 (da978b02...) by warm-starting a fresh
TerraStateV2 from the student-init object — that is the value both future-state caches
were built against, and the value the resume asserts.

CPU only.  Writes state_sha_check.json.  Fails closed (exit 1) on any mismatch.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
REPO = Path("/csy-mix02/cog8/zjliu17/Agent/WorldModel2026v2/terrastate")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import torch  # noqa: E402

from models.encoders.pvt_contextformer_q import PVTContextformerQ, contextformer6m_hparams  # noqa: E402
from models.terrastate_v2 import TerraStateV2, warm_start_terrastate_v2  # noqa: E402
from train.terrastate_v2_common import module_pair_sha256, state_sha  # noqa: E402

OPS = Path(__file__).resolve().parent
PUB = json.loads((OPS / "published_artifacts.json").read_text())
BY_ID = {a["logical_id"]: a for a in PUB["artifacts"]}

PARENT = BY_ID["terrastate/v2/legacy-boundary11904@v1"]["object_path"]
STUDENT = BY_ID["obsworld/b4-exclusive/student-main-last-step14880@v1"]["object_path"]
TEACHER = BY_ID["obsworld/b4/teacher-best-step13000@v1"]["object_path"]


def main():
    out = {"parent_object": PARENT, "student_object": STUDENT, "teacher_object": TEACHER}
    parent = torch.load(PARENT, map_location="cpu", weights_only=False)
    expect = parent["sha"]

    init_ck = torch.load(STUDENT, map_location="cpu", weights_only=False)
    teach_ck = torch.load(TEACHER, map_location="cpu", weights_only=False)

    out["student_init_arch"] = init_ck.get("arch")
    out["teacher_arch"] = teach_ck.get("arch")

    # 1) student_init_sha256 = state_sha(b4_state_dict)
    got_student = state_sha(init_ck["b4_state_dict"])
    out["student_init_sha256"] = got_student
    out["student_init_sha256_expected"] = expect["student_init_sha256"]
    out["student_init_match"] = got_student == expect["student_init_sha256"]

    # 2) warm-start a fresh TerraStateV2 exactly as the trainer does, then the INITIAL
    #    frozen (q, projector) identity that both caches were built against.
    hp = contextformer6m_hparams(pvt_pretrained=False)
    student = TerraStateV2(hp, contract_cfg={"state_dim": 256, "freeze_b0": True})
    miss, unexp, src = warm_start_terrastate_v2(student, init_ck)
    out["warm_start_source"] = src
    out["warm_start_missing"] = len(list(miss))
    out["warm_start_unexpected"] = len(list(unexp))
    out["warm_start_exact"] = (len(list(miss)) == 0 and len(list(unexp)) == 0)

    got_qproj = module_pair_sha256(student.q, student.projector)
    out["q_projector_init_sha256"] = got_qproj
    out["q_projector_init_sha256_expected"] = expect["q_projector_init_sha256"]
    out["q_projector_match"] = got_qproj == expect["q_projector_init_sha256"]

    # 3) teacher_sha256 = state_sha(frozen PVTContextformerQ after exact q.* load)
    teacher = PVTContextformerQ(hp)
    q_sd = {k[len("q."):]: v for k, v in teach_ck["b4_state_dict"].items() if k.startswith("q.")}
    t_miss, t_unexp = teacher.load_state_dict(q_sd, strict=False)
    out["teacher_q_keys"] = len(q_sd)
    out["teacher_load_missing"] = len(list(t_miss))
    out["teacher_load_unexpected"] = len(list(t_unexp))
    out["teacher_load_exact"] = (len(list(t_miss)) == 0 and len(list(t_unexp)) == 0)
    teacher.eval()
    got_teacher = state_sha(teacher.state_dict())
    out["teacher_sha256"] = got_teacher
    out["teacher_sha256_expected"] = expect["teacher_sha256"]
    out["teacher_match"] = got_teacher == expect["teacher_sha256"]

    # 4) the parent's own weight identity (for the registry / later bit-compare)
    out["parent_b4_state_sha256"] = state_sha(parent["b4_state_dict"])
    out["parent_step"] = int(parent["step"])
    out["parent_stage"] = int(parent["stage"])

    ok = all(out[k] for k in ("student_init_match", "q_projector_match", "teacher_match",
                              "warm_start_exact", "teacher_load_exact"))
    out["all_match"] = ok
    (OPS / "state_sha_check.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    for k in ("student_init_match", "q_projector_match", "teacher_match",
              "warm_start_exact", "teacher_load_exact"):
        print(f"{k} = {out[k]}", flush=True)
    print(f"student_init_arch={out['student_init_arch']} teacher_arch={out['teacher_arch']}", flush=True)
    print(f"parent_b4_state_sha256={out['parent_b4_state_sha256']}", flush=True)
    print(f"all_match={ok}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
