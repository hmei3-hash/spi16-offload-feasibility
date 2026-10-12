"""Transport layer: send one CS-framed sequence of 16-bit words and receive an equally long sequence back."""

from typing import List, Sequence

from .frame import bytes_to_words, words_to_bytes


class SpidevTransport:
    """Based on Linux spidev (Raspberry Pi).

    Notes:
    - spidev limits a single transfer to 4096 bytes by default (kernel parameter bufsiz);
      this class does not split transfers.
    - Enable SPI with `sudo raspi-config`, or add `dtparam=spi=on` to config.txt.
    """

    MAX_BYTES = 4096

    def __init__(self, bus: int = 0, dev: int = 0, speed_hz: int = 1_000_000, mode: int = 0):
        import spidev  # imported lazily so unit tests run on machines without SPI hardware

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
