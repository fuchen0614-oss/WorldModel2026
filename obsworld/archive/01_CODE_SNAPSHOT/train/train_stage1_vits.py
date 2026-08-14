"""
Stage 1 ViT-S/16 双模态 MAE 预训练入口

完全复用 train.train_stage1_dual 的训练逻辑，只新增一个功能：
    在配置里 `epoch_tag_steps` 指定的 step 节点，额外复制一份带 tag 后缀
    的 checkpoint，便于后续按 patch-epoch 数定位（e.g. _epoch100/_epoch150/_epoch200）。

用法（torchrun 8 卡）：
    torchrun --nproc_per_node=8 --master_port=29601 \
        -m train.train_stage1_vits \
        --config configs/train/stage1_vits_dual.yaml

设计说明：
- 这是 train_stage1_dual 的薄包装。原训练脚本不动。
- 通过 monkey-patch `save_checkpoint`，在原有 ckpt 写盘后额外 cp 一份带 tag 名。
  额外副本和原 ckpt 内容完全一致，只是文件名不同。
"""
import shutil
import sys
from pathlib import Path

# 加入项目根目录路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from train import train_stage1_dual
from train.fsdp_utils import is_main_process, barrier


# 保留原 save_checkpoint 的引用
_original_save_checkpoint = train_stage1_dual.save_checkpoint


def save_checkpoint_with_tag(
    checkpoint_dir, global_step,
    model, encoder, decoder, optimizer, config
):
    """正常 save_checkpoint，然后按 config.epoch_tag_steps 复制带 tag 的副本。

    epoch_tag_steps 在 yaml 里的格式：
        epoch_tag_steps:
          - {step: 47500, tag: epoch100}
          - {step: 71500, tag: epoch150}
          - {step: 95000, tag: epoch200}
    """
    # 调用原始保存逻辑
    _original_save_checkpoint(
        checkpoint_dir, global_step, model, encoder, decoder, optimizer, config
    )

    # 只在 rank 0 做文件复制
    if not is_main_process():
        barrier()
        return

    # 检查当前 step 是否是 tag 节点
    tag_entries = config.get('epoch_tag_steps', [])
    matched = [e for e in tag_entries if int(e.get('step', -1)) == int(global_step)]
    if not matched:
        barrier()
        return

    import os
    src = os.path.join(checkpoint_dir, f"checkpoint_step_{global_step}.pt")
    if not os.path.exists(src):
        print(f"[警告] epoch tag 想复制的 ckpt 不存在: {src}")
        barrier()
        return

    for e in matched:
        tag = e.get('tag')
        dst = os.path.join(
            checkpoint_dir,
            f"checkpoint_{tag}_step_{global_step}.pt"
        )
        shutil.copy2(src, dst)
        print(f"[epoch-tag] 已复制: {src} -> {dst}")

    barrier()


# 替换原模块的 save_checkpoint，使训练循环内部调用走我们的版本
train_stage1_dual.save_checkpoint = save_checkpoint_with_tag


if __name__ == "__main__":
    # 直接复用原 main()
    train_stage1_dual.main()
