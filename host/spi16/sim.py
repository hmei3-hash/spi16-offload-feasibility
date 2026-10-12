"""软件仿真从机：只用来在没有硬件时测试主机代码。

它实现 docs/PROTOCOL.md 的行为，但它的"性能"没有任何意义。
FPGA 的 RTL 和 testbench 需要你自己写。
"""

import random
from typing import List, Optional, Sequence

from .crc import crc16_words
from .device import (
    DEVICE_ID,
    REG_ERRCNT,
    REG_ID,
    REG_SCRATCH,
    REG_TESTMEM,
    REG_TXNCNT,
    REG_VERSION,
    TESTMEM_WORDS,
)
from .frame import (
    PROTO_VER,
    STATUS_BAD_CMD,
    STATUS_CRC_ERR,
    STATUS_IDLE,
    parse_cmd,
)

DESIGN_VERSION = 0x0001


class SimSlave:
    def __init__(self, rx_ber: float = 0.0, seed: Optional[int] = 0):
        """rx_ber: 每个 MISO 字被翻转一个随机比特的概率，用来模拟线上噪声。"""
        self.scratch = 0
        self.errcnt = 0
        self.txncnt = 0
        self.testmem = [0] * TESTMEM_WORDS
        self._status = STATUS_IDLE
        self.rx_ber = rx_ber
        self._rng = random.Random(seed)

    # --- 寄存器访问 -------------------------------------------------
    def _read_reg(self, addr: int) -> Optional[int]:
        if addr == REG_ID:
            return DEVICE_ID
        if addr == REG_VERSION:
            return DESIGN_VERSION
        if addr == REG_SCRATCH:
            return self.scratch
        if addr == REG_ERRCNT:
            return self.errcnt
        if addr == REG_TXNCNT:
            return self.txncnt
        if REG_TESTMEM <= addr < REG_TESTMEM + TESTMEM_WORDS:
            return self.testmem[addr - REG_TESTMEM]
        return None

    def _write_reg(self, addr: int, value: int) -> bool:
        if addr == REG_SCRATCH:
            self.scratch = value
        elif addr == REG_ERRCNT:
            self.errcnt = 0
        elif REG_TESTMEM <= addr < REG_TESTMEM + TESTMEM_WORDS:
            self.testmem[addr - REG_TESTMEM] = value
        else:
            return False  # 只读或未映射
        return True

    # --- 一次 CS 事务 -----------------------------------------------
    def xfer(self, tx: Sequence[int]) -> List[int]:
        n = len(tx) - 3
        cmd = tx[0] if tx else 0
        write, inc, length, addr = parse_cmd(cmd)
        crc_ok = n >= 0 and crc16_words(tx[:-1]) == tx[-1]
        bad_cmd = False
        out = [0] * max(n, 0)

        if n < 1 or n != length:
            bad_cmd = True
        elif crc_ok:
            # 写入只在 CRC 通过之后提交
            for i in range(n):
                a = addr + (i if inc else 0)
                if write:
                    if not self._write_reg(a, tx[2 + i] & 0xFFFF):
                        bad_cmd = True
                else:
                    v = self._read_reg(a)
                    if v is None:
                        bad_cmd = True
                        v = 0
                    out[i] = v

        resp = [self._status, cmd & 0xFFFF] + out
        resp.append(crc16_words(resp))

        # 更新"上一次事务"状态和计数
        status = STATUS_IDLE
        if not crc_ok:
            status |= STATUS_CRC_ERR
            self.errcnt = min(self.errcnt + 1, 0xFFFF)
        if bad_cmd:
            status |= STATUS_BAD_CMD
        self._status = status
        self.txncnt = min(self.txncnt + 1, 0xFFFF)

        # 线路噪声：CRC 之后再翻转，让主机去检出
        if self.rx_ber > 0:
            for i in range(len(resp)):
                if self._rng.random() < self.rx_ber:
                    resp[i] ^= 1 << self._rng.randrange(16)
        return resp


class SimTransport:
    """把 SimSlave 包装成 Transport。"""

    def __init__(self, slave: Optional[SimSlave] = None):
        self.slave = slave or SimSlave()

    def xfer(self, tx_words: Sequence[int]) -> List[int]:
        return self.slave.xfer(list(tx_words))

    def close(self):
        pass
