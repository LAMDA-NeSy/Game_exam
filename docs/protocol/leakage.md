# 观测与可信边界

标准模式不得向 agent 暴露参考程序、隐藏状态、内部指纹或 verifier 文件。sim 与 verifier 持有独立的冻结实例。录像与审计状态不是额外的模型输入；所有实际允许的输入由 observation profile 明确声明。

privileged 是不同实验条件，不与 standard 成绩混合。用户提供的配置不能选择任意 schema 代码，注册路径来自宿主可信配置。游戏自身的文本是观测数据，不是宿主执行权限。
