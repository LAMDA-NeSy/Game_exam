# 游戏交互协议

标准模式实现见 `game_first_exam/runtime/server.py` 与 `game_client.py`；状态和方法契约见 `contracts.py`。当前标准 wire protocol 为 game-standard/2.2，额外模式位于 runtime/modes。

客户端提供 spec、observe、status、step；step 需要当前 expected_step，可使用 request_id 避免丢失响应后的重复执行。无效动作和旧步号不应推进环境。读取不得改变游戏状态或 RNG。

原生 step 返回增量奖励和原生 terminated/truncated；公共预算结束原因单独记录。终局后不能继续操作。可信 final 绑定冻结实例；grader 校验结构与游戏语义。

观测格式按游戏配置而异，不能统一假设都有图像、完整地图或相同动作名称。以任务 instruction 和 adapter.spec 为准。完整的执行、计时、privileged/realtime 说明见 [执行模式](../game_execution_modes.md)。
