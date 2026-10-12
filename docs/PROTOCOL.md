# SPI16 Protocol Specification v0.1

A register-style SPI protocol with 16-bit words, used to judge whether offloading a computation to an
FPGA is worthwhile. This document is the common reference for the host code, the software slave model,
and the RTL and testbench you write yourself.

## 1. Physical layer

| Item | Value |
|---|---|
| SPI mode | Mode 0 (CPOL = 0, CPHA = 0) |
| Bit order | MSB first |
| Word width | 16 bits, big-endian byte order (high byte first) |
| Framing | CS low delimits one transaction; the rising edge of CS ends it |
| Optional signal | `DRDY` (FPGA-to-host interrupt / ready line; not required in v0.1) |

Levels and pins: before wiring anything, check the board schematic, the I/O bank voltage and the header
pinout. Raspberry Pi GPIO is 3.3 V and is not 5 V tolerant.

## 2. Transaction format

A transaction is `N + 3` words, where `N` is the payload length (1 to 64 words). Reads and writes have
the same length.

```
MOSI: [ CMD ][ GAP=0x0000 ][ D0 ... D(N-1) ][ CRC_M ]
MISO: [ STATUS_PREV ][ ECHO ][ R0 ... R(N-1) ][ CRC_S ]
```

- Write: `D0..D(N-1)` is the data to write; the `R*` words on MISO are all 0.
- Read: `D*` are 0 (placeholders); the `R*` words on MISO carry the data read.
- `GAP` gives the slave one word time (16 SCLK cycles) to decode the command and fetch data. Read
  data therefore starts at the third word.
- `ECHO` is the CMD the slave decoded, sent back so the host can confirm the command was not corrupted.
- `STATUS_PREV` is the status of the **previous** transaction (the slave does not know the result of the
  current one before it has received the CMD).
- Transaction efficiency is roughly `N / (N + 3)`.

### 2.1 Command word (CMD)

| Bits | Name | Meaning |
|---|---|---|
| 15 | W | 1 = write, 0 = read |
| 14 | INC | 1 = address auto-increments per word; 0 = every word accesses the same address (FIFO style) |
| 13:8 | LEN-1 | Payload length minus one (0 to 63, i.e. 1 to 64 words) |
| 7:0 | ADDR | Starting register address |

The length in CMD must match the actual frame length; otherwise the command is treated as bad.

### 2.2 Status word (STATUS)

| Bits | Name | Meaning |
|---|---|---|
| 15:12 | VER | Protocol version; v0.1 = 0x1 |
| 1 | BAD_CMD | Previous transaction had an illegal command (unmapped address, or length not matching the frame) |
| 0 | CRC_ERR | Previous transaction had a CRC mismatch |

Idle with no error: STATUS = `0x1000`.

### 2.3 Checksum

CRC-16/CCITT-FALSE: polynomial `0x1021`, initial value `0xFFFF`, no reflection, no final XOR.
Input is fed word by word in big-endian byte order. Check value: the CRC of `"123456789"` is `0x29B1`.

- `CRC_M` covers every word on MOSI except itself: `CMD, GAP, D*`.
- `CRC_S` covers every word on MISO except itself: `STATUS_PREV, ECHO, R*`.

**A write takes effect only after its CRC has been verified.** A write transaction with a bad CRC must
not change any register; it must set `CRC_ERR` and increment the error counter. This means the RTL has to
buffer the write data and commit it at the end of the transaction (after the CS rising edge, once the CRC
has been compared).

## 3. Register map (for testing)

| Address | Name | Access | Description |
|---|---|---|---|
| 0x00 | ID | RO | Fixed `0x5A16` |
| 0x01 | VERSION | RO | Design version; v0.1 = `0x0001` |
| 0x02 | SCRATCH | RW | Loopback testing |
| 0x03 | ERRCNT | RO | Count of CRC-error transactions; writing any value clears it; saturates at 0xFFFF |
| 0x04 | TXNCNT | RO | Transaction count (including erroneous ones); saturates at 0xFFFF |
| 0x10 to 0x4F | TESTMEM | RW | 64 words of test memory for burst read/write and throughput tests |

Accessing an unmapped address changes no state, reads return 0, and `BAD_CMD` is set.

## 4. Design decisions and pitfalls (for the RTL author)

1. **Clock domain crossing**: SCLK and the system clock are asynchronous. Do not synchronize multi-bit
   data with plain two-flop synchronizers; use a handshake or an asynchronous FIFO.
2. **CS reset**: CS going high must unconditionally reset the in-frame state (bit counter, word counter,
   CRC accumulator).
3. **MISO tri-state**: when CS is high, MISO should be high impedance (if several slaves share the line).
   Put the tri-state in an IOBUF at the top level, not in a submodule.
4. **Sampling edge**: in Mode 0, sample MOSI on the rising edge of SCLK and update MISO on the falling
   edge. The first MISO bit must be valid after CS falls and before the first SCLK rising edge.
5. **Read data preparation time**: the GAP word gives 16 SCLK cycles to fetch data, but if TESTMEM is a
   BRAM, a synchronous read has one cycle of latency. Account for it in the design.
6. **Commit writes only after the CRC passes** (see 2.3).
7. **ISE toolchain**: Spartan-6 supports only ISE, and XST has limited SystemVerilog support. Write
   Verilog-2001.
8. **Metastability**: `cs_n`, `sclk` and `mosi` come from outside; synchronize them before they enter the
   system clock domain. If the whole design lives in the SCLK domain, pay attention to how SCLK rising
   edges line up with word boundaries.
9. **Byte order**: use big-endian on both ends. On the host use `struct.pack(">H")`; do not depend on
   machine endianness.
