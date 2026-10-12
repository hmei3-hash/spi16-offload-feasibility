"""Register-level access interface."""

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
    """Implements read/write transactions on any Transport.

    Note: `last_status` is the status of the **previous** transaction (see section 2 of
    PROTOCOL.md), so the status flags seen after a read or write belong to the transaction
    before that one.
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
