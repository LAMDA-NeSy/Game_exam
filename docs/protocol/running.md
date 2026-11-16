# 运行游戏

入口、认证、结果目录和测试命令见 [根 README](../../README.md)。固定 Harbor 0.23.0，使用原生 agents；不提供自建模型 gateway 或直接 RL/LLM 入口。

## 镜像与平台

`prepare_games.py` 从 `FILES.json` 组装确定性的文件镜像并加载本地 Docker。移动字节一致的连接源码到 shared/connection 不改变连接镜像摘要。游戏任务的引擎镜像按 Dockerfile 安装冻结依赖。

推荐 Docker containerd image store，保证本地加载的 OCI 镜像可以按摘要被 COPY --from 解析。classic overlay2 store 可能仍向注册表请求相同摘要，此时需要配置支持的 image store，或由维护者发布完全相同内容的镜像；不能把 digest 改成任意浮动 tag 绕过。

`ghcr.io/mll-lab-nu/efe:*` 是继承的固定引用。游戏文件镜像可按源码本地构建，不表示已上传组织镜像仓库。monitor 是独立基础镜像依赖，首次运行仍需能取得其固定引用。Linux/AMD64、Linux/ARM64 的原生包可用性并不总相同；本地测试结果与 GitHub 的 Linux runner 结果应分别记录。

TextWorld 的冻结游戏经原生 Jericho 执行；不调用异构 wheel 中的游戏生成程序。MiniHack 使用固定 NLE/MiniHack 和模拟器日历设置，详情见游戏 README。

## 时间、网络与资源

Harbor 的 agent 超时包括模型调用和工具执行；服务预算不延长外层截止。标准模式由动作推进。Crafter realtime 首次请求开始服务计时、首次计划开始游戏时钟，后台控制程序在工具调用结束后应持续运行。

网络开放或 allowlist 以具体 task.toml 为准。原生 agent 禁用的搜索/连接器与容器网络是不同层。API 凭据从本地环境提供，不应放入任务和版本控制。

monitor 的采样结果和 resource_enforced 字段决定哪些额外限制实际生效。该记录不替代 Docker 自身的 CPU/内存限制。正式比较需固定 budget、agent、模型、观测 profile 和重试政策。

## 收集与结果

Harbor 按 verifier.collect 的顺序结束或封存运行、收集可信记录，然后在独立 verifier 中评分。GameRecords 派生汇总检查实例与代码指纹、完整性、重复局和故障分类。不要删掉失败局再计算成功率。

保留整个 job 与 jobs/prepared 冻结副本；旧报告使用旧代码/版本解释。正常评测默认不重试；重跑必须说明原因并保留原始尝试。
