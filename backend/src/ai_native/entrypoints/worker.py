"""Worker 进程入口（占位，Day 1 填充）。

约束（DELIVERY-BL / D10-08）：Worker 只做 Run 领取、租约与 fencing、MAF 运行宿主、
资源/预算控制、恢复协调与事件投影；Executor 激活、Edge 路由、条件、并行汇合、
HITL 等待、Checkpoint 推进全部归 MAF —— 严禁在本进程写第二套 DAG 推进逻辑。
"""