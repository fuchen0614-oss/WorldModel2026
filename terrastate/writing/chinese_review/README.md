# TerraState 中文审阅 PDF

该目录生成一份便于作者检查叙事、公式、表格和证据强度的中文 PDF。

- 中文内容源：`../MANUSCRIPT_ZH_FULL.md`
- 英文事实源：`../paper/main.tex`
- 输出：`TerraState_AAAI27_中文完整审阅版.pdf`
- 编译引擎：项目本地 TeX Live 2026 + XeLaTeX + CTeX/Fandol
- 当前状态：2026-07-28 编译通过，共 14 页；包含 Figure 1--2、公式（1）--（9）、
  Table 1--3、局限性、结论、中文审阅导航和参考文献。

重新生成：

```bash
cd /mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/chinese_review
python3 build_zh_review.py
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
  latexmk -xelatex -interaction=nonstopmode -halt-on-error main_zh.tex
```

该 PDF 不是投稿文件，不使用 AAAI 样式，也不会修改英文权威稿。

质量核验：

- 无 LaTeX error、overfull box、undefined citation/reference 或缺字；
- 仅有 1 条不影响阅读的 `Underfull \hbox`；
- 27 个字体对象均包含嵌入字体程序，Type 3 字体为 0；
- 逐页预览位于 `review_pages/`。
