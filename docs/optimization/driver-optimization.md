# Driver 待机优化

## 优化方向

- 待机前释放不必要资源。
- 正确关闭 regulator、clock 和 IRQ。
- 配置合理的 wakeup source。
- 避免 suspend/resume 中异常重试。
- 确保 GPIO 状态不会造成漏电。

## 常见问题

| 问题 | 影响 | 建议 |
|---|---|---|
| regulator 未关闭 | deep sleep 电流偏高 | 检查引用计数和 suspend 流程 |
| clock 未关闭 | 平台无法进入更深低功耗 | 检查 runtime PM 和 suspend 回调 |
| IRQ 配置错误 | 频繁唤醒 | 检查触发类型和 wakeup 配置 |
| GPIO 默认态错误 | 外设或板级漏电 | 对比硬件设计和低功耗状态表 |

## 验证方法

- 单独关闭可疑 driver 做隔离。
- 对比寄存器和电源轨状态。
- 检查 suspend/resume 日志。
- 做功能回归和长时间待机复测。
