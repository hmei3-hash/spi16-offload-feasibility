"""寄存器级访问接口。"""

from typing import List, Sequence

from .frame import (
    MAX_LEN,
    ProtocolError,
    build_request,
    make_cmd,
    parse_response,
)

REG_ID = 0x00
REG_VERSION = 0x01
REG_SCRATCH = 0x02
REG_ERRCNT = 0x03
REG_TXNCNT = 0x04
REG_TESTMEM = 0x10
TESTMEM_WORDS = 64

DEVICE_ID = 0x5A16


class Spi16Device:
    """在任意 Transport 上实现读写事务。

    注意：`last_status` 是**上一次**事务的状态（见 PROTOCOL.md 第 2 节），
    读写完一次后看到的状态标志属于再之前的那次事务。
    """

    def __init__(self, transport):
        self.transport = transport
        self.last_status = None
        self.stats = {"txns": 0, "crc_errors": 0, "echo_errors": 0, "length_errors": 0}

    def _txn(self, write: bool, addr: int, length: int, payload: Sequence[int], inc: bool):
        cmd = make_cmd(write, addr, length, inc)
        req = build_request(cmd, payload)
        rx = self.transport.xfer(req)
        self.stats["txns"] += 1
        try:
            resp = parse_response(cmd, rx, length)
        except ProtocolError as e:
            kind = str(e).split(":", 1)[0]
            key = {"crc": "crc_errors", "echo": "echo_errors", "length": "length_errors"}.get(kind)
            if key:
                self.stats[key] += 1
            raise
        self.last_status = resp.status
        return resp

    def read(self, addr: int, length: int = 1, inc: bool = True) -> List[int]:
        return self._txn(False, addr, length, [0] * length, inc).data

    def write(self, addr: int, words: Sequence[int], inc: bool = True) -> None:
        if not 1 <= len(words) <= MAX_LEN:
            raise ValueError(f"write length must be 1..{MAX_LEN}")
        self._txn(True, addr, len(words), words, inc)

    def read_reg(self, addr: int) -> int:
        return self.read(addr, 1)[0]

    def write_reg(self, addr: int, value: int) -> None:
        self.write(addr, [value])

    def check_id(self) -> bool:
        return self.read_reg(REG_ID) == DEVICE_ID
