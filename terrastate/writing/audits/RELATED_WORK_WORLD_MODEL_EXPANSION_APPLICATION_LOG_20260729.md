# TerraState Related Work 世界模型谱系扩充应用记录

日期：2026-07-29  
任务性质：两次独立审计后的受控应用  
最终状态：**READY_FOR_POST_APPLICATION_REGRESSION_AUDIT**

## 1. 输入门禁

写入前重新计算的 SHA-256 与作者指定值完全一致：

| 文件 | 指定 SHA-256 | 写入前实测 | 结果 |
|---|---|---|---|
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` | PASS |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` | PASS |

## 2. 实际修改

### 2.1 `paper/main.tex`

只修改了三个获批区块：

1. Section 2 替换为 `RELATED_WORK_WORLD_MODEL_EXPANSION_REVISED_PROPOSAL_20260729.md` 第 5 节的 409 词、四段英文候选；
2. `Limitations and Scope` 替换为原提案第 12.3 节的 91 词候选；
3. `Conclusion` 替换为返修提案第 9.2 节的 76 词候选。

逐段规范化空白后，Section 2 四段、Conclusion 和 Limitations 均与各自获批候选逐字一致。没有继续自由压缩，也没有修改 Abstract、Introduction、Method、Experiments、表格、caption、Figure 或 Q1–Q3 定义。

### 2.2 `paper/references.bib`

- 新增且仅新增指定的六个 key；
- 将 `ha2018worldmodels` 从 arXiv `@misc` 整体切换为正式 NeurIPS 2018 `@inproceedings`；
- 未新增 DreamerV3、TD-MPC2、Deep-OSG 或 group-action 正文引用；
- 原有未使用条目 `chen2023deeposg` 与 `wang2026groupactions` 保留，未进入正文。

### 2.3 中英文镜像

- `MANUSCRIPT.md`：同步最终英文 Section 2、Limitations 和 Conclusion；
- `MANUSCRIPT_ZH.md`：同步对应中文四段 Related Work、Limitations 和 Conclusion；
- `MANUSCRIPT_ZH_FULL.md`：同步相同中文内容，并把正文唯一引用数更新为 28。

三个镜像提取到的引用 key 集合均与 `paper/main.tex` 完全一致：28 个，缺失 0，额外 0。中文仅忠实翻译最终英文，没有增加解释性或更强主张。

## 3. 六篇新增文献的正式元数据

