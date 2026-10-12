# rtl/

这里只放骨架 `spi16_slave.v`，实现由你自己完成，规格见 [`../docs/PROTOCOL.md`](../docs/PROTOCOL.md)。

## 建议的模块划分

| 模块 | 职责 |
|---|---|
| `spi_rx_tx` | 同步外部信号、位/字计数、移位收发 |
| `frame_fsm` | 帧状态：CMD、GAP、DATA、CRC；CS 上升沿复位 |
| `crc16` | CRC-16/CCITT-FALSE，按位或按字更新 |
| `regfile` | ID、VERSION、SCRATCH、ERRCNT、TXNCNT、TESTMEM |
| `top` | 例化以上模块，处理 MISO 三态、引脚约束 |

## 设计时要先回答的问题

1. 整个逻辑跑在 SCLK 域，还是只在 SCLK 域做移位、其余放系统时钟域？各自的跨时钟域代价是什么？
2. 系统时钟要比 SCLK 快多少，两级同步才稳妥？
3. TESTMEM 用 BRAM 还是分布式 RAM？读延迟是几拍，GAP 字里放得下吗？
4. 写数据暂存在哪里，容量够 64 个字吗？提交动作发生在哪个时钟域？
5. CRC 用逐位串行更新，还是每个字并行更新？资源和时序如何权衡？

## 常见的坑

- 第一个 MISO 位在 SCLK 第一个上升沿之前就要有效。
- CS 提前拉高、中途断帧时，状态机和 CRC 累加器必须能恢复。
- ISE 的 XST 对 SystemVerilog 支持有限，不要用 `logic`、`always_ff` 等。
- 引脚约束（`.ucf`）和 I/O 电压要对照开发板原理图，不能假设能直连 Pi。
