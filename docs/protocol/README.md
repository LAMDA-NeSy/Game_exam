# 游戏任务与可信评测约定

本仓库复用上游任务封装与 Harbor 隔离机制，原始来源见 [UPSTREAM](../../UPSTREAM.md)。这里记录游戏版本实际采用的边界，不是复制全部机器人协议。

## 1. 任务交付

每个冻结任务包含 instruction、task.toml、environment、tests、solution、README 和 DIGEST。公用文件通过确定性 files-only 镜像进入任务。solution 不进入 agent 镜像；游戏资产与实例由 sim/verifier 分别绑定。

## 2. 原生设置

引擎版本、seed、原生环境、资产、观测 profile、原生动作预算、公共预算和指标由冻结实例声明，校验未知即拒绝。新增任务不等于重新设计原生奖励。说明中必须区分额外的观测/执行包装与原生环境本身。

## 3. 执行模式

standard 通过可信 sim 操作 live episode；privileged 本地探索后提交受 verifier 重放的动作序列；realtime 的游戏时钟在首次有效计划后独立推进。当前支持范围见根 README，模式不存在时不能靠命令行开关创建。

## 4. 评分与参考程序

评分由独立 verifier 产生；oracle 是参考解而非模型成绩，partial 参考程序应声明覆盖范围。基准原生奖励、主分数、辅助成功目标分开保存。有效失败进入分母；缺失、重复、基础设施异常不能默默当作成功或忽略。

## 5. 任务说明

写明场景、目标、允许的观测、动作、客户端参数与返回、评分和时间。指纹、隐藏状态、参考路线不进入标准观测。API 返回和示例必须与当前客户端一致。模板位于 docs/templates/game-standard。

## 6. 资源

时间由 Harbor 截止，公共动作预算与原生截断分开；资源数字是容器上限。monitor 记录使用情况，其额外强制限制开关与是否缺失必须进入结果。不能仅凭配置存在就宣称限制已生效。

## Appendix H — 保留的可信边界

H.1 verifier 与 agent 隔离；H.2 参考解不向 agent 泄露；H.3 标准模式 sim 是可信侧；H.4 verifier 使用可信封存证据；H.5 区分基础设施异常与有效模型失败，当前预设不自动重跑；H.6 声明并实施容器网络与权限边界；H.7 比较模式时明确一致的任务条件与预算；H.8 通过 DIGEST 绑定冻结任务内容。

可执行检查见 `ci_checks/check-games.py`，实际实现优先于泛化的文字。完整命令、结果位置和扩展流程见 [根 README](../../README.md)。
