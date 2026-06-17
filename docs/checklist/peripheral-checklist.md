# 外设功耗检查清单

## 适用场景

系统能够进入 suspend 或 deep sleep，但待机电流仍然偏高，或不同硬件样机功耗差异明显。

## 检查对象

- GPIO 上下拉和默认电平。
- Sensor、Camera、Audio、Display、Touch。
- Wi-Fi、BT、GNSS、Modem。
- PMIC regulator 和 clock。
- Debug UART、USB、JTAG。

## 排查步骤

1. 确认外设在待机场景下是否应关闭或进入低功耗。
2. 检查 regulator 是否关闭到预期状态。
3. 检查 clock 是否关闭或降频。
4. 检查 GPIO 是否存在异常拉电流。
5. 对比正常样机的寄存器、GPIO 和电源轨状态。
6. 逐个关闭可疑外设做隔离验证。

## 常见原因

| 现象 | 可能原因 | 处理建议 |
|---|---|---|
| deep sleep 电流仍高 | 某路电源未关闭 | 检查 regulator 配置和引用计数 |
| 单板差异大 | GPIO 或外设漏电 | 做硬件隔离和 AB 对比 |
| 连接 USB 后功耗异常 | USB PHY 或调试链路活跃 | 明确测试是否允许 USB 连接 |
