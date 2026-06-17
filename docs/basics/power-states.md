# 电源状态

## 常见状态

| 状态 | 说明 | 分析重点 |
|---|---|---|
| Active | CPU、外设或业务处于活跃状态 | 业务负载、后台任务、日志 |
| Idle | CPU 空闲但系统未完全 suspend | idle residency、定时器、中断 |
| Suspend | 系统进入挂起流程 | suspend blocker、设备 suspend 回调 |
| Deep Sleep | 平台进入更深低功耗状态 | 唤醒源、外设电源、PMIC 状态 |

## 判断方向

- 如果无法进入 suspend，优先检查 wakelock、suspend blocker 和活跃服务。
- 如果能进入 suspend 但电流仍高，优先检查外设电源、GPIO、PMIC 和硬件漏电。
- 如果周期性退出 suspend，优先检查 wakeup source、alarm 和网络唤醒。
