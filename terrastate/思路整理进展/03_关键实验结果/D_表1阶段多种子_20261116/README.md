# D正文表1：阶段多种子评价
授权：新增seed27/97同seed C1/C0R配对评价，复用seed42验收结果；不重跑标准四split。
范围：IID共同55–100天窗口；直接、50、25+25、15+35四条路径。每seed四卡按样本分片，共同有效2837例、每例80行。与seed42逐时刻掩码计数严格对账。
冻结身份：requirements.json列明四个SHA、seed、epoch及阶段/最终选模属性。绝不随在训best变化而自动换权重。本批为阶段预览，不称100epoch最终三种子。
优先节点：seed27→946，seed97→909；显存不足的下一周期分别转916/991。每GPU至少7000MiB可用才启动，不杀现有训练或保卡任务。
唯一执行器：工作区_dqueue_20261114/table1_queue.py。当前本地PID33236；即时状态followthrough_state.json；各seed启动及进度回执seed*_status.json、seed*_latest.json。SSH ConnectTimeout=300，外层1500秒。首轮立即执行；后续3小时有界跟进，最多4轮，业务错误停止留证。
远程controller持久执行四分片→完整性验收→原统计及地理bootstrap→OSS归档。本地接续取回结果，复用seed42，生成逐seedCSV、跨seed均值及样本SD，集中追加A51/A08。地理置信区间与种子SD分别保留。
OSS目标：/oss-chengjuntao/makerdata/chenzhisheng/WD_LA/SpanWorld_GreenEarthNet/table1_multiseed_interim_20261116/seed27或seed97。
启动程序不等于服务器已开跑；以远程launch/PID、first_sample_PASS、progress及真实exit为准。正文不修改。原稿同版式图片任务单独继续，不使用被撤销的自定义版式。
