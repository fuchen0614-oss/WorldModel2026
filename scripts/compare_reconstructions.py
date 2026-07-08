"""
把多个训练步数的重建可视化图纵向拼成一张对比图。

用法:
    python scripts/compare_reconstructions.py \
        --steps 1000 5000 9500 \
        --recon-dir logs/long_run/reconstructions \
        --output outputs/recon_compare.png
"""

import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


def main():
    parser = argparse.ArgumentParser(description="重建可视化对比图")
    parser.add_argument("--steps", type=int, nargs="+", default=[1000, 5000, 9500],
                        help="要对比的训练步数")
    parser.add_argument("--recon-dir", type=str,
                        default="logs/long_run/reconstructions",
                        help="重建图所在目录")
    parser.add_argument("--output", type=str,
                        default="outputs/recon_compare.png",
                        help="输出对比图路径")
    args = parser.parse_args()

    # 收集存在的图
    items = []
    for step in args.steps:
        path = os.path.join(args.recon_dir, f"recon_step_{step}.png")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            items.append((step, path))
        else:
            print(f"[跳过] step {step} 的图不存在或为空: {path}")

    if not items:
        print("没有可用的重建图，退出。")
        return

    # 纵向排列：每行一个 step
    n = len(items)
    fig, axes = plt.subplots(n, 1, figsize=(10, 4 * n))
    if n == 1:
        axes = [axes]

    for ax, (step, path) in zip(axes, items):
        img = mpimg.imread(path)
        ax.imshow(img)
        ax.axis("off")
        ax.set_title(f"训练 {step} 步", fontsize=14, fontweight="bold")

    fig.suptitle("MAE 重建质量随训练步数的变化（每张图三列：原图 | 遮掩输入 | 重建）",
                 fontsize=13, y=0.998)
    fig.tight_layout()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=90, bbox_inches="tight")
    plt.close(fig)
    print(f"对比图已保存: {args.output}")


if __name__ == "__main__":
    main()
