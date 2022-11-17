//////////////////////////////////////////////////////////////////////
////                                                              ////
//// WISHBONE SD Card Controller IP Core                          ////
////                                                              ////
//// sd_fifo_filler.v                                             ////
////                                                              ////
//// This file is part of the WISHBONE SD Card                    ////
//// Controller IP Core project                                   ////
//// http://opencores.org/project,sd_card_controller              ////
////                                                              ////
//// Description                                                  ////
//// Fifo interface between sd card and wishbone clock domains    ////
//// and DMA engine eble to write/read to/from CPU memory         ////
////                                                              ////
//// Author(s):                                                   ////
////     - Marek Czerski, ma.czerski@gmail.com                    ////
////                                                              ////
//////////////////////////////////////////////////////////////////////
////                                                              ////
//// Copyright (C) 2013 Authors                                   ////
////                                                              ////
//// Based on original work by                                    ////
////     Adam Edvardsson (adam.edvardsson@orsoc.se)               ////
////                                                              ////
////     Copyright (C) 2009 Authors                               ////
////                                                              ////
//// This source file may be used and distributed without         ////
//// restriction provided that this copyright statement is not    ////
//// removed from the file and that any derivative work contains  ////
//// the original copyright notice and the associated disclaimer. ////
////                                                              ////
//// This source file is free software; you can redistribute it   ////
//// and/or modify it under the terms of the GNU Lesser General   ////
//// Public License as published by the Free Software Foundation; ////
//// either version 2.1 of the License, or (at your option) any   ////
//// later version.                                               ////
////                                                              ////
//// This source is distributed in the hope that it will be       ////
//// useful, but WITHOUT ANY WARRANTY; without even the implied   ////
//// warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR      ////
//// PURPOSE. See the GNU Lesser General Public License for more  ////
//// details.                                                     ////
////                                                              ////
//// You should have received a copy of the GNU Lesser General    ////
//// Public License along with this source; if not, download it   ////
//// from http://www.opencores.org/lgpl.shtml                     ////
////                                                              ////
//////////////////////////////////////////////////////////////////////

`include "sd_defines.h"

module sd_fifo_filler(
           input wb_clk,
           input rst,
           //WB Signals
           output reg [31:0] wbm_adr_o,
           output wbm_we_o,
           output [31:0] wbm_dat_o,
           input [31:0] wbm_dat_i,
           output wbm_cyc_o,
           output wbm_stb_o,
           input wbm_ack_i,
           //Data Master Control signals
           input en_rx_i,
           input en_tx_i,
           input [31:0] adr_i,
           //Data Serial signals
           input sd_clk,
           input [31:0] dat_i,
           output [31:0] dat_o,
           input wr_i,
           input rd_i,
           output sd_full_o,
           output sd_empty_o,
           output wb_full_o,
           output wb_empty_o,

           input start_tx_i,
           input start_rx_i,

           input [`BLKSIZE_W+`BLKCNT_W-1:0] xfersize_i,

           output wire wb_finish_o
);

//
// Data transfer counter
//

localparam WB_CNT_W = (`BLKSIZE_W+`BLKCNT_W);

reg [`BLKSIZE_W+`BLKCNT_W-1:0] wb_cnt;
wire wb_ena;
wire wb_cnt_start;

assign wb_cnt_start = start_tx_i || start_rx_i;

always @(posedge wb_clk or posedge rst) begin
    if (rst)
        wb_cnt <= {WB_CNT_W{1'b0}};
    else begin
        if (wb_cnt_start)
            wb_cnt <= (xfersize_i >> 2);
        else if (wbm_ack_i && (|wb_cnt))
            wb_cnt <= wb_cnt - 1'b1;
    end
end

assign wb_ena = (|wb_cnt);
assign wb_finish_o = !(|wb_cnt);

`define FIFO_MEM_ADR_SIZE 4
`define MEM_OFFSET 4

wire reset_fifo;
wire fifo_rd;
reg fifo_rd_ack;
reg fifo_rd_reg;

assign fifo_rd = wbm_cyc_o & wbm_ack_i;
// assign reset_fifo = !en_rx_i & !en_tx_i;
assign reset_fifo = start_tx_i || start_rx_i;

assign wbm_we_o  = (en_rx_i & !wb_empty_o);
assign wbm_cyc_o = wb_ena & (en_rx_i ? en_rx_i & !wb_empty_o : en_tx_i & !wb_full_o);
assign wbm_stb_o = wb_ena & (en_rx_i ? wbm_cyc_o & fifo_rd_ack : wbm_cyc_o);

generic_fifo_dc_gray #(
    .dw(32),
    .aw(`FIFO_MEM_ADR_SIZE)
    ) generic_fifo_dc_gray0 (
    .rd_clk(wb_clk),
    .wr_clk(sd_clk),
    .rst(!(rst | reset_fifo)),
    .clr(1'b0),
    .din(dat_i),
    .we(wr_i),
    .dout(wbm_dat_o),
    .re(en_rx_i & wbm_cyc_o & wbm_ack_i),
    .full(sd_full_o),
    .empty(wb_empty_o),
    .wr_level(),
    .rd_level()
    );

generic_fifo_dc_gray #(
    .dw(32),
    .aw(`FIFO_MEM_ADR_SIZE)
    ) generic_fifo_dc_gray1 (
    .rd_clk(sd_clk),
    .wr_clk(wb_clk),
    .rst(!(rst | reset_fifo)),
    .clr(1'b0),
    .din(wbm_dat_i),
    .we(en_tx_i & wbm_cyc_o & wbm_stb_o & wbm_ack_i),
    .dout(dat_o),
    .re(rd_i),
    .full(wb_full_o),
    .empty(sd_empty_o),
    .wr_level(),
    .rd_level()
    );

always @(posedge wb_clk or posedge rst)
    if (rst) begin
        wbm_adr_o <= 0;
        fifo_rd_reg <= 0;
        fifo_rd_ack <= 1;
    end
    else begin
        fifo_rd_reg <= fifo_rd;
        fifo_rd_ack <= fifo_rd_reg | !fifo_rd;
        if (wbm_cyc_o & wbm_stb_o & wbm_ack_i)
            wbm_adr_o <= wbm_adr_o + `MEM_OFFSET;
        else if (reset_fifo)
            wbm_adr_o <= adr_i;
    end

endmodule


