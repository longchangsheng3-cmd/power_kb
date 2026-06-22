# 案例：待机耗电高 - USB wake lock 长时间活跃

## 基本信息

- 平台：待补充
- 软件版本：待补充
- 硬件版本：待补充
- 测试场景：待补充
- 期望电流：待补充
- 实测电流：待补充
- 确认日期：2026-06-18
- 复核人：longchangsheng

## 问题现象

待机耗电高，kernel log 显示 USB wake lock 长时间 active

## 输入材料

- 日志：inputs\logs\kernel_log_12__2026_0617_174148
- 结构化分析结论：人工确认后入库

## 分析过程

最可疑方向：11201000.usb0 长时间持有 wake lock。该结论基于 V0.3.1 日志聚合结果生成，需要人工结合测试场景确认。

## 可能原因排序

| 优先级 | 可能原因 | 关键依据 | 下一步验证 |
|---|---|---|---|
| P1 | 11201000.usb0 长时间持有 wake lock | Top Active Wake Locks 显示样本数 28，最长 active_since 540.1s，最大 active_count 8。 | 检查该 wake lock 对应驱动/子系统是否符合待机场景，确认是否应释放或降频。 |
| P2 | 11201000.usb0 重复出现在 Pending Wakeup Sources | Top Pending Wakeup Sources 显示出现 52 次。 | 结合 wakeup source 统计和驱动日志确认该源是否反复阻塞 suspend 或唤醒系统。 |
| P2 | USB/Type-C/Charging 状态可能影响待机功耗 | 分类统计 usb=20074，charger=985。 | 确认测试是否连接 USB/充电器；若是纯待机测试，建议拔线复测并对比 wake lock。 |
| P3 | 网络日志命中较多但需结合具体 wake lock 判断 | 分类统计 network=311。 | 检查是否存在 wlan/modem 相关 active wake lock；没有时不要直接归因为网络。 |

## 根因

待人工补充最终根因。如果已确认，可将 P1 结论整理为根因。

## 优化方案

待人工补充实际修改、配置调整或规避方案。

## 验证结果

1. 纯电池、断开 USB/Type-C 后复测待机电流。
2. 若异常消失，进一步定位 USB controller、Type-C 检测、充电策略或调试连接。
3. 若异常仍存在，继续分析第二优先级 wake lock/wakeup source。

## 人工复核记录

- 确认测试场景是否允许 USB/充电器连接。
- 对比拔掉 USB/充电器后的待机电流和 wake lock。
- 补充 `/sys/kernel/debug/wakeup_sources` 和 `/sys/power/suspend_stats`。
- 对比正常样机同一场景下的 Top wake locks 和 Pending Wakeup Sources。
- 确认日志时间段是否覆盖完整待机异常窗口。

## 关联知识

- docs/optimization/kernel-optimization.md
- docs/optimization/driver-optimization.md
- docs/cases/case-001-high-wakelock.md
- docs/checklist/kernel-wakelock-checklist.md
- docs/checklist/peripheral-checklist.md
