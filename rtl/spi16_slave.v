// SPI16 slave -- skeleton (ports and notes only, no implementation)
//
// Reference: docs/PROTOCOL.md
// Toolchain: Xilinx ISE (Spartan-6); write Verilog-2001.
//
// What you need to implement (suggested order):
//   1. Synchronize cs_n / sclk / mosi into the clock domain(s) you choose
//   2. Bit counter, word counter, frame state machine (CS rising edge resets unconditionally)
//   3. Shift register that receives CMD and decodes W / INC / LEN / ADDR
//   4. Register map (ID, VERSION, SCRATCH, ERRCNT, TXNCNT, TESTMEM)
//   5. CRC-16/CCITT-FALSE: receive-side check and transmit-side generation
//   6. Buffer write data; commit only at the end of the transaction, after the CRC passes
//   7. MISO transmit: STATUS_PREV, ECHO, read data, CRC_S
//
// The ports are only a suggestion; adapt them to your top-level design.

module spi16_slave #(
    parameter ADDR_W  = 8,    // register address width
    parameter MAX_LEN = 64    // maximum payload words per transaction
)(
    input  wire clk,          // system clock
    input  wire rst_n,        // active-low reset

    input  wire sclk,         // SPI clock (from the host, asynchronous)
    input  wire cs_n,         // chip select, active low
    input  wire mosi,
    output wire miso,         // put the high-impedance handling in a top-level IOBUF

    output wire drdy          // optional: data ready / interrupt
);

    // TODO: implement. The two lines below only let the skeleton synthesize;
    // delete them when you write the real logic.
    assign miso = 1'b0;
    assign drdy = 1'b0;

endmodule
