# 日志辅助分析清单

## 适用场景

用户已经提供 kernel log、系统日志、模块日志或功耗测试日志，需要先从日志中提取待机功耗相关线索。

## 重点关键词

| 分类 | 关键词示例 | 分析方向 |
|---|---|---|
| wakelock | wakelock、wake_lock、wake lock | 是否有长时间阻止睡眠的锁 |
| wakeup | wakeup、wakeup_source | 是否有频繁唤醒源 |
| suspend | suspend、deep sleep、s2idle | 是否进入目标低功耗状态 |
| resume | resume、resumed | 是否频繁退出低功耗 |
| alarm | alarm、alarmtimer、rtc | 是否存在周期性定时唤醒 |
| network | wlan、wifi、modem、rx、tx | 是否有网络包或无线模块唤醒 |
| power-rail | pmic、regulator、ldo、buck | 是否有电源轨未关闭 |
| clock-irq | clock、clk、irq、interrupt | 是否有时钟未关或中断风暴 |
| error | error、fail、timeout、blocker | 是否存在失败、超时或 blocker |

## 推荐流程

1. 使用 `scripts/analyze_log.py` 提取关键日志行。
2. 根据分类统计判断优先分析方向。
3. 使用问题描述执行 RAG 检索，召回相关 checklist 和案例。
4. 使用 `scripts/build_analysis_context.py` 生成 Claude Code 分析上下文。
5. 使用 `scripts/create_analysis_report.py` 生成报告草稿。
6. 人工确认后补充根因、优化方案和验证结果。

## 注意事项

- 关键词命中不是根因，只是证据线索。
- 日志必须结合测试场景、电流曲线和正常样机对比判断。
- 需要保留原始日志位置，便于回溯上下文。
