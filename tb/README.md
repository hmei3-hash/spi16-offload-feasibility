# tb/

You write the testbench yourself. Below is a suggested checklist of what to cover; the spec is in
[`../docs/PROTOCOL.md`](../docs/PROTOCOL.md).

## Directed tests

| # | Test | Expected result |
|---|---|---|
| 1 | Read ID (0x00) | Returns `0x5A16`, ECHO equals the CMD sent, CRC_S is correct |
| 2 | Read VERSION | Returns `0x0001` |
| 3 | Write SCRATCH, read it back | Value read back matches |
| 4 | Burst write to TESTMEM (INC=1, N=64), read back | Every word matches |
| 5 | INC=0, write N words to the same address | The last word takes effect |
| 6 | Access an unmapped address | Read returns 0; the next transaction's STATUS has BAD_CMD=1 |
| 7 | LEN in the command does not match the actual frame length | BAD_CMD=1, no side effects |
| 8 | Write transaction with CRC_M deliberately wrong by one bit | Registers unchanged; next STATUS has CRC_ERR=1; ERRCNT increments |
| 9 | Write ERRCNT | Clears to 0 |
| 10 | CS goes high in the middle of a transaction | State machine resets; the next transaction works |
| 11 | Back-to-back transactions (minimum CS gap) | No dropped words |

## Randomized tests

- Random address, length, INC, read/write and data, compared word by word against a simple software
  reference model.
- Randomly inject single-bit errors into a frame on MOSI; check that the error is detected and the write
  does not take effect.

## Timing tests

- Run with different SCLK-to-system-clock ratios to find where synchronization breaks.
- Repeat the tests with random phase offsets between SCLK and the system clock.

## Reference

- `host/spi16/sim.py` is a software model of the same protocol and can be used to generate test vectors,
  but the testbench itself and its comparison logic are yours to write.
