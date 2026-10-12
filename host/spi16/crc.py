"""CRC-16/CCITT-FALSE (polynomial 0x1021, init 0xFFFF, no reflection, no final XOR).

Words are fed in big-endian byte order; see docs/PROTOCOL.md.
"""

from typing import Iterable

_POLY = 0x1021


def _make_table():
    table = []
    for byte in range(256):
        crc = byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
        table.append(crc)
    return table


_TABLE = _make_table()


def crc16_bytes(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ b) & 0xFF]
    return crc


def crc16_words(words: Iterable[int], init: int = 0xFFFF) -> int:
    """CRC over a sequence of 16-bit words, each processed high byte first."""
    crc = init
    for w in words:
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ ((w >> 8) & 0xFF)) & 0xFF]
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ (w & 0xFF)) & 0xFF]
    return crc
