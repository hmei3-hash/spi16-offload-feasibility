# Experiment Design: SPI16 Offload Feasibility

Purpose: use data to judge whether "host + FPGA moving data over SPI" makes sense, then decide whether to
continue or drop it. This repository provides the measurement tools and a decision framework;
**you draw the conclusion from the data.**

## Decision approach

For a task being offloaded:

```
Software time   T_sw
Offloaded time  T_off = T_xfer + T_fpga + T_sync
```

- `T_xfer`: SPI transfer time, measured by this repository (throughput, single-transaction latency).
- `T_fpga`: FPGA compute time, determined by the RTL and clock.
- `T_sync`: overhead from waiting for ready, polling or interrupts.

Offloading is worth continuing only if `T_off < T_sw`, or if it frees up a meaningful amount of host CPU.

## Stages and outputs

| Stage | What to do | Hardware needed | Output |
|---|---|---|---|
| 0 | Self-test the host code | No | `python -m unittest` all pass |
| 1 | Raw host SPI performance (MOSI jumpered to MISO) | Pi only | Throughput, latency, CPU usage, bit errors |
| 2 | Loopback protocol check (your RTL) | Pi + FPGA | ID read, SCRATCH loopback, burst read/write, CRC error counts |
| 3 | Real-link performance | Pi + FPGA | Effective throughput, latency and error rate at each SPI speed |
| 4 | Comparison | No | Plug T_xfer into the task you want to offload and reach a conclusion |

## How to run

```bash
cd host

# Stage 0: no hardware required
python3 -m unittest discover -s tests -v
python3 bench.py device --sim --iters 200

# Stage 1: on the Pi, jumper MOSI (GPIO10, pin 19) to MISO (GPIO9, pin 21)
python3 bench.py raw --bus 0 --dev 0 --speeds 1e6,4e6,8e6,16e6,32e6

# Stages 2/3: after connecting the FPGA (check the schematic and voltages before wiring)
python3 bench.py device --bus 0 --dev 0 --speeds 1e6,4e6,8e6,16e6
```

Each run writes a new timestamped CSV under `results/` and prints a summary to the terminal.

## Decision criteria (fill in the thresholds yourself)

Fill these in before you look at the data, so the bar is not adjusted after the fact.

| Metric | Your pass threshold | Measured | Verdict |
|---|---|---|---|
| Single-register read round-trip latency (p99) | ___ µs | | |
| Effective throughput of a 64-word burst read | ___ KB/s | | |
| Data rate required by the task to offload | ___ KB/s | | |
| Link utilization (required / available) | < ___ % | | |
| Host CPU usage during transfers | < ___ % | | |
| CRC / echo error rate over a long run | ___ | | |
| Software task time T_sw | ___ ms | | |
| Offloaded task time T_off | ___ ms | | |

## Known limitations

- The Python layer adds interpreter overhead: the measured latency includes `spidev` calls and CRC
  computation, so it is pessimistic. If the conclusion lands on a boundary, re-measure in C
  (`ioctl(SPI_IOC_MESSAGE)`).
- `spidev` limits each transfer to 4096 bytes by default (kernel parameter `bufsiz`).
- The Pi's CPU frequency policy, temperature and other processes affect latency; record the conditions.
- The software slave model (`spi16/sim.py`) exists only to test the host code; its "performance" is
  meaningless.
