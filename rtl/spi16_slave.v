// SPI16 slave — 骨架（只有端口和说明，没有实现）
//
// 实现依据：docs/PROTOCOL.md
// 工具链：Xilinx ISE（Spartan-6），请写 Verilog-2001。
//
// 你要完成的部分（建议按这个顺序）：
//   1. 同步 cs_n / sclk / mosi 到所需的时钟域
//   2. 位计数、字计数、帧状态机（CS 上升沿无条件复位）
//   3. 移位寄存器接收 CMD，解析 W / INC / LEN / ADDR
//   4. 寄存器表（ID、VERSION、SCRATCH、ERRCNT、TXNCNT、TESTMEM）
//   5. CRC-16/CCITT-FALSE 的接收端校验和发送端生成
//   6. 写数据暂存，事务末尾 CRC 通过后再提交
//   7. MISO 发送：STATUS_PREV、ECHO、读数据、CRC_S
//
// 端口只是建议，可按你的顶层设计调整。

module spi16_slave #(
    parameter ADDR_W  = 8,    // 寄存器地址位宽
    parameter MAX_LEN = 64    // 单次事务最大负载字数
)(
    input  wire clk,          // 系统时钟
    input  wire rst_n,        // 低有效复位

    input  wire sclk,         // SPI 时钟（来自主机，异步）
    input  wire cs_n,         // 片选，低有效
    input  wire mosi,
    output wire miso,         // 高阻处理请放在顶层 IOBUF

    output wire drdy          // 可选：数据就绪 / 中断
);

    // TODO: 实现。下面两行只是让骨架能通过综合，请在写真实逻辑时删除。
    assign miso = 1'b0;
    assign drdy = 1'b0;

endmodule
