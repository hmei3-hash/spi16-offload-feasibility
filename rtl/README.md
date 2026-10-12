# rtl/

This directory holds only the skeleton `spi16_slave.v`. The implementation is yours to write; the spec is
in [`../docs/PROTOCOL.md`](../docs/PROTOCOL.md).

## Suggested module breakdown

| Module | Responsibility |
|---|---|
| `spi_rx_tx` | Synchronize external signals, bit/word counting, shift in/out |
| `frame_fsm` | Frame states: CMD, GAP, DATA, CRC; reset on the CS rising edge |
| `crc16` | CRC-16/CCITT-FALSE, updated per bit or per word |
| `regfile` | ID, VERSION, SCRATCH, ERRCNT, TXNCNT, TESTMEM |
| `top` | Instantiate the above, handle the MISO tri-state and pin constraints |

## Questions to answer before designing

1. Does the whole logic run in the SCLK domain, or only the shifting while the rest runs in the system
   clock domain? What does each choice cost in clock-domain crossings?
2. How much faster than SCLK must the system clock be for a two-flop synchronizer to be safe?
3. Should TESTMEM be a BRAM or distributed RAM? How many cycles of read latency does it add, and does it
   fit inside the GAP word?
4. Where is the write data buffered, and is 64 words enough? In which clock domain does the commit happen?
5. Should the CRC update bit-serially or one word at a time? What is the resource/timing trade-off?

## Common pitfalls

- The first MISO bit must be valid before the first rising edge of SCLK.
- If CS goes high early and cuts a frame short, the state machine and the CRC accumulator must recover.
- ISE's XST has limited SystemVerilog support; avoid `logic`, `always_ff` and the like.
- Pin constraints (`.ucf`) and I/O voltage must come from the board schematic; do not assume a direct
  connection to the Pi is safe.
