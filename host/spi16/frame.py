"""Frame encoding/decoding; see section 2 of docs/PROTOCOL.md."""

import struct
from dataclasses import dataclass
from typing import List, Sequence

from .crc import crc16_words

MAX_LEN = 64
PROTO_VER = 0x1

STATUS_CRC_ERR = 1 << 0
STATUS_BAD_CMD = 1 << 1
STATUS_IDLE = PROTO_VER << 12  # idle, no error


class ProtocolError(Exception):
    """Frame length, echo or CRC mismatch."""


def make_cmd(write: bool, addr: int, length: int, inc: bool = True) -> int:
    if not 1 <= length <= MAX_LEN:
        raise ValueError(f"length must be 1..{MAX_LEN}, got {length}")
    if not 0 <= addr <= 0xFF:
        raise ValueError(f"addr must be 0..255, got {addr}")
    return (int(write) << 15) | (int(inc) << 14) | ((length - 1) << 8) | addr


def parse_cmd(cmd: int):
    """Return (write, inc, length, addr)."""
    return bool(cmd & 0x8000), bool(cmd & 0x4000), ((cmd >> 8) & 0x3F) + 1, cmd & 0xFF


def build_request(cmd: int, payload: Sequence[int]) -> List[int]:
    """MOSI: CMD, GAP(0), payload..., CRC_M. For read transactions the payload is all zeros."""
    words = [cmd & 0xFFFF, 0x0000] + [w & 0xFFFF for w in payload]
    words.append(crc16_words(words))
    return words


@dataclass
class Response:
    status: int          # status of the previous transaction
    echo: int
    data: List[int]


def parse_response(cmd: int, rx: Sequence[int], length: int) -> Response:
    """Validate MISO: STATUS_PREV, ECHO, R..., CRC_S. Raises ProtocolError on failure."""
    expected = length + 3
    if len(rx) != expected:
        raise ProtocolError(f"length: expected {expected} words, got {len(rx)}")
    if crc16_words(rx[:-1]) != rx[-1]:
        raise ProtocolError("crc: CRC_S mismatch")
    if rx[1] != (cmd & 0xFFFF):
        raise ProtocolError(f"echo: sent {cmd:#06x}, got {rx[1]:#06x}")
    return Response(status=rx[0], echo=rx[1], data=list(rx[2:-1]))


def words_to_bytes(words: Sequence[int]) -> bytes:
    return struct.pack(">%dH" % len(words), *words)


def bytes_to_words(data: bytes) -> List[int]:
    if len(data) % 2:
        raise ValueError("odd number of bytes")
    return list(struct.unpack(">%dH" % (len(data) // 2), data))


def decode_status(status: int) -> dict:
    return {
        "version": (status >> 12) & 0xF,
        "crc_err": bool(status & STATUS_CRC_ERR),
        "bad_cmd": bool(status & STATUS_BAD_CMD),
    }
