# 实验设计：SPI16 offload 可行性

目的：用数据判断"主机 + FPGA 通过 SPI 搬数据"是否有意义，再决定继续还是废弃。
本仓库只提供测量工具和判定框架，**结论由你根据数据下**。

## 判定思路

对某个被 offload 的任务：

```
软件版耗时   T_sw
offload 版   T_off = T_xfer + T_fpga + T_sync
```

- `T_xfer`：SPI 传输耗时，由本仓库测得（吞吐、单次事务延迟）。
- `T_fpga`：FPGA 计算耗时，由 RTL 和时钟决定。
- `T_sync`：等待就绪、轮询或中断带来的开销。

只有当 `T_off < T_sw`，或者 offload 能明显释放主机 CPU 时，才值得继续。

## 阶段与产出

| 阶段 | 要做的事 | 需要硬件 | 产出 |
|---|---|---|---|
| 0 | 主机代码自测 | 否 | `python -m unittest` 全部通过 |
| 1 | 主机 SPI 原始性能（MOSI 与 MISO 短接） | 仅 Pi | 吞吐、延迟、CPU 占用、位错误数 |
| 2 | 回环协议验证（你写的 RTL） | Pi + FPGA | ID 读取、SCRATCH 回环、突发读写、CRC 错误统计 |
| 3 | 真实链路性能 | Pi + FPGA | 各 SPI 速率下的有效吞吐、延迟、错误率 |
| 4 | 对比 | 无 | 把 T_xfer 代入你要 offload 的任务，得出结论 |

## 如何运行

```bash
cd host

# 阶段 0：不需要任何硬件
python3 -m unittest discover -s tests -v
python3 bench.py device --sim --iters 200

# 阶段 1：Pi 上，把 MOSI(GPIO10, pin 19) 和 MISO(GPIO9, pin 21) 用杜邦线短接
python3 bench.py raw --bus 0 --dev 0 --speeds 1e6,4e6,8e6,16e6,32e6

# 阶段 2/3：接上 FPGA 后（接线前先核对原理图和电压）
python3 bench.py device --bus 0 --dev 0 --speeds 1e6,4e6,8e6,16e6
```

每次运行会把结果追加写入 `results/` 下的 CSV，并在终端打印汇总。

## 判定标准（请你自己填写阈值）

先在看数据之前填好，避免事后调整标准。

| 指标 | 你的通过阈值 | 实测 | 结论 |
|---|---|---|---|
| 单寄存器读往返延迟（p99） | ___ µs | | |
| 64 字突发读有效吞吐 | ___ KB/s | | |
| 要 offload 的任务所需数据率 | ___ KB/s | | |
| 链路利用率（需要的 / 可用的） | < ___ % | | |
| 主机 CPU 占用（传输期间） | < ___ % | | |
| 长时间运行 CRC/回显错误率 | ___ | | |
| 软件版任务耗时 T_sw | ___ ms | | |
| offload 版任务耗时 T_off | ___ ms | | |

## 已知局限

- Python 层有解释器开销，测得的延迟包含 `spidev` 调用和 CRC 计算，偏悲观。如果结论落在边界上，需要用 C 重测（`ioctl(SPI_IOC_MESSAGE)`）。
- `spidev` 每次传输默认最多 4096 字节（内核参数 `bufsiz`）。
- 测试时 Pi 的 CPU 频率策略、温度和其他进程会影响延迟，请记录条件。
- 软件仿真从机（`spi16/sim.py`）只用来测主机代码，它的"性能"没有任何意义。
