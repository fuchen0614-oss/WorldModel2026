# TerraState AAAI-27 正文提交指南

> 截止时间：2026-07-29 11:59 UTC（北京时间 2026-07-29 19:59）
>
> 投稿入口：https://openreview.net/group?id=AAAI.org%2F2027%2FConference

## 1. 首先打开已有投稿

1. 使用注册摘要时的同一个 OpenReview 账号登录。
2. 在 `Your Submissions` 中找到已有的 TerraState 投稿和 Paper ID。
3. 点击 `Revision`、`Edit` 或 `Submit Revision`。
4. 不要创建新的投稿；正文必须提交到此前已注册摘要的 Paper ID。

## 2. Track

复制或选择：

```text
Main Technical Track
```

## 3. Title

下面标题在文件中实际只有一行，可整行复制：

```text
TerraState: A Testable Predictive-State World Model for Weather-Driven Land-Surface Forecasting
```

## 4. Abstract

下面摘要在文件中实际只有一行。编辑器中看见的折行只是视觉自动换行，不会复制成换行：

```text
High-resolution satellite time series are a primary tool for monitoring vegetation, agriculture, and ecosystem response. Forecasting from these series is increasingly formulated as a weather-driven task: predicting future land-surface observations from cloud-obscured image histories and meteorological drivers. Yet such models are primarily evaluated by fixed-horizon pixel accuracy, which cannot establish whether an internal representation functions as a forecast-bearing, weather-responsive predictive state. An accurate forecaster may still ignore the weather forcing, collapse toward persistence, or expose a latent state that does not actually carry the forecast—failures that standard error metrics cannot detect. We introduce TerraState, a testable predictive-state world model. TerraState infers a spatial predictive state from cloud-masked histories. A shared transition advances this state under future weather, geography, and elapsed time, and a state readout converts the advanced state into an explicit contribution to the final forecast. Rather than treating architecture alone as evidence that a world state exists, TerraState makes its predictive-state claim falsifiable through state-contribution removal, a supporting identity-transition control, and matched interventions comparing actual future weather with matched-donor and normalized-mean weather. On GreenEarthNet under temporal distribution shift, TerraState retains useful forecasting skill; state removal degrades validation and OOD-t performance, and actual weather yields lower complete-window loss than both controls on a frozen heat–drought subset.
```

粘贴后只需检查：

- 是否出现单词中间的异常断词，例如 `predic- tive`；
- 是否出现重复空格；
- `heat–drought` 中间是短横线也不影响提交；
- 不要从 PDF 重新复制摘要。

## 5. Authors

以已有 OpenReview 投稿中的作者信息为基础，逐项确认：

- [ ] 作者全部齐全；
- [ ] 作者顺序正确；
- [ ] 每名作者关联的是正确 OpenReview Profile；
- [ ] 通讯邮箱正确；
- [ ] 所有作者均同意投稿。

截止后不能新增作者。

## 6. Topics / Keywords

推荐选择：

### Primary topic

```text
ML: World Models, Simulation & Environment Models
```

### Secondary topics

```text
CV: Remote Sensing / Geospatial AI
ML: Time-Series & Data Streams
ML: Representation Learning
ML: Evaluation, Benchmarking, Datasets & Analysis
```

如果 OpenReview 限制次级关键词数量，按以上顺序保留前三项即可。

## 7. 必须上传的文件

### Main Paper / Paper PDF

```text
/mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/paper/main.pdf
```

当前核对信息：

- 9 页；
- 第 1–7 页正文；
- 第 8–9 页仅参考文献；
- AAAI-27 submission 模板；
- US Letter；
- 匿名；
- 无编译错误、引用错误或文字溢出；
- SHA-256：`5578ad0ceaa28bf6398f55443f7b67fd633a193622ac6e5631206f1445ce4242`。

### Reproducibility Checklist

```text
/mnt/data/users/luzheng/workspace/iclr/czj/TerraState_AAAI27/paper/ReproducibilityChecklist.pdf
```

必须上传到表单中专门的 `Reproducibility Checklist` 字段，不要与主论文合并。

## 8. 不需要随正文上传

- LaTeX 源码；
- `references.bib`；
- 单独图片；
- PPTX；
- 中文版 Markdown；
- 权重；
- 训练日志。

## 9. 投稿声明

按照真实情况确认：

- [ ] 投稿为匿名版本；
- [ ] 未同时投稿到其他存档型会议或期刊；
- [ ] 不存在违反规定的重复或高度重叠投稿；
- [ ] 所有作者均知情并同意；
- [ ] 作者、利益冲突和 OpenReview Profile 信息完整；
- [ ] 论文遵守 AAAI 的伦理及投稿政策。

## 10. 最终提交

1. 点击 `Save Revision`、`Submit Revision` 或页面对应的最终提交按钮。
2. 返回 Paper ID 页面。
3. 确认页面显示最新 Revision 时间，且早于截止时间。
4. 点击系统中上传后的 PDF，确认：
   - [ ] 首页标题为 TerraState；
   - [ ] 显示 `Anonymous submission`；
   - [ ] Figure 1 和 Figure 2 是最新图片；
   - [ ] PDF 共 9 页；
   - [ ] 最后两页只有参考文献。
5. 点击页面右上角 `Email`，给自己或所有作者发送投稿确认邮件。
6. 截图保存 Paper ID、投稿状态和提交时间。

## 11. 可选补充材料

补充材料截止时间为 2026-07-31 11:59 PM UTC-12（北京时间 2026-08-01 19:59）。

正文提交完成后可以选择上传：

- Supplementary Document PDF；
- Code and Data ZIP；
- Supplementary Media ZIP。

这些材料均为可选，不能耽误当前正文提交。补充材料中不要放匿名 GitHub、Hugging Face 或其他网页链接，应直接上传文件。

## 最短执行顺序

```text
打开已有 Paper ID
→ Revision/Edit
→ 更新标题和最终摘要
→ 核对作者
→ 选择 Topics
→ 上传 main.pdf
→ 上传 ReproducibilityChecklist.pdf
→ Submit Revision
→ 打开上传后的 PDF 检查
→ Email 投稿回执
```
