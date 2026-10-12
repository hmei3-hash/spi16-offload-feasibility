# spi16-offload-feasibility

Measure and judge whether offloading a piece of computation from a host to an FPGA over a
16-bit-word SPI protocol is feasible. The goal of this repository is to reach a conclusion from data:
keep going, or drop the idea.

## What is in here

| Directory | Contents | Status |
|---|---|---|
| `docs/PROTOCOL.md` | Protocol spec: frame format, command word, status word, CRC, register map, RTL design notes | Done |
| `docs/EXPERIMENT.md` | Experiment stages, how to run, go/no-go criteria template (you fill in the thresholds) | Done |
| `host/` | Host-side Python: protocol library, software slave model, benchmark tool, unit tests | Done, 26 tests pass |
| `rtl/` | `spi16_slave.v` skeleton and a list of design questions | Skeleton only, **to be implemented by you** |
| `tb/` | Testbench checklist | Checklist only, **to be implemented by you** |
| `results/` | Benchmark CSV output | Empty until you collect data |

## Quick start

```bash
cd host

# 1. No hardware needed: library self-test + benchmark smoke run against the software slave
python3 -m unittest discover -s tests -v
python3 bench.py device --sim --iters 200 --out /tmp

# 2. Raw SPI performance on a Raspberry Pi
#    Jumper MOSI (GPIO10, header pin 19) to MISO (GPIO9, header pin 21)
sudo apt install python3-spidev
python3 bench.py raw --speeds 1e6,4e6,8e6,16e6,32e6

# 3. With the FPGA connected (check the board schematic, I/O bank voltage and pinout first;
#    never connect 5 V logic to Pi GPIO)
python3 bench.py device --speeds 1e6,4e6,8e6,16e6
```

Each run writes a new timestamped CSV to `results/`. See `docs/EXPERIMENT.md` for the decision criteria.

## Important notes

- `host/spi16/sim.py` is a software slave model that exists **only to test the host code**. Any
  "performance" measured against it is meaningless, so write `--sim` output to `/tmp` and do not commit it
  to `results/`.
- The FPGA side (RTL and testbench) is yours to write. The repository contains only the spec, a
  skeleton and a test checklist.
- The Python layer adds interpreter overhead, so measured latencies are pessimistic. If the conclusion
  lands near a decision boundary, re-measure in C.
- The hardware paths have not been run on real hardware: `raw` and `device` modes exist as code only,
  with no measured data yet.

## Layout

```
docs/    PROTOCOL.md  EXPERIMENT.md
host/    spi16/ (crc, frame, device, sim, transport)  bench.py  tests/
rtl/     spi16_slave.v  README.md
tb/      README.md
results/ (benchmark CSVs)
```
