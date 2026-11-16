# 游戏框架

公开仓库只包含游戏及它们的共用依赖。使用与完整说明见 [README](../README.md)。

## Harbor 原生启动与记录

`harbor run --game-suite <suite> --standard -c <agent-config>` 经过 `scripts/efe.py` 的任务筛选与 `prepare_games.py` 的预检/文件准备，随后交给原生 Harbor 0.23.0 执行。Agent、模型、工具权限和配置合并均沿用 Harbor。普通 `-p`、`-c` 源参数在不指定游戏筛选时原样传递。

Harbor 保存 config、lock、result、agent 和 verifier 记录。`game_harbor:GameRecords` 是可选的原生 job plugin，仅增加实际镜像来源和派生游戏报告。它不代理模型请求、不篡改原始结果，不把不同模式混成一个分数。历史报告按保存的代码指纹重算，不能使用新算法默默覆盖旧成绩。

## 数据流和信任边界

标准模式的数据流：

```text
instruction.md → Harbor 原生 coding agent → agent 写的程序
                                              ↓ game_client
                                          可信 sim 服务
                                              ↓ adapter
                                          原生游戏引擎
                                              ↓ 封存记录
                      Harbor 收集 → 隔离 verifier → reward.json
```

`runtime/server.py` 管理动作序号、去重、公共预算和可信封存；`benchmarks/<game>/adapter.py` 管理原生环境、观测、原生动作和原生结束。`grade.py` 检查可信 final 的结构和实例绑定，`metric_rules.py` 检查专属语义；这依赖容器隔离和收集顺序，不宣称任意轨迹都被逐步重放证明。

不要把指纹、原生内部状态或审计帧自动放进 agent 观测。允许看到什么由 instance 的 observation profile、adapter 和 instruction 共同定义。配置校验路径来自宿主可信注册表，不能来自 agent 的输入。

## 目录职责

- `game_first_exam/runtime/`：游戏公共协议、预算、错误类型、评分、录像和 reducer。
- `game_first_exam/runtime/modes/`：独立的 privileged 和 realtime 执行方式。
- `game_first_exam/benchmarks/`：五个原生环境的薄适配器、专属 schema、指标和依赖。
- `game_first_exam/tasks/`：自包含冻结任务；运行不依赖宿主源码路径。
- `shared/connection/`：从上游原样保留的就绪等待、地址选择和连接处理。
- `images/connection-files/`、`images/monitor/`：共用连接镜像与资源监控。
- `scripts/`：任务选择、规范化、确定性文件镜像、准备和结果分类/汇总。
- `ci_checks/`、`game_first_exam/tests/`：全套件预检、共享契约与原生等价性验证。

机器人任务、专属实现和镜像已移除。网站及其命令构建前端不在此仓库；保留上游版权与必要的历史标识。

## 扩展边界

新游戏先实现 Adapter 的构造、spec/observe/step、metrics/success、fingerprint/frame 和 close；只读方法不得改变状态或 RNG。`step` 返回增量 reward，原生 terminated/truncated 与公共预算原因分开。模型非法动作、原生失败、环境异常和基础设施异常应能在报告中分辨。

新增游戏一般只增加 adapter、专属 schema/metric_rules、冻结任务、files-only 镜像、套件和固定环境测试。新 reducer 需要独立标识和版本。不要为了可能的多 agent/实时需求扩展所有同步 step 接口；先实现并验证一个明确的执行模式。

标准任务说明参考 [模板](templates/game-standard/README.md)；模式差异见 [执行模式](game_execution_modes.md)。原生任务、种子、评分和观测限制以实际冻结文件为准。
