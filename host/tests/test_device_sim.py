import random
import unittest

from spi16 import ProtocolError, SimSlave, SimTransport, Spi16Device
from spi16.crc import crc16_words
from spi16.device import (
    DEVICE_ID,
    REG_ERRCNT,
    REG_ID,
    REG_SCRATCH,
    REG_TESTMEM,
    REG_TXNCNT,
    REG_VERSION,
)
from spi16.frame import STATUS_BAD_CMD, STATUS_CRC_ERR, STATUS_IDLE, build_request, make_cmd


def make_dev(**kw):
    slave = SimSlave(**kw)
    return Spi16Device(SimTransport(slave)), slave


class TestDeviceSim(unittest.TestCase):
    def test_id_and_version(self):
        dev, _ = make_dev()
        self.assertEqual(dev.read_reg(REG_ID), DEVICE_ID)
        self.assertEqual(dev.read_reg(REG_VERSION), 0x0001)
        self.assertTrue(dev.check_id())

    def test_scratch_roundtrip(self):
        dev, _ = make_dev()
        for v in [0, 0xFFFF, 0xA5A5, 0x5A5A] + [1 << i for i in range(16)]:
            dev.write_reg(REG_SCRATCH, v)
            self.assertEqual(dev.read_reg(REG_SCRATCH), v)

    def test_burst_inc(self):
        dev, _ = make_dev()
        rng = random.Random(0)
        data = [rng.randrange(0x10000) for _ in range(64)]
        dev.write(REG_TESTMEM, data)
        self.assertEqual(dev.read(REG_TESTMEM, 64), data)
        self.assertEqual(dev.read(REG_TESTMEM + 5, 3), data[5:8])

    def test_burst_no_inc_last_word_wins(self):
        dev, _ = make_dev()
        dev.write(REG_TESTMEM, [1, 2, 3, 4], inc=False)
        self.assertEqual(dev.read_reg(REG_TESTMEM), 4)
        self.assertEqual(dev.read_reg(REG_TESTMEM + 1), 0)

    def test_status_is_previous_transaction(self):
        dev, slave = make_dev()
        dev.read(0x99, 1)                       # unmapped address: this transaction itself reports no error
        self.assertEqual(dev.last_status, STATUS_IDLE)
        dev.read_reg(REG_ID)                    # the next transaction is the one that reports the previous BAD_CMD
        self.assertTrue(dev.last_status & STATUS_BAD_CMD)
        dev.read_reg(REG_ID)
        self.assertEqual(dev.last_status, STATUS_IDLE)

    def test_unmapped_read_returns_zero_and_no_side_effect(self):
        dev, _ = make_dev()
        dev.write_reg(REG_SCRATCH, 0x1234)
        self.assertEqual(dev.read(0x99, 2), [0, 0])
        self.assertEqual(dev.read_reg(REG_SCRATCH), 0x1234)

    def test_write_to_readonly_sets_bad_cmd(self):
        dev, _ = make_dev()
        dev.write_reg(REG_ID, 0xDEAD)
        dev.read_reg(REG_ID)
        # ID still has its original value
        self.assertEqual(dev.read_reg(REG_ID), DEVICE_ID)

    def test_bad_crc_write_is_not_committed(self):
        dev, slave = make_dev()
        dev.write_reg(REG_SCRATCH, 0x1111)
        cmd = make_cmd(True, REG_SCRATCH, 1)
        req = build_request(cmd, [0x2222])
        req[-1] ^= 0x0001                       # corrupt CRC_M
        slave.xfer(req)
        self.assertEqual(dev.read_reg(REG_SCRATCH), 0x1111)   # not committed
        # the next transaction returns the status of the previous (bad-CRC) one
        self.assertTrue(dev.last_status & STATUS_CRC_ERR)

    def test_errcnt_counts_and_clears(self):
        dev, slave = make_dev()
        for _ in range(3):
            req = build_request(make_cmd(False, REG_ID, 1), [0])
            req[-1] ^= 0x8000
            slave.xfer(req)
        self.assertEqual(dev.read_reg(REG_ERRCNT), 3)
        dev.write_reg(REG_ERRCNT, 0)
        self.assertEqual(dev.read_reg(REG_ERRCNT), 0)

    def test_txncnt_increments(self):
        dev, _ = make_dev()
        dev.read_reg(REG_ID)
        dev.read_reg(REG_ID)
        self.assertEqual(dev.read_reg(REG_TXNCNT), 2)

    def test_length_mismatch_is_bad_cmd(self):
        dev, slave = make_dev()
        cmd = make_cmd(True, REG_SCRATCH, 4)     # claims 4 words
        req = build_request(cmd, [0x7777])       # but only 1 word is actually sent
        slave.xfer(req)
        dev.read_reg(REG_ID)
        self.assertTrue(dev.last_status & STATUS_BAD_CMD)
        self.assertEqual(dev.read_reg(REG_SCRATCH), 0)

    def test_line_noise_is_detected(self):
        dev, _ = make_dev(rx_ber=1.0, seed=1)    # every returned word has one bit flipped
        with self.assertRaises(ProtocolError):
            dev.read_reg(REG_ID)
        self.assertGreaterEqual(dev.stats["crc_errors"] + dev.stats["echo_errors"], 1)

    def test_response_crc_is_valid_for_clean_line(self):
        _, slave = make_dev()
        rx = slave.xfer(build_request(make_cmd(False, REG_ID, 1), [0]))
        self.assertEqual(rx[-1], crc16_words(rx[:-1]))


if __name__ == "__main__":
    unittest.main()