1. **`schrittwieser2020muzero`**  
   Julian Schrittwieser, Ioannis Antonoglou, Thomas Hubert, Karen Simonyan, Laurent Sifre, Simon Schmitt, Arthur Guez, Edward Lockhart, Demis Hassabis, Thore Graepel, Timothy Lillicrap, David Silver.  
   *Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model*. Nature 588:604–609, 2020. DOI: [10.1038/s41586-020-03051-4](https://doi.org/10.1038/s41586-020-03051-4).

2. **`micheli2023iris`**  
   Vincent Micheli, Eloi Alonso, François Fleuret.  
   *Transformers are Sample-Efficient World Models*. International Conference on Learning Representations, 2023. [OpenReview `vhFu1Acb0xb`](https://openreview.net/forum?id=vhFu1Acb0xb). ICLR/OpenReview 版本没有连续页码，因此未虚构 `pages` 字段。

3. **`bruce2024genie`**  
   Jake Bruce, Michael D. Dennis, Ashley Edwards, Jack Parker-Holder, Yuge Shi, Edward Hughes, Matthew Lai, Aditi Mavalankar, Richie Steigerwald, Chris Apps, Yusuf Aytar, Sarah Maria Elisabeth Bechtle, Feryal Behbahani, Stephanie C. Y. Chan, Nicolas Heess, Lucy Gonzalez, Simon Osindero, Sherjil Ozair, Scott Reed, Jingwei Zhang, Konrad Zolna, Jeff Clune, Nando De Freitas, Satinder Singh, Tim Rocktäschel.  
   *Genie: Generative Interactive Environments*. Proceedings of the 41st International Conference on Machine Learning, PMLR 235:4603–4623, 2024. [PMLR official record](https://proceedings.mlr.press/v235/bruce24a.html).  
   PMLR 正式记录为 25 位作者；第二次审计正文中的“26 位”是计数笔误，本次按 PMLR 完整顺序写入。

4. **`yang2025driveoccworld`**  
   Yu Yang, Jianbiao Mei, Yukai Ma, Siliang Du, Wenqing Chen, Yijie Qian, Yuxiang Feng, Yong Liu.  
   *Driving in the Occupancy World: Vision-Centric 4D Occupancy Forecasting and Planning via World Models for Autonomous Driving*. Proceedings of the AAAI Conference on Artificial Intelligence 39(9):9327–9335, 2025. DOI: [10.1609/aaai.v39i9.33010](https://doi.org/10.1609/aaai.v39i9.33010).

5. **`venkatraman2017predictivestate`**  
   Arun Venkatraman, Nicholas Rhinehart, Wen Sun, Lerrel Pinto, Martial Hebert, Byron Boots, Kris M. Kitani, J. Andrew Bagnell.  
   *Predictive-State Decoders: Encoding the Future into Recurrent Networks*. Advances in Neural Information Processing Systems 30:1172–1183, 2017. [NeurIPS official record](https://proceedings.neurips.cc/paper/2017/hash/61b4a64be663682e8cb037d9719ad8cd-Abstract.html).

6. **`vafa2024evaluating`**  
   Keyon Vafa, Justin Y. Chen, Ashesh Rambachan, Jon Kleinberg, Sendhil Mullainathan.  
   *Evaluating the World Model Implicit in a Generative Model*. Advances in Neural Information Processing Systems 37:26941–26975, 2024. DOI: [10.52202/079017-0846](https://doi.org/10.52202/079017-0846).

`ha2018worldmodels` 现为 David Ha 与 Jürgen Schmidhuber 的正式论文 *Recurrent World Models Facilitate Policy Evolution*, Advances in Neural Information Processing Systems 31:2455–2467, 2018，并指向 [NeurIPS 正式记录](https://proceedings.neurips.cc/paper/2018/hash/2de5d16682c3c35007e4e92982f1a2ba-Abstract.html)。条目不再包含 arXiv 题名、ID 或 `@misc` 身份。

## 4. 引用清点

使用：

```text
python .../cite-bib-check/scripts/citation_inventory.py \
  --bib paper/references.bib \
  --tex paper/main.tex \
  --output /tmp/terrastate-cite-inventory/inventory.json
```

结果：

| 项目 | 数量 |
|---|---:|
| citation commands | 24 |
| cited-key occurrences | 37 |
| unique cited keys | **28** |
| BibTeX entries | 30 |
| missing keys | **0** |
| duplicate keys | **0** |
| unused entries | 2 |
| unresolved inputs / unknown citation commands | 0 / 0 |

未使用条目仅为 `chen2023deeposg` 与 `wang2026groupactions`，与受控方案一致。

## 5. 编译与页面检查

编译命令：

```text
cd /mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/paper
PATH=/mnt/data/users/luzheng/workspace/iclr/czj/.tools/texlive-2026/bin/x86_64-linux:$PATH \
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

`latexmk` 实际执行 BibTeX 和三轮 `pdflatex`，返回状态为 0。

| 检查项 | 结果 |
|---|---|
| PDF 总页数 | **9** |
| 页面尺寸 | 612 × 792 pt（US Letter） |
| 正文结束位置 | 第 7 页，Conclusion 完整结束 |
| 第 8 页 | 仅 References |
| 第 9 页 | 仅 References 续页 |
| LaTeX errors | 0 |
| undefined citations/references | 0 |
| BibTeX warnings/errors | 0 |
| overfull hbox / vbox | **0 / 0** |
| underfull hbox / vbox | 7 / 1；仅记录，页面检查未见裁切或异常重叠 |
| 负 `\vspace` / `\vskip` | 0 |

实页渲染检查确认：第 7 页包含 Results 尾部、Table 1–3、完整 Limitations 和完整 Conclusion；第 8 页从 `References` 标题开始；第 9 页仅包含参考文献续项。未调整字体、页边距、行距、图像或表格字号。

## 6. 冻结区块回归

以下 `main.tex` 区块在修改前后 SHA-256 完全相同：

| 区块 | 修改前 | 修改后 |
|---|---|---|
| Abstract | `86d59f313f2c09925f357b9bff0924685cc75b48f46ffd3fcc6691ec269a53e0` | 同左 |
| Introduction | `09233d4eb27f2814f69dc1cb3df075a883aa22d1e4f0bb027c472d37c2d70e32` | 同左 |
| Method | `ab3faa77b35306692636b6f76478db05a21871dfc4cf781f1d50398dcbee4f4f` | 同左 |
| Experiments | `be0f5f75e6e7cf526b6bbbd9f4bca70b4d9a83b9b7eea90d5f307839a8dedd06` | 同左 |

因此公式、表格、caption、实验数字、Q1–Q3、40 epochs / 14,880 updates 均未改变。正文中 `Q4`、DreamerV3、TD-MPC2、Deep-OSG 和 group-action citation key 的出现数均为 0；没有恢复 composition 主张，也没有向 TerraState 赋予控制、规划、因果、反事实、完整物理状态、SOTA 或严格排名能力。

正式 Figure 文件的 SHA-256 在修改前后不变：

| Figure | SHA-256 |
|---|---|
| Figure 1 PNG | `14e32ab755b1c8edb8f35f0764e68041cdaf6c1c3797dcbe1d9ddaef4842c4a6` |
| Figure 2 PNG | `8fed0b7c4f2cb727d2e7726e72c0ffc2fb4c3f4f26db127e330c0a0e2fe80153` |
| Figure 3 PDF | `b9049a5a66990a7d026b2049aa4956c817ea3b6764ae5466d16d14197584d17e` |

## 7. 文件 SHA-256

| 文件 | 修改前 | 修改后 |
|---|---|---|
| `paper/main.tex` | `304db26cc894ba73641c8b2d09acd5fd3f36da1a9f54c6f7b7480b07be52a5d2` | `05a89a3f9329cd55af1bf98222db12ebf96eb5e20377948c81bd5b0a9a117ded` |
| `paper/references.bib` | `47ae88064b84fd1f830d9c5a14ad02f0e1b79dbae8014cffe700b398c8b876c3` | `4fd6cec24ab29d097ad4fa28fdd4f8479fe059ed05e5db57a3b4023a0210cf8a` |
| `paper/main.pdf` | `f9c3fce5e209b3506c0afa44e4c742b209ad21168f855419ae4e41c3aca2daed` | `6d85dcdcaa31e6b637a632ee5b491d85324b88a0860edf063c76904b87b870c0` |
| `MANUSCRIPT.md` | `07579ab6c8cc78ab93b114a141d94e70a85b7d70693c6124e4913f1e686a6094` | `d5e1d532536619cbae7e055542e55ae0176b090a4deb99583038feb1110ba22e` |
| `MANUSCRIPT_ZH.md` | `d3f16021b91bf30291201a58e9d83ca0070648927870c67f3f0335e7c11d5a56` | `1b8920dfe9f22e4332c5f60fb82af6ecc3988ad3aa358dc9f0529a0b4b2a8504` |
| `MANUSCRIPT_ZH_FULL.md` | `8e94bce246fc4d6411517e3afab4f3db06e06996c5f29402f901713df0982338` | `98084ad43570d3d8c48d5a6f2ef7fc5e877aeb575ff37f5a0469cd1c48df504f` |
| `paper/main.bbl` | 编译产物 | `c862d5bee9fce9397c9db71e2d320fb28daad5b9ca5e16604648915cd9b2f7d5` |

## 8. 最终判定

所有指定内容、引用、编译、页数和冻结区块门禁均通过。

# READY_FOR_POST_APPLICATION_REGRESSION_AUDIT
