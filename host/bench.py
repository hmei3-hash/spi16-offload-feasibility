#!/usr/bin/env python3
"""SPI16 offload 可行性 benchmark。

模式：
  raw     MOSI 与 MISO 短接，测 Pi 端 SPI 的原始吞吐、延迟、CPU 占用、位错误。
  device  对真实 FPGA（或 --sim 软件仿真从机）做协议事务：ID、回环、突发读写、吞吐。

示例：
  python3 bench.py device --sim --iters 200
  python3 bench.py raw --speeds 1e6,4e6,8e6,16e6 --sizes 2,16,128,1024,4096
  python3 bench.py device --speeds 1e6,4e6,8e6

结果追加写入 ../results/bench_<mode>_<时间戳>.csv。
"""

import argparse
import csv
import os
import random
import time
from datetime import datetime

from spi16 import ProtocolError, SimSlave, SimTransport, Spi16Device
from spi16.device import (
    REG_ERRCNT,
    REG_SCRATCH,
    REG_TESTMEM,
    REG_VERSION,
)

FIELDS = [
    "timestamp", "mode", "speed_hz", "test", "size", "iters",
    "mean_us", "p50_us", "p99_us", "max_us",
    "payload_KBps", "theoretical_KBps", "efficiency", "cpu_util",
    "protocol_errors", "data_errors",
]


