# Factorio Learning Environment

套件 `factorio` 提供 FLE v0.4.3 的 `iron_plate_throughput`。目标是在 60 个游戏秒内自动生产至少 16 块铁板。首次运行需要 Linux 容器、Docker Compose v2 和访问镜像仓库及 GitHub 的构建网络。构建使用固定提交中的官方 Dockerfile 和 Factorio 2.0.73。FLE 的 Python 依赖安装在镜像内。[上游任务定义](https://github.com/JackHopkins/factorio-learning-environment/blob/6439e18b7870770454cf91eb36b3d1e6412724f4/fle/eval/tasks/task_definitions/lab_play/throughput_tasks.py)

```bash
harbor run --game-suite factorio --list
harbor run --game-suite factorio -a oracle --job-name fle-probe -y
harbor run --game-suite factorio -c configs/harbor/codex-deepseek.json --job-name fle-iron -y
```

`oracle` 用两次原生动作检查环境，无须模型密钥。它在查询库存时写入本局的随机标记，再从 REPL 读回该标记。两步的铁板产量都应为零。正式运行使用所选 Harbor coding agent。它读取官方 API 说明、结构化观测和执行反馈，向原生 REPL 提交 Python 源码。策略和对话历史由 Harbor agent 管理，因此该模式与作者的 Inspect solver 分开报告。

## 隔离

每个 Harbor trial（包括重试）使用独立的 Compose 项目、Factorio 进程、REPL 和命名卷。游戏与记录服务均关闭网络。游戏的 RCON 只在引擎容器内可用，记录服务通过私有 Unix socket 调用上游 bridge。agent 以只读方式挂载公开控制 socket 所在目录。套件只声明 trial 专属卷。项目源码目录和宿主 Docker socket 均不在容器挂载清单内。模型凭据与 trial 日志由 Harbor 管理。

记录服务串行执行动作，并用步号和源码摘要识别重试。上游执行结果存放在记录服务自己的文件系统。Harbor 在 agent 结束后通过记录容器内部的独立 Unix socket 封存轨迹，再收集 `artifacts/evidence/episode.json` 供断网 verifier 评分。原生 REPL 和游戏 bridge 共享引擎容器，评分依赖上游 bridge 如实返回游戏状态。

Linux CI 同时启动两个 Harbor trial，并通过 Docker 运行时记录确认两个引擎的运行时间重叠。检查覆盖容器网络模式、卷标识与读写权限、独立评分容器，以及两局各自的 REPL 标记、封存记录和成绩。agent 的公开 socket 只提供查询和游戏动作。正式模型的联网权限取决于 Harbor agent 配置。

## 成绩

- `iron_plate_goal_reached` 来自原生 Gym 的 `terminated`，即上游 `ThroughputTask.verify` 的吞吐量判定。逐步的 `reward` 由 Gym 返回。
- `fle_inspect_score` 来自原版 `comprehensive_factorio_scorer`。verifier 将原生每步的 `production_score` 装入 Inspect 的轨迹对象，再调用上游评分器。该指标依据最终生产分数计算，可能与铁板达标值不同。[上游评分实现](https://github.com/JackHopkins/factorio-learning-environment/blob/6439e18b7870770454cf91eb36b3d1e6412724f4/fle/eval/inspect/integration/scorers.py)

单局最多提交 64 步，沿用原生任务预算。游戏初始化、执行或评分故障会使验证失败。固定的上游源码提交、协议和任务 ID 记录在 `iron_plate_throughput/task.toml` 中。镜像依赖层固定 `a2a-sdk==0.3.22` 和 `inspect-ai==0.3.139`，以保留 v0.4.3 评分器使用的类型接口。其他传递依赖由官方 Dockerfile 在构建时解析。
