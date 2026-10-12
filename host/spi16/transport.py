"""传输层：把一次 CS 帧的 16 位字序列发出去，同时收回等长的字序列。"""

from typing import List, Sequence

from .frame import bytes_to_words, words_to_bytes


class SpidevTransport:
    """基于 Linux spidev（Raspberry Pi）。

    注意：
    - spidev 单次传输默认上限 4096 字节（内核参数 bufsiz），本类不做拆分。
    - 开启 SPI：`sudo raspi-config` 打开 SPI，或在 config.txt 里加 `dtparam=spi=on`。
    """

    MAX_BYTES = 4096

    def __init__(self, bus: int = 0, dev: int = 0, speed_hz: int = 1_000_000, mode: int = 0):
        import spidev  # 延迟导入，没有硬件的机器也能跑单元测试

        self.spi = spidev.SpiDev()
        self.spi.open(bus, dev)
        self.spi.max_speed_hz = int(speed_hz)
        self.spi.mode = mode
        self.spi.bits_per_word = 8
        self.speed_hz = int(speed_hz)

    def xfer_bytes(self, data: bytes) -> bytes:
        if len(data) > self.MAX_BYTES:
            raise ValueError(f"transfer of {len(data)} bytes exceeds spidev limit {self.MAX_BYTES}")
        return bytes(self.spi.xfer2(list(data)))

    def xfer(self, tx_words: Sequence[int]) -> List[int]:
        return bytes_to_words(self.xfer_bytes(words_to_bytes(tx_words)))

    def close(self):
        self.spi.close()
