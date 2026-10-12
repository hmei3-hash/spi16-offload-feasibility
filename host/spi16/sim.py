"""Software slave model: used only to test the host code when no hardware is available.

It implements the behavior in docs/PROTOCOL.md, but its "performance" is meaningless.
The FPGA RTL and testbench are yours to write.
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
        """rx_ber: probability that each MISO word has one random bit flipped, to simulate line noise."""
        self.scratch = 0
        self.errcnt = 0
        self.txncnt = 0
        self.testmem = [0] * TESTMEM_WORDS
        self._status = STATUS_IDLE
        self.rx_ber = rx_ber
        self._rng = random.Random(seed)

    # --- register access ---------------------------------------------
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
            return False  # read-only or unmapped
        return True

    # --- one CS transaction ------------------------------------------
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
            # writes are committed only after the CRC passes
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

        # update the "previous transaction" status and the counters
        status = STATUS_IDLE
        if not crc_ok:
            status |= STATUS_CRC_ERR
            self.errcnt = min(self.errcnt + 1, 0xFFFF)
        if bad_cmd:
            status |= STATUS_BAD_CMD
        self._status = status
        self.txncnt = min(self.txncnt + 1, 0xFFFF)

        # line noise: flip bits after the CRC is computed so the host has to detect it
        if self.rx_ber > 0:
            for i in range(len(resp)):
                if self._rng.random() < self.rx_ber:
                    resp[i] ^= 1 << self._rng.randrange(16)
        return resp


class SimTransport:
    """Wrap a SimSlave as a Transport."""

    def __init__(self, slave: Optional[SimSlave] = None):
        self.slave = slave or SimSlave()

    def xfer(self, tx_words: Sequence[int]) -> List[int]:
        return self.slave.xfer(list(tx_words))

    def close(self):
        pass
