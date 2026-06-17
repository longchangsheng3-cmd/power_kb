# Kernel Wakelock 检查清单

## 适用场景

待机电流偏高，系统无法进入深度睡眠，或 suspend 次数明显偏少。

## 需要收集的信息

- `/sys/kernel/debug/wakeup_sources`
- `/sys/power/suspend_stats`
- kernel log
- 电流曲线
- 正常样机对比数据

## 排查步骤

1. 查看 `active_count`、`event_count`、`wakeup_count` 和 `total_time`。
2. 找出长时间 active 或高频触发的 wakeup source。
3. 对比正常样机是否存在同名 source 或次数差异。
4. 结合 kernel log 定位对应 driver 或 subsystem。
5. 检查是否有 suspend 回调失败或重复唤醒。

## 常见原因

| 现象 | 可能原因 | 处理建议 |
|---|---|---|
| wlan 相关 wakelock 高频活跃 | 网络包唤醒或 Wi-Fi power save 未生效 | 检查 Wi-Fi 省电配置和网络环境 |
| alarmtimer 高频唤醒 | 应用或系统定时任务过密 | 检查 alarm dump 和后台策略 |
| sensor wakelock 长时间 active | 传感器未正确关闭 | 检查 sensor HAL 和业务订阅 |
| suspend_stats 失败计数增加 | 设备 suspend 回调失败 | 根据失败设备定位驱动 |
