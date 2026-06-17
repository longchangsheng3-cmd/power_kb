# Kernel 待机优化

## 优化方向

- 减少不必要 wakelock。
- 修复 suspend blocker。
- 降低周期性定时器频率。
- 确保 driver suspend/resume 流程正确。
- 关闭待机不需要的 debug log。

## 检查重点

| 方向 | 检查项 |
|---|---|
| Wakelock | 是否长时间 active，是否高频触发 |
| Timer | 是否存在过密周期任务 |
| Interrupt | 是否存在中断风暴或错误 wakeup 配置 |
| Driver | suspend 回调是否失败，外设是否释放资源 |
| Debug | 日志、trace、UART 是否影响睡眠 |

## 验证方法

- 对比优化前后的 wakeup_sources。
- 对比 suspend_stats 成功率。
- 对比深睡占比和平均电流。
- 做关键功能回归，避免误关必要唤醒。
