#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Candidate C launcher：把冻结的 YAML 配置翻译成 trainer 的 flag 列表。

为什么需要它：trainer 只吃命令行 flag，不读 YAML。如果 YAML 只是"记录用"，它就会
和真正跑的命令悄悄漂移——那冻结配置就失去意义了。这个 launcher 让 YAML 成为唯一
事实来源，并且 fail-closed：

  * flag 名用 AST 从 trainer 源码里抽出来逐个核对：拼错立刻报错，而不是静默训错东西；
  * trainer 的 required flag 缺一个就报错；
  * 声明 frozen_formal_arm: true 的配置额外强制：
      - 必须 --verify-data-manifest，且两个 expect-*-manifest-sha 非空；
      - 四个 λ 必须全为 0；
      - stop-after-step / max-steps 必须为 0（正式臂跑满预注册 schedule）；
      - 禁止出现 allow-unverified-parent / allow-nonzero-lambdas / allow-existing-out。
  * --set 的覆盖值会并入后再跑同一套校验，所以拿正式配置 --set lambda-z=0.1 会被拦住，
    不需要额外的"我知道我在干什么"开关。

刻意不 import trainer 模块：避免任何 import 期副作用，也不依赖它的内部函数名。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shlex
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TS = HERE.parent                                  # terrastate/
TRAINER = HERE / "train_terrastate_candidate_c.py"

FORBIDDEN_IN_FORMAL = ("allow-unverified-parent", "allow-nonzero-lambdas",
                       "allow-existing-out")
LAMBDA_FLAGS = ("lambda-z", "lambda-y", "lambda-pair", "lambda-nc")
MUST_BE_ZERO_IN_FORMAL = ("stop-after-step", "max-steps")

# 由 launcher 从命令行注入，不冻结在 YAML 里（每个 run 都不一样）。
INJECTED = ("output-dir", "resume")


def trainer_options(src: Path) -> dict:
    """AST 抽取 trainer 的全部 --flag -> {store_true, required}。

    用 AST 而不是 grep：help 文本里出现 "--xxx" 不该被误当成真 flag。
    """
    tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        flags = [a.value for a in node.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)
                 and a.value.startswith("--")]
        if not flags:
            continue
        kw = {k.arg: k.value for k in node.keywords}

        def _is(key, want):
            v = kw.get(key)
            return isinstance(v, ast.Constant) and v.value == want

        # 默认值只在能静态求值时记录（Constant / 一元负号常量）。像
        # default=PARENT_ALIAS 这种 Name 记为 None，逼调用方显式指定，
        # 而不是让冻结配置去猜一个可能已经改掉的模块级常量。
        dflt, dflt_known = None, False
        dnode = kw.get("default")
        if isinstance(dnode, ast.Constant):
            dflt, dflt_known = dnode.value, True
        elif (isinstance(dnode, ast.UnaryOp) and isinstance(dnode.op, ast.USub)
              and isinstance(dnode.operand, ast.Constant)):
            dflt, dflt_known = -dnode.operand.value, True

        for f in flags:
            out[f[2:]] = {"store_true": _is("action", "store_true"),
                          "required": _is("required", True),
                          "default": dflt, "default_known": dflt_known}
    if not out:
        raise SystemExit(f"没能从 {src} 抽到任何 flag —— trainer 结构可能变了，停止")
    return out


def as_cli(val) -> str:
    """YAML 标量 -> 命令行字符串。repr 保证 float 可往返（3e-05 不变成长尾小数）。"""
    return repr(val) if isinstance(val, float) else str(val)


