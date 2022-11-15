
`default_nettype none

module wb_fifo #(
    parameter ENABLE_VCD = 1
)(
    input  wire        clk_i    ,
    input  wire        rst_i    ,

    input  wire [31:0] wr_dat_i ,
    output wire [31:0] wr_dat_o ,
    input  wire [31:0] wr_adr_i ,
    input  wire [3:0]  wr_sel_i ,
    input  wire        wr_we_i  ,
    input  wire        wr_cyc_i ,
    input  wire        wr_stb_i ,
    output wire        wr_ack_o ,

    input  wire [31:0] rd_dat_i ,
    output wire [31:0] rd_dat_o ,
    input  wire [31:0] rd_adr_i ,
    input  wire [3:0]  rd_sel_i ,
    input  wire        rd_we_i  ,
    input  wire        rd_cyc_i ,
    input  wire        rd_stb_i ,
    output wire        rd_ack_o
);

    localparam FIFO_ADR_W = 10;

    localparam DW = 32;
    localparam AW = 32;

    localparam [2*AW-1:0] MUX_MATCH_ADDR = {
        {  4'b0, 4'b1, {(AW-8){1'b0}}  },
        {  4'b0, 4'b0, {(AW-8){1'b0}}  }
    };

    localparam [2*AW-1:0] MUX_MATCH_MASK = {
        {  4'b0, 4'b1, {(AW-8){1'b0}}  },
        {  4'b0, 4'b1, {(AW-8){1'b0}}  }
    };

    // ----------------------------------------------------------------
    // Write port MUX
    // ----------------------------------------------------------------
    //

    wire [1:0][DW-1:0]  wr_mux_dat_o ;
    wire [1:0]          wr_mux_we_o  ;
    wire [1:0]          wr_mux_cyc_o ;
    wire [1:0]          wr_mux_stb_o ;
    wire [1:0][DW-1:0]  wr_mux_dat_i ;
    wire [1:0]          wr_mux_ack_i ;

    wb_mux #(
        .dw         ( DW ),
        .aw         ( AW ),
        .num_slaves ( 2  ),
        .MATCH_ADDR ( MUX_MATCH_ADDR ),
        .MATCH_MASK ( MUX_MATCH_MASK )
    ) wr_mux (
        .wb_clk_i  ( clk_i     ) ,
        .wb_rst_i  ( rst_i     ) ,
        // Master interface
        .wbm_adr_i ( wr_adr_i ) ,
        .wbm_dat_i ( wr_dat_i ) ,
        .wbm_sel_i ( wr_sel_i ) ,
        .wbm_we_i  ( wr_we_i  ) ,
        .wbm_cyc_i ( wr_cyc_i ) ,
        .wbm_stb_i ( wr_stb_i ) ,
        .wbm_dat_o ( wr_dat_o ) ,
        .wbm_ack_o ( wr_ack_o ) ,
        .wbm_cti_i ( '0       ) ,
        .wbm_bte_i ( '0       ) ,
        .wbm_err_o (          ) ,
        .wbm_rty_o (          ) ,
        // Slave interfaces
        .wbs_adr_o (              ) ,
        .wbs_dat_o ( wr_mux_dat_o ) ,
        .wbs_sel_o (              ) ,
        .wbs_we_o  ( wr_mux_we_o  ) ,
        .wbs_cyc_o ( wr_mux_cyc_o ) ,
        .wbs_stb_o ( wr_mux_stb_o ) ,
        .wbs_dat_i ( wr_mux_dat_i ) ,
        .wbs_ack_i ( wr_mux_ack_i ) ,
        .wbs_cti_o (              ) ,
        .wbs_bte_o (              ) ,
        .wbs_err_i ( '0           ) ,
        .wbs_rty_i ( '0           )
    );

    // ----------------------------------------------------------------
    // Read port MUX
    // ----------------------------------------------------------------
    //

    wire [1:0]          rd_mux_cyc_o ;
    wire [1:0]          rd_mux_stb_o ;
    wire [1:0][DW-1:0]  rd_mux_dat_i ;
    wire [1:0]          rd_mux_ack_i ;

    wb_mux #(
        .dw         ( DW ),
        .aw         ( AW ),
        .num_slaves ( 2  ),
        .MATCH_ADDR ( MUX_MATCH_ADDR ),
        .MATCH_MASK ( MUX_MATCH_MASK )
    ) rd_mux (
        .wb_clk_i  ( clk_i     ) ,
        .wb_rst_i  ( rst_i     ) ,
        // Master interface
        .wbm_adr_i ( rd_adr_i ) ,
        .wbm_dat_i ( rd_dat_i ) ,
        .wbm_sel_i ( rd_sel_i ) ,
        .wbm_we_i  ( rd_we_i  ) ,
        .wbm_cyc_i ( rd_cyc_i ) ,
        .wbm_stb_i ( rd_stb_i ) ,
        .wbm_dat_o ( rd_dat_o ) ,
        .wbm_ack_o ( rd_ack_o ) ,
        .wbm_cti_i ( '0       ) ,
        .wbm_bte_i ( '0       ) ,
        .wbm_err_o (          ) ,
        .wbm_rty_o (          ) ,
        // Slave interfaces
        .wbs_adr_o (              ) ,
        .wbs_dat_o (              ) ,
        .wbs_sel_o (              ) ,
        .wbs_we_o  (              ) ,
        .wbs_cyc_o ( rd_mux_cyc_o ) ,
        .wbs_stb_o ( rd_mux_stb_o ) ,
        .wbs_dat_i ( rd_mux_dat_i ) ,
        .wbs_ack_i ( rd_mux_ack_i ) ,
        .wbs_cti_o (              ) ,
        .wbs_bte_o (              ) ,
        .wbs_err_i ( '0           ) ,
        .wbs_rty_i ( '0           )
    );

    // ----------------------------------------------------------------
    // FIFO
    // ----------------------------------------------------------------
    //

    wb_32bit_sfifo #(.ADR_W (FIFO_ADR_W)) fifo (
        .clk_i ,
        .rst_i ,

        .wr_wbd_dat_i ( wr_mux_dat_o[0] ) ,
        .wr_wbd_we_i  ( wr_mux_we_o [0] ) ,
        .wr_wbd_cyc_i ( wr_mux_cyc_o[0] ) ,
        .wr_wbd_stb_i ( wr_mux_stb_o[0] ) ,
        .wr_wbd_ack_o ( wr_mux_ack_i[0] ) ,

        .wr_wbs_cyc_i ( wr_mux_cyc_o[1] ),
        .wr_wbs_stb_i ( wr_mux_stb_o[1] ),
        .wr_wbs_ack_o ( wr_mux_ack_i[1] ),
        .wr_wbs_dat_o ( wr_mux_dat_i[1] ),

        .rd_wbd_cyc_i ( rd_mux_cyc_o[0] ),
        .rd_wbd_stb_i ( rd_mux_stb_o[0] ),
        .rd_wbd_ack_o ( rd_mux_ack_i[0] ),
        .rd_wbd_dat_o ( rd_mux_dat_i[0] ),

        .rd_wbs_cyc_i ( rd_mux_cyc_o[1] ),
        .rd_wbs_stb_i ( rd_mux_stb_o[1] ),
        .rd_wbs_ack_o ( rd_mux_ack_i[1] ),
        .rd_wbs_dat_o ( rd_mux_dat_i[1] )
    );

    // ----------------------------------------------------------------
    // VCD dump
    // ----------------------------------------------------------------
    //

    initial if (ENABLE_VCD) begin
        $dumpfile("wb_fifo.vcd");
        $dumpvars(0, wb_fifo);
    end

endmodule