#!/usr/bin/env python3
"""Part 2a: remove the stale "official baselines unavailable" assertions from the reference master.

The master draft (2026-09-12) predates the baseline inference and the final redraw, so two of its
sentences now assert something false. History is preserved: a banner marks the document as a
superseded master and the two sentences are corrected, without touching any number or conclusion.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REL = Path("/data/zs/WorldModel2026/terrastate/releases/first_dataset_20260913")
P = REL / "figures/references/OVERVIEW_母稿_20260912T112243Z.md"
t = P.read_text(encoding="utf-8")

BANNER = """> **历史母稿，已被取代。** 本文件是 2026-09-12 的叙事母稿，保留用于追溯行文演变；
> **当前以 `narrative/01_TerraState_第一数据集成果总览_十二章继承更新版.md`（十二章版）与
> `narrative/02_TerraState_中文论文叙事稿.md` 为准**。本文件中"图件"一节描述的是**重绘前**的
> 早期图，其后终稿已完成：图3 现已包含四个官方基线（ConvLSTM / PredRNN / SimVP / Contextformer），
> 图3、图5、图6、图7、图8、图9 均已重绘并收录于 `figures/`。文中所有**数值与科学结论未改动**。
"""

anchor = "**版本**：文案重构版（母稿）。本轮只做叙事、表格与证据表达的整理，不新增训练、不新增推理、不改动图件。\n"
if anchor not in t:
    sys.exit("banner anchor not found")
t = t.replace(anchor, anchor + "\n" + BANNER, 1)
print("inserted the historical-master banner")

# ---- the two false sentences
OLD201 = ("**基线的空间预测面板缺失**——Contextformer / PredRNN / ConvLSTM / SimVP 的预测文件与权重"
          "不在本服务器上，因此本图只包含 GT、Persistence 与 C1，没有用任何方法冒名替代；"
          "这些基线的**数值**仍在表 1 中并排比较。")
NEW201 = ("**当时的状态（已过时）**：写作本母稿时四个基线（Contextformer / PredRNN / ConvLSTM / SimVP）"
          "的预测尚未生成，因此这里的早期草图只含 GT、Persistence 与 C1。**该缺口已补齐**："
          "终稿图3 使用匹配的 GreenEarthNet 官方 seed-42 checkpoint 完成四个基线的推理，"
          "正文请以 `figures/图3_标准空间预测/`（终稿）与表 1 为准。")
if OLD201 in t:
    t = t.replace(OLD201, NEW201, 1)
    print("corrected the 3.5 figure note")
else:
    # tolerate the exact wording
    idx = t.find("**基线的空间预测面板缺失**")
    if idx < 0:
        sys.exit("could not find the 3.5 note")
    end = t.find("\n", idx)
    t = t[:idx] + NEW201 + t[end:]
    print("corrected the 3.5 note (by line)")

OLD600 = ("> **共同限制**：四个基线的空间预测文件在本服务器上不可用，因此候选图只包含 GT、Persistence "
          "与 TerraState-C1。基线的**数值**比较在表 1 中完整给出。")
NEW600 = ("> **关于四个基线的说明（已更新）**：写作本母稿时其预测文件尚未生成，候选图曾只含 GT、"
          "Persistence 与 TerraState-C1。**该限制已解除**：终稿图3 已包含四个官方基线"
          "（ConvLSTM / PredRNN / SimVP / Contextformer，来自匹配的 GreenEarthNet 官方 seed-42 "
          "checkpoint），复现数组随包提供（`reproduction/P42_official_baselines.npz`）；"
          "基线的**数值**比较仍在表 1 中完整给出。")
if OLD600 in t:
    t = t.replace(OLD600, NEW600, 1)
    print("corrected the candidate-gallery note")
else:
    sys.exit("could not find the line-600 note")

P.write_text(t, encoding="utf-8")
print(f"wrote {P.relative_to(REL)}  ({len(t):,} B)")

left = [ln for ln in t.splitlines()
        if "不可用" in ln and ("基线" in ln or "baseline" in ln.lower())]
print(f"\nremaining baseline-unavailable lines: {len(left)}")
for ln in left[:5]:
    print("  ", ln.strip()[:160])
