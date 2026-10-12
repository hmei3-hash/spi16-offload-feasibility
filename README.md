# spi16-offload-feasibility

用一个 16 位字的 SPI 协议，测量并判断"把某块计算从主机 offload 到 FPGA"是否可行。
这个仓库的目的是拿数据下结论：继续做，还是废弃。

## 里面有什么

| 目录 | 内容 | 状态 |
|---|---|---|
| `docs/PROTOCOL.md` | 协议规格：帧格式、命令字、状态字、CRC、寄存器表、RTL 设计要点 | 完成 |
| `docs/EXPERIMENT.md` | 实验阶段、运行方法、判定标准模板（阈值由你填） | 完成 |
| `host/` | 主机端 Python：协议库、软件仿真从机、benchmark 工具、单元测试 | 完成，26 个测试通过 |
| `rtl/` | `spi16_slave.v` 骨架和设计问题清单 | 只有骨架，**由你实现** |
| `tb/` | testbench 测试清单 | 只有清单，**由你实现** |
| `results/` | benchmark 输出 CSV | 空，等你跑出数据 |

## 快速开始

```bash
cd host

# 1. 不需要任何硬件：协议库自测 + 软件仿真从机上的 benchmark 冒烟
python3 -m unittest discover -s tests -v
python3 bench.py device --sim --iters 200 --out /tmp

# 2. 在 Raspberry Pi 上测原始 SPI 性能
#    把 MOSI(GPIO10, 排针 19) 和 MISO(GPIO9, 排针 21) 用杜邦线短接
sudo apt install python3-spidev
python3 bench.py raw --speeds 1e6,4e6,8e6,16e6,32e6

# 3. 接上 FPGA（接线前先核对原理图、I/O 电压和引脚，不要直连 5 V）
python3 bench.py device --speeds 1e6,4e6,8e6,16e6
```

结果会追加写入 `results/`，字段说明见 `docs/EXPERIMENT.md`。

## 重要说明

- `host/spi16/sim.py` 是软件仿真从机，**只用来测试主机代码**。用它跑出的任何"性能"都没有意义，
  所以 `--sim` 的输出建议写到 `/tmp`，不要提交到 `results/`。
- FPGA 一侧的 RTL 和 testbench 需要你自己写，仓库里只有规格、骨架和测试清单。
- Python 层有解释器开销，测得的延迟偏悲观。如果结论落在判定边界上，需要用 C 重测。
- 没有在真实硬件上跑过：raw 和 device 模式的硬件路径目前只有代码，没有实测数据。

## 目录

```
docs/    PROTOCOL.md  EXPERIMENT.md
host/    spi16/ (crc, frame, device, sim, transport)  bench.py  tests/
rtl/     spi16_slave.v  README.md
tb/      README.md
results/ （benchmark CSV）
```