def validate(cfg: dict, opts: dict) -> list:
    """一次收集全部错误再报，避免"改一个跑一次"的来回。返回错误列表。"""
    errs: list[str] = []
    flags = cfg.get("flags")
    if not isinstance(flags, dict):
        return ["flags: 缺失或不是 mapping"]

    for k, v in sorted(flags.items()):
        if k not in opts:
            errs.append(f"--{k}: trainer 没有这个 flag（拼错或 trainer 已改）")
            continue
        if k in INJECTED:
            errs.append(f"--{k}: 由 launcher 注入，不能写在 YAML 里")
        # None 对任何 flag 都没有意义：as_cli(None) 会把字面量 "None" 传给 trainer，
        # 于是 --expect-train-manifest-sha None 变成一个"非空但永远对不上"的指纹。
        if v is None:
            errs.append(f"--{k}: 值为 null；要留空请写空字符串，不要用 null")
        if opts[k]["store_true"] and not isinstance(v, bool):
            errs.append(f"--{k}: 是开关，值必须是 true/false，实际 {v!r}")
        if not opts[k]["store_true"] and isinstance(v, bool):
            errs.append(f"--{k}: 不是开关，不能给 true/false")

    for k, meta in sorted(opts.items()):
        if meta["required"] and k not in flags and k not in INJECTED:
            errs.append(f"--{k}: trainer 要求必填，但配置里没有")

    # arm 与 factual_path 必须自洽：C1=recursive-only，C0R=direct 对照。
    # 写错这一对，两个臂会变成同一条路径，整个对照实验静默失效。
    pair = (flags.get("arm"), flags.get("factual-path"))
    if pair not in (("C1", "recursive"), ("C0R", "direct")):
        errs.append(f"arm/factual-path 组合非法: {pair}；只允许 "
                    "('C1','recursive') 或 ('C0R','direct')")

    # 锁定门 split 绝不能进训练期观测。trainer 自己在 L332 也会拒，但那时 8 张卡
    # 已经起来了；在这里拦住等于把"污染锁定门"的代价从一次 run 降到一次 exit 3。
    sel = str(flags.get("val-split-selector", ""))
    if "val_locked" in sel:
        errs.append(f"--val-split-selector={sel!r}: val_locked 是最终锁定门，"
                    "训练期不得作为观测 split")

    # ---- 跨工件核对：指向别的工件"内部"的字符串，必须真的去那个工件里解析一次 ----
    # smoke attempt 2 的死因就在这里：--val-split-selector 曾是 trainer argparse 的
    # 默认值 "splits.val_dev.ids"，而冻结 manifest 没有 splits 顶层键。逐 flag 校验
    # 全绿（它是个非空字符串、类型也对），但它指向的东西不存在。8 张卡起来之后才炸。
    # 逐 flag 合法 ≠ 工件之间自洽。这一段专门查后者。
    for key, must in (("val-split-manifest", True), ("q4-partition-manifest", False)):
        p = str(flags.get(key, "") or "").strip()
        if not p:
            if must:
                errs.append(f"--{key}: 不得为空")
            continue
        if not Path(p).is_file():
            errs.append(f"--{key}={p}: 文件不存在")
    for key in ("train-dir", "val-dir"):
        d = str(flags.get(key, "") or "").strip()
        if not d or not Path(d).is_dir():
            errs.append(f"--{key}={d!r}: 目录不存在")

    man = str(flags.get("val-split-manifest", "") or "").strip()
    if sel and man and Path(man).is_file():
        try:
            # 用 trainer 自己的 load_val_split：冻结/启动期的解析必须和训练期是同一份
            # 代码，否则"launcher 能解析"证明不了"trainer 能解析"。
            # 顺带白赚一件事：这行 import 成功就证明 trainer 模块本身可导入，
            # 同样是在 8 卡分配之前查出来，而不是之后。
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from train.train_terrastate_candidate_c import load_val_split
            ids, _ = load_val_split(man, sel)
            n = len(ids)
            if n != len(set(ids)):
                errs.append(f"--val-split-selector={sel}: 解析出的 ID 列表有重复")
            if n < 2:
                errs.append(f"--val-split-selector={sel}: 只解析出 {n} 个 ID")
        except KeyError as exc:
            errs.append(f"--val-split-selector={sel}: 在 {Path(man).name} 里解析不到"
                        f"（{exc}）。逐 flag 校验发现不了这种错，必须跨工件解析。")
        except (OSError, ValueError, ImportError) as exc:
            errs.append(f"--val-split-selector={sel}: 解析失败 {type(exc).__name__}: {exc}")

    # λ_pair 对**任何**配置都必须为 0（不只是正式臂）：trainer L280 无条件拒绝，
    # 因为 L_pair 需要 paired simulator truth，而本轮 simulator 情景库不存在。
    # 这条镜像 trainer 的闸门，好处是 dry-run 就能发现，而不是 8 卡起来后才炸。
    try:
        if float(flags.get("lambda-pair", 0.0)) != 0.0:
            errs.append(f"--lambda-pair={flags.get('lambda-pair')!r}: 必须为 0 —— "
                        "L_pair 需要 paired simulator truth，本轮 simulator 情景库不存在"
                        "（trainer 无条件拒绝，--allow-nonzero-lambdas 也放不开）")
    except (TypeError, ValueError):
        errs.append(f"--lambda-pair={flags.get('lambda-pair')!r}: 不是数值")

    if cfg.get("frozen_formal_arm") is True:
        for k in FORBIDDEN_IN_FORMAL:
            if flags.get(k):
                errs.append(f"--{k}: 正式臂禁止使用")
        for k in LAMBDA_FLAGS:
            if float(flags.get(k, 0.0)) != 0.0:
                errs.append(f"--{k}: 正式臂必须为 0，实际 {flags.get(k)!r}")
        for k in MUST_BE_ZERO_IN_FORMAL:
            if int(flags.get(k, 0)) != 0:
                errs.append(f"--{k}: 正式臂必须为 0（跑满预注册 schedule）")
        if not flags.get("verify-data-manifest"):
            errs.append("--verify-data-manifest: 正式 run 必须开启")
        # 不止"非空"：必须是 64 位小写十六进制。只查非空的话，一个截断或写错的
        # 指纹能过 launcher，然后在 8 张卡都起来之后才在 trainer 里炸掉。
        for k in ("expect-train-manifest-sha", "expect-val-manifest-sha"):
            v = str(flags.get(k, "") or "").strip()
            if not v:
                errs.append(f"--{k}: 正式 run 必须非空")
            elif len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
                errs.append(f"--{k}: 必须是 64 位小写 hex sha256，实际 {v!r}")

    # ---- 派生配置的"父一致性"：核实它对自己出身的声称，而不是信它的标签 ----
    # 背景：pilot 必须 frozen_formal_arm: false（否则 stop-after-step=128 会被上面那段拒），
    # 但它又必须**严格使用正式 C1 的参数**。这两件事在旧闸门下无法同时成立——实测拿
    # pilot 配置 --set per-gpu-batch=4 / branch-lr=1e-4 / lambda-z=0.1 / seed=7 …
    # 16 个负例里有 11 个畅通无阻，因为"非正式配置"本来就允许改这些。
    #
    # 修法不是给 pilot 再加一堆硬编码白名单（那会随 C1 漂移），而是：配置若声明
    # `derived_from`，就必须能被**重新推导**出来 —— 去父配置那里逐 flag 比对，
    # 只有 changed_flags 里显式声明的键允许不同，且必须恰好等于声明的目标值。
    # 于是"我是 C1 加恰好一处改动"从一句注释变成一条可执行断言。
    # 同一条跨工件教训：指向别的工件的声称，必须真的去那个工件核实一次。
    df = cfg.get("derived_from")
    if isinstance(df, dict):
        ppath = str(df.get("config", "") or "").strip()
        if not ppath:
            errs.append("derived_from 缺 config：无法核实派生声称")
        elif not Path(ppath).is_file():
            errs.append(f"derived_from.config={ppath}: 父配置文件不存在")
        else:
            pbytes = Path(ppath).read_bytes()
            plive = __import__("hashlib").sha256(pbytes).hexdigest()
            pdecl = str(df.get("sha256", "") or "").strip()
            if pdecl and pdecl != plive:
                # 父配置在派生之后被改过 —— 此时"继承自 C1"已经不成立了。
                errs.append(f"derived_from.sha256 与父配置现场不符：声称 {pdecl[:16]}… "
                            f"实际 {plive[:16]}…；父配置已变，派生关系失效，必须重新派生")
            pcfg = yaml.safe_load(pbytes.decode("utf-8")) or {}
            pflags = pcfg.get("flags") or {}
            changed = df.get("changed_flags") or {}
            if not isinstance(changed, dict):
                errs.append("derived_from.changed_flags 必须是 mapping")
                changed = {}
            for k in sorted(set(pflags) | set(flags)):
                if k in INJECTED:
                    continue
                pv, cv = pflags.get(k, "<absent>"), flags.get(k, "<absent>")
                if pv == cv:
                    continue
                if k not in changed:
                    errs.append(
                        f"--{k}: 派生配置擅自偏离父配置（{pv!r} -> {cv!r}），"
                        f"而 derived_from.changed_flags 没有声明这一项。"
                        f"若确实需要改动 batch size / 学习率 / 损失权重 / 训练步数，"
                        f"必须停下汇报并由用户决定，不得自行调整后继续")
                else:
                    want = changed[k].get("to") if isinstance(changed[k], dict) else changed[k]
                    if cv != want:
                        errs.append(
                            f"--{k}: 已声明为可改动，但当前值 {cv!r} 不等于声明的目标值 "
                            f"{want!r}。声明允许的是一个具体值，不是『这个 flag 随便改』")
    return errs