def pct(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    idx = min(len(sorted_vals) - 1, int(round(p / 100.0 * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def parse_list(text, cast):
    return [cast(float(x)) for x in text.split(",") if x.strip()]


class Recorder:
    def __init__(self, mode, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(out_dir, f"bench_{mode}_{stamp}.csv")
        self.mode = mode
        self.f = open(self.path, "w", newline="")
        self.w = csv.DictWriter(self.f, fieldnames=FIELDS)
        self.w.writeheader()
        self.rows = 0

    def add(self, **row):
        self.rows += 1
        row.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        row.setdefault("mode", self.mode)
        self.w.writerow({k: row.get(k, "") for k in FIELDS})
        self.f.flush()
        print(
            f"{row.get('speed_hz', ''):>10} {row.get('test', ''):<14} size={row.get('size', ''):<5} "
            f"mean={row.get('mean_us', ''):>9} p99={row.get('p99_us', ''):>9} us  "
            f"{row.get('payload_KBps', ''):>9} KB/s  cpu={row.get('cpu_util', '')} "
            f"perr={row.get('protocol_errors', '')} derr={row.get('data_errors', '')}"
        )

    def close(self):
        self.f.close()
        if self.rows == 0:
            os.remove(self.path)  # 没有任何结果就不留空文件
            return
        print(f"\n结果已写入 {self.path}")


def summarize(durs_us, payload_bytes, wall_s, cpu_s, speed_hz):
    s = sorted(durs_us)
    mean = sum(s) / len(s)
    kbps = payload_bytes / (mean * 1e-6) / 1000.0
    theo = speed_hz / 8.0 / 1000.0 if speed_hz else ""
    return dict(
        mean_us=round(mean, 1),
        p50_us=round(pct(s, 50), 1),
        p99_us=round(pct(s, 99), 1),
        max_us=round(s[-1], 1),
        payload_KBps=round(kbps, 1),
        theoretical_KBps=round(theo, 1) if theo != "" else "",
        efficiency=round(kbps / theo, 3) if theo else "",
        cpu_util=round(cpu_s / wall_s, 2) if wall_s > 0 else "",
    )


def timed_loop(fn, iters):
    """fn() 返回 (耗时被计入的结果)；这里只计时。返回 (durs_us, wall_s, cpu_s)。"""
    durs = []
    c0, w0 = time.process_time(), time.perf_counter()
    for _ in range(iters):
        a = time.perf_counter_ns()
        fn()
        durs.append((time.perf_counter_ns() - a) / 1000.0)
    return durs, time.perf_counter() - w0, time.process_time() - c0


# ---------------------------------------------------------------- raw
def run_raw(args, rec):
    from spi16.transport import SpidevTransport

    rng = random.Random(args.seed)
    for speed in parse_list(args.speeds, int):
        t = SpidevTransport(args.bus, args.dev, speed)
        try:
            for size in parse_list(args.sizes, int):
                payload = bytes(rng.randrange(256) for _ in range(size))
                for _ in range(args.warmup):
                    t.xfer_bytes(payload)
                last = {}

                def one():
                    last["rx"] = t.xfer_bytes(payload)

                bad = 0

                def checked():
                    nonlocal bad
                    one()
                    if last["rx"] != payload:
                        bad += sum(1 for a, b in zip(last["rx"], payload) if a != b)

                # 位错误统计放在计时之外：先测时间，再单独跑校验
                durs, wall, cpu = timed_loop(one, args.iters)
                for _ in range(min(args.iters, 200)):
                    checked()
                rec.add(
                    speed_hz=speed, test="raw_loopback", size=size, iters=args.iters,
                    protocol_errors=0, data_errors=bad,
                    **summarize(durs, size, wall, cpu, speed),
                )
        finally:
            t.close()


# ------------------------------------------------------------- device
def make_transport(args, speed):
    if args.sim:
        return SimTransport(SimSlave(rx_ber=args.ber, seed=args.seed))
    from spi16.transport import SpidevTransport

    return SpidevTransport(args.bus, args.dev, speed)


def run_device(args, rec):
    rng = random.Random(args.seed)
    speeds = parse_list(args.speeds, int) if not args.sim else [0]
    for speed in speeds:
        transport = make_transport(args, speed)
        dev = Spi16Device(transport)
        try:
            # --- 功能检查
            perr = derr = 0
            try:
                id_ok = dev.check_id()
            except ProtocolError as e:
                print(f"[{speed}] ID 读取失败：{e}")
                id_ok = False
            if not id_ok and not args.force:
                print(f"[{speed}] 设备无响应或 ID 不符，跳过该速率（--force 可强制继续）")
                rec.add(speed_hz=speed, test="id_check", size=1, iters=1,
                        protocol_errors=1, data_errors=0)
                continue
            patterns = [0x0000, 0xFFFF, 0xA5A5, 0x5A5A] + [1 << i for i in range(16)]
            for p in patterns:
                try:
                    dev.write_reg(REG_SCRATCH, p)
                    if dev.read_reg(REG_SCRATCH) != p:
                        derr += 1
                except ProtocolError:
                    perr += 1
            rec.add(speed_hz=speed, test="scratch_check", size=len(patterns), iters=len(patterns),
                    protocol_errors=perr, data_errors=derr)

            # --- 单寄存器读延迟
            perr = 0

            def rd():
                nonlocal perr
                try:
                    dev.read_reg(REG_VERSION)
                except ProtocolError:
                    perr += 1

            for _ in range(args.warmup):
                rd()
            perr = 0
            durs, wall, cpu = timed_loop(rd, args.iters)
            rec.add(speed_hz=speed, test="reg_read", size=1, iters=args.iters,
                    protocol_errors=perr, data_errors=0,
                    **summarize(durs, 2, wall, cpu, speed))

            # --- 突发读写
            for n in parse_list(args.bursts, int):
                data = [rng.randrange(0x10000) for _ in range(n)]
                perr = derr = 0

                def wr():
                    nonlocal perr
                    try:
                        dev.write(REG_TESTMEM, data)
                    except ProtocolError:
                        perr += 1

                got = {}

                def rdb():
                    nonlocal perr
                    try:
                        got["d"] = dev.read(REG_TESTMEM, n)
                    except ProtocolError:
                        perr += 1
                        got["d"] = None

                for _ in range(args.warmup):
                    wr()
                perr = 0
                durs, wall, cpu = timed_loop(wr, args.iters)
                rec.add(speed_hz=speed, test="burst_write", size=n, iters=args.iters,
                        protocol_errors=perr, data_errors=0,
                        **summarize(durs, n * 2, wall, cpu, speed))

                perr = 0
                mismatches = 0
                wr()  # 确保 TESTMEM 里是 data
                c0, w0 = time.process_time(), time.perf_counter()
                durs = []
                for _ in range(args.iters):
                    a = time.perf_counter_ns()
                    rdb()
                    durs.append((time.perf_counter_ns() - a) / 1000.0)
                    if got["d"] is not None and got["d"] != data:
                        mismatches += 1
                wall, cpu = time.perf_counter() - w0, time.process_time() - c0
                rec.add(speed_hz=speed, test="burst_read", size=n, iters=args.iters,
                        protocol_errors=perr, data_errors=mismatches,
                        **summarize(durs, n * 2, wall, cpu, speed))

            # --- 设备侧错误计数
            try:
                print(f"[{speed}] 设备侧 ERRCNT = {dev.read_reg(REG_ERRCNT)}，主机侧统计 = {dev.stats}")
            except ProtocolError:
                print(f"[{speed}] 读取 ERRCNT 失败，主机侧统计 = {dev.stats}")
        finally:
            transport.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["raw", "device"])
    ap.add_argument("--bus", type=int, default=0)
    ap.add_argument("--dev", type=int, default=0)
    ap.add_argument("--speeds", default="1e6,4e6,8e6", help="SPI 时钟列表(Hz)，逗号分隔")
    ap.add_argument("--sizes", default="2,16,128,1024,4096", help="raw 模式的传输字节数")
    ap.add_argument("--bursts", default="1,4,16,64", help="device 模式的突发字数")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--warmup", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sim", action="store_true", help="device 模式使用软件仿真从机（无需硬件）")
    ap.add_argument("--ber", type=float, default=0.0, help="--sim 时每个 MISO 字被翻转一位的概率")
    ap.add_argument("--force", action="store_true", help="ID 检查失败也继续")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results"))
    args = ap.parse_args()

    if args.mode == "raw" and args.sim:
        ap.error("raw 模式需要真实 SPI 设备，不支持 --sim")

    rec = Recorder(args.mode, args.out)
    try:
        (run_raw if args.mode == "raw" else run_device)(args, rec)
    except ImportError as e:
        raise SystemExit(
            f"缺少依赖：{e}\n在 Raspberry Pi 上请安装：sudo apt install python3-spidev "
            "（或 pip install spidev），并确认已开启 SPI。"
        )
    except FileNotFoundError as e:
        raise SystemExit(
            f"打不开 SPI 设备：{e}\n请确认已开启 SPI，且存在 /dev/spidev{args.bus}.{args.dev}。"
        )
    finally:
        rec.close()


if __name__ == "__main__":
    main()
