"""CRC-16/CCITT-FALSE（多项式 0x1021，初值 0xFFFF，不反射，不取反）。

字按大端字节序喂入，见 docs/PROTOCOL.md。
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
    """对 16 位字序列求 CRC，每个字按高字节在前处理。"""
    crc = init
    for w in words:
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ ((w >> 8) & 0xFF)) & 0xFF]
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ (w & 0xFF)) & 0xFF]
    return crc