def build_argv(cfg: dict, opts: dict, output_dir: str, resume: str) -> list:
    """按 flag 名排序生成 argv：同一份配置总是产生逐字节相同的命令，便于登记与复现。"""
    flags = dict(cfg["flags"])
    flags["output-dir"] = output_dir
    if resume:
        flags["resume"] = resume
    argv: list[str] = []
    for k in sorted(flags):
        v = flags[k]
        if opts[k]["store_true"]:
            if v:                                  # False 就是"不传"，不能传 --flag false
                argv.append(f"--{k}")
        else:
            argv += [f"--{k}", as_cli(v)]
    return argv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Candidate C 冻结配置 -> torchrun 启动")
    ap.add_argument("--config", required=True, help="冻结的 YAML 配置")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--resume", default="")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="覆盖 flags 里的键；覆盖后仍会重跑全部校验")
    ap.add_argument("--nproc", type=int, default=0, help="默认取配置的 world_size")
    ap.add_argument("--gpus", default="", help="设 CUDA_VISIBLE_DEVICES；留空则不改")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令，不启动")
    ap.add_argument("--emit-json", default="", help="把解析结果写到该 JSON 路径")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        print(f"配置不是 mapping: {a.config}", file=sys.stderr)
        return 2

    overrides = {}
    for item in a.set:
        if "=" not in item:
            print(f"--set 需要 KEY=VALUE，实际 {item!r}", file=sys.stderr)
            return 2
        k, _, raw = item.partition("=")
        # yaml.safe_load("") 返回 None，而 str(None) == "None" 是真值——"--set k="
        # 这种清空动作会因此绕过"必须非空"校验。空串就当空串，交给下面的规则去拒。
        overrides[k.strip()] = "" if raw.strip() == "" else yaml.safe_load(raw)
    cfg.setdefault("flags", {}).update(overrides)

    opts = trainer_options(TRAINER)
    errs = validate(cfg, opts)
    if errs:
        print(f"配置校验失败（{len(errs)} 项），未启动任何进程：", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 3

    nproc = a.nproc or int(cfg.get("world_size", 8))
    train_argv = build_argv(cfg, opts, a.output_dir, a.resume)
    cmd = [sys.executable, "-m", "torch.distributed.run",
           "--standalone", f"--nproc_per_node={nproc}",
           str(TRAINER)] + train_argv

    env = dict(os.environ)
    if a.gpus:
        env["CUDA_VISIBLE_DEVICES"] = a.gpus

    info = {"config": str(Path(a.config).resolve()),
            "config_name": cfg.get("name"),
            "arm": cfg["flags"].get("arm"),
            "frozen_formal_arm": bool(cfg.get("frozen_formal_arm")),
            "overrides": overrides,
            "nproc": nproc,
            "output_dir": a.output_dir,
            "resume": a.resume,
            "cuda_visible_devices": env.get("CUDA_VISIBLE_DEVICES", "<unset>"),
            "cmd": cmd,
            "cmd_shell": " ".join(shlex.quote(c) for c in cmd),
            "cwd": str(TS)}
    if a.emit_json:
        Path(a.emit_json).write_text(
            json.dumps(info, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
    print(info["cmd_shell"])
    if a.dry_run:
        return 0
    # execvpe 替换自身：不多留一层 shell，信号（含协作停止）直达 torchrun。
    os.chdir(TS)
    os.execvpe(cmd[0], cmd, env)
    return 0                                        # 不会到达


if __name__ == "__main__":
    sys.exit(main())
