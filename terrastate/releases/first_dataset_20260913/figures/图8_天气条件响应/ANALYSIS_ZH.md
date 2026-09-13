# 图8阅读与结果分析

## 怎么看

总体图先看A的两个效应量及区间是否位于0右侧，再看B中同一颜色的实线与虚线差异。W02详图从上到下依次读取空间预测、逐像素误差/替换差值、全时距输出轨迹和事实误差。

## 横纵轴、图例与色带

总体A横轴是loss benefit（MSE，正值表示actual天气相对替换天气误差更低），纵轴是actual vs donor与actual vs mean。总体B横轴是1–20个五日target step，纵轴是标准化天气z值；蓝、橙、绿分别为rain、mean temperature、shortwave radiation，实线为actual、虚线为donor。单一图例第一行为rain、actual、donor，第二行为mean temperature、shortwave radiation。详图第一行色带是NDVI 0–1；第二行左侧色带是绝对误差0–0.4；中间共享色带是带符号差值−0.4至0.4，蓝负红正；三条色带均与其负责的图组水平对齐。底部横轴仍是target step，左纵轴为spatial-mean NDVI，右纵轴为相对观测truth的RMSE。

## 当前效果与结论边界

84对样本中，actual相对donor的MSE收益为0.0021，95%区间[0.0008,0.0034]；actual相对mean的收益为0.0101，[0.0068,0.0138]，两者均位于0以上。W02中donor天气与actual天气存在明显轨迹差异，后期donor事实误差上升更强；mean通常介于actual与donor之间。donor与mean没有真实反事实GT，因此差值图表示模型响应，不是反事实预测准确率。
