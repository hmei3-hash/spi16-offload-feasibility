import unittest

from spi16.crc import crc16_bytes, crc16_words
from spi16.frame import (
    ProtocolError,
    STATUS_IDLE,
    build_request,
    bytes_to_words,
    decode_status,
    make_cmd,
    parse_cmd,
    parse_response,
    words_to_bytes,
)


class TestCrc(unittest.TestCase):
    def test_known_check_value(self):
        # CRC-16/CCITT-FALSE 的标准检验值
        self.assertEqual(crc16_bytes(b"123456789"), 0x29B1)

    def test_words_match_bytes(self):
        words = [0x1234, 0xABCD, 0x0000, 0xFFFF]
        self.assertEqual(crc16_words(words), crc16_bytes(words_to_bytes(words)))

    def test_empty(self):
        self.assertEqual(crc16_bytes(b""), 0xFFFF)


class TestFrame(unittest.TestCase):
    def test_cmd_roundtrip(self):
        for write in (False, True):
            for inc in (False, True):
                for length in (1, 2, 17, 64):
                    for addr in (0, 1, 0x10, 0xFF):
                        cmd = make_cmd(write, addr, length, inc)
                        self.assertEqual(parse_cmd(cmd), (write, inc, length, addr))

    def test_cmd_bit_layout(self):
        self.assertEqual(make_cmd(True, 0x02, 1, inc=False), 0x8002)
        self.assertEqual(make_cmd(False, 0x10, 64, inc=True), 0x7F10)

    def test_cmd_range_checks(self):
        with self.assertRaises(ValueError):
            make_cmd(False, 0, 0)
        with self.assertRaises(ValueError):
            make_cmd(False, 0, 65)
        with self.assertRaises(ValueError):
            make_cmd(False, 256, 1)

    def test_request_layout(self):
        cmd = make_cmd(True, 0x02, 2)
        req = build_request(cmd, [0x1111, 0x2222])
        self.assertEqual(len(req), 2 + 3)
        self.assertEqual(req[:4], [cmd, 0x0000, 0x1111, 0x2222])
        self.assertEqual(req[-1], crc16_words(req[:-1]))

    def _good_response(self, cmd, data):
        rx = [STATUS_IDLE, cmd] + list(data)
        rx.append(crc16_words(rx))
        return rx

    def test_parse_response_ok(self):
        cmd = make_cmd(False, 0x00, 2)
        resp = parse_response(cmd, self._good_response(cmd, [0x5A16, 0x0001]), 2)
        self.assertEqual(resp.data, [0x5A16, 0x0001])
        self.assertEqual(resp.status, STATUS_IDLE)

    def test_parse_response_bad_crc(self):
        cmd = make_cmd(False, 0x00, 1)
        rx = self._good_response(cmd, [0x5A16])
        rx[2] ^= 0x0001
        with self.assertRaisesRegex(ProtocolError, "crc"):
            parse_response(cmd, rx, 1)

    def test_parse_response_bad_echo(self):
        cmd = make_cmd(False, 0x00, 1)
        other = make_cmd(False, 0x01, 1)
        with self.assertRaisesRegex(ProtocolError, "echo"):
            parse_response(cmd, self._good_response(other, [0]), 1)

    def test_parse_response_bad_length(self):
        cmd = make_cmd(False, 0x00, 2)
        with self.assertRaisesRegex(ProtocolError, "length"):
            parse_response(cmd, self._good_response(cmd, [1]), 2)

    def test_bytes_words_roundtrip(self):
        words = [0x0000, 0x00FF, 0xFF00, 0xABCD]
        self.assertEqual(bytes_to_words(words_to_bytes(words)), words)
        self.assertEqual(words_to_bytes([0x1234]), b"\x12\x34")  # 大端

    def test_decode_status(self):
        self.assertEqual(decode_status(STATUS_IDLE), {"version": 1, "crc_err": False, "bad_cmd": False})
        self.assertTrue(decode_status(STATUS_IDLE | 1)["crc_err"])
        self.assertTrue(decode_status(STATUS_IDLE | 2)["bad_cmd"])


if __name__ == "__main__":
    unittest.main()
