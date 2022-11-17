
`default_nettype none

`timescale 1ns/1ns

module tb_top (
    // WISHBONE slave
    input  wire [31:0] wb_dat_i ,
    output wire [31:0] wb_dat_o ,
    input  wire [31:0] wb_adr_i ,
    input  wire [3:0]  wb_sel_i ,
    input  wire        wb_we_i  ,
    input  wire        wb_cyc_i ,
    input  wire        wb_stb_i ,
    output wire        wb_ack_o ,

    // IRQ
    output wire        sd_dat_irq_o ,
    output wire        sd_cmd_irq_o
);

    // ----------------------------------------------------------------
    // VCD dump
    // ----------------------------------------------------------------
    //

    initial begin
        $dumpfile("tb_top.vcd");
        $dumpvars(0, tb_top);
    end

    // ----------------------------------------------------------------
    // Clock & Reset
    // ----------------------------------------------------------------
    //

    int unsigned T_CLK_NS    = 20ns;
    int unsigned T_SD_CLK_SRC_NS = 10ns;

    logic wb_clk = 1'b0;
    logic sd_clk_src = 1'b0;

    always  #((T_CLK_NS / 2) * 1ns) wb_clk <= ~wb_clk;

    initial begin
        #($urandom_range(1, T_CLK_NS) * 1ns);
        forever begin
            #((T_SD_CLK_SRC_NS / 2) * 1ns)
            sd_clk_src <= ~sd_clk_src;
        end
    end

    logic wb_rst_raw = 1'b0;
    logic wb_rst = 1'b1;

    initial #(100 * T_CLK_NS) wb_rst = 1'b0;

    // ----------------------------------------------------------------
    // Wishbone slave MUX
    // ----------------------------------------------------------------
    //

    localparam DW = 32;
    localparam AW = 32;
    localparam SLV_N = 3;

    // Slave IDs
    localparam WB_SDC_ID   = 0;
    localparam WB_FIFO0_ID = 1;
    localparam WB_FIFO1_ID = 2;

    localparam [SLV_N*AW-1:0] MUX_MATCH_ADDR = {
        {  2'd2, {(AW-2){1'b0}}  },
        {  2'd1, {(AW-2){1'b0}}  },
        {  2'd0, {(AW-2){1'b0}}  }
    };

    localparam [SLV_N*AW-1:0] MUX_MATCH_MASK = {
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd3, {(AW-2){1'b0}}  }
    };

    // Wishbone Slave interface
    wire [SLV_N-1:0][AW-1:0]  wbs_adr_o ;
    wire [SLV_N-1:0][DW-1:0]  wbs_dat_o ;
    wire [SLV_N-1:0][4-1:0]   wbs_sel_o ;
    wire [SLV_N-1:0]          wbs_we_o  ;
    wire [SLV_N-1:0]          wbs_cyc_o ;
    wire [SLV_N-1:0]          wbs_stb_o ;
    wire [SLV_N-1:0][DW-1:0]  wbs_dat_i ;
    wire [SLV_N-1:0]          wbs_ack_i ;

    wb_mux #(
        .dw         ( DW             ),
        .aw         ( AW             ),
        .num_slaves ( SLV_N          ),
        .MATCH_ADDR ( MUX_MATCH_ADDR ),
        .MATCH_MASK ( MUX_MATCH_MASK )
    ) wb_mux (
        .wb_clk_i   ( wb_clk   ) ,
        .wb_rst_i   ( wb_rst   ) ,
        // Master interface
        .wbm_adr_i  ( wb_adr_i ) ,
        .wbm_dat_i  ( wb_dat_i ) ,
        .wbm_sel_i  ( wb_sel_i ) ,
        .wbm_we_i   ( wb_we_i  ) ,
        .wbm_cyc_i  ( wb_cyc_i ) ,
        .wbm_stb_i  ( wb_stb_i ) ,
        .wbm_dat_o  ( wb_dat_o ) ,
        .wbm_ack_o  ( wb_ack_o ) ,
        .wbm_cti_i  ( '0  ) ,
        .wbm_bte_i  ( '0  ) ,
        .wbm_err_o  (     ) ,
        .wbm_rty_o  (     ) ,
        // Slave interfaces
        .wbs_adr_o  ( wbs_adr_o ) ,
        .wbs_dat_o  ( wbs_dat_o ) ,
        .wbs_sel_o  ( wbs_sel_o ) ,
        .wbs_we_o   ( wbs_we_o  ) ,
        .wbs_cyc_o  ( wbs_cyc_o ) ,
        .wbs_stb_o  ( wbs_stb_o ) ,
        .wbs_dat_i  ( wbs_dat_i ) ,
        .wbs_ack_i  ( wbs_ack_i ) ,
        .wbs_cti_o  (    ) ,
        .wbs_bte_o  (    ) ,
        .wbs_err_i  ( '0 ) ,
        .wbs_rty_i  ( '0 )
    );


    // ----------------------------------------------------------------
    // SD controller instans
    // ----------------------------------------------------------------
    //

    // SD DMA Wishbone master
    wire [31:0] m_wb_dat_i ;
    wire [31:0] m_wb_dat_o ;
    wire [31:0] m_wb_adr_o ;
    wire [3:0]  m_wb_sel_o ;
    wire        m_wb_we_o  ;
    wire        m_wb_cyc_o ;
    wire        m_wb_stb_o ;
    wire        m_wb_ack_i ;
    wire  [2:0] m_wb_cti_o ;
    wire  [1:0] m_wb_bte_o ;

    wire        sd_cmd_dat_i ;
    wire        sd_cmd_out_o ;
    wire        sd_cmd_oe_o  ;

    wire  [3:0] sd_dat_dat_i ;
    wire  [3:0] sd_dat_out_o ;
    wire        sd_dat_oe_o  ;


    wire       sd_clk_o  ;
    tri1       sd_cmd_io ;
    tri1 [3:0] sd_dat_io ;

    sdc_controller sdc (
        // WISHBONE common
        .wb_clk_i (wb_clk) ,
        .wb_rst_i (wb_rst) ,

        // WISHBONE slave
        .wb_dat_i  ( wbs_dat_o[WB_SDC_ID] ) ,
        .wb_dat_o  ( wbs_dat_i[WB_SDC_ID] ) ,
        .wb_adr_i  ( wbs_adr_o[WB_SDC_ID][7:0] ) ,
        .wb_sel_i  ( wbs_sel_o[WB_SDC_ID] ) ,
        .wb_we_i   ( wbs_we_o [WB_SDC_ID] ) ,
        .wb_cyc_i  ( wbs_cyc_o[WB_SDC_ID] ) ,
        .wb_stb_i  ( wbs_stb_o[WB_SDC_ID] ) ,
        .wb_ack_o  ( wbs_ack_i[WB_SDC_ID] ) ,

        // WISHBONE master
        .m_wb_dat_o    ,
        .m_wb_dat_i    ,
        .m_wb_adr_o    ,
        .m_wb_sel_o    ,
        .m_wb_we_o     ,
        .m_wb_cyc_o    ,
        .m_wb_stb_o    ,
        .m_wb_ack_i    ,
        .m_wb_cti_o    ,
        .m_wb_bte_o    ,
        .sd_clk_i_pad (sd_clk_src),
        .sd_clk_o_pad (sd_clk_o),

        // SD Command interface - not used
        .sd_cmd_dat_i ,
        .sd_cmd_out_o ,
        .sd_cmd_oe_o  ,
        .int_cmd      ( sd_cmd_irq_o ),

        // SD Data interface
        .sd_dat_dat_i ,
        .sd_dat_out_o ,
        .sd_dat_oe_o  ,
        .int_data     ( sd_dat_irq_o )
    );

    // ----------------------------------------------------------------
    // SD Card model
    // ----------------------------------------------------------------
    //

    localparam SD_MODEL_LOG_NAME = "sd_model_log.txt";

    sdModel #(
        .log_file(SD_MODEL_LOG_NAME)
    ) sd_model (
        .sdClk ( sd_clk_o  ),
        .cmd   ( sd_cmd_io ),
        .dat   ( sd_dat_io )
    );

    assign sd_cmd_io = sd_cmd_oe_o ? sd_cmd_out_o : 'z;
    assign sd_cmd_dat_i = sd_cmd_io;

    assign sd_dat_io = sd_dat_oe_o ? sd_dat_out_o : 'z;
    assign sd_dat_dat_i = sd_dat_io;

    // ----------------------------------------------------------------
    // SDC DMA Wishbone MUX
    // ----------------------------------------------------------------
    //

    localparam DMA_SLV_N = 4;

    // Slave IDs
    localparam DMA_WB_RAM0_ID  = 0;
    localparam DMA_WB_RAM1_ID  = 1;
    localparam DMA_WB_FIFO0_ID = 2;
    localparam DMA_WB_FIFO1_ID = 3;

    localparam [DMA_SLV_N*AW-1:0] DMA_MUX_MATCH_ADDR = {
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd2, {(AW-2){1'b0}}  },
        {  2'd1, {(AW-2){1'b0}}  },
        {  2'd0, {(AW-2){1'b0}}  }
    };

    localparam [DMA_SLV_N*AW-1:0] DMA_MUX_MATCH_MASK = {
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd3, {(AW-2){1'b0}}  },
        {  2'd3, {(AW-2){1'b0}}  }
    };

    // Wishbone Slave interface
    wire [DMA_SLV_N-1:0][AW-1:0]  wbs_dma_adr_o ;
    wire [DMA_SLV_N-1:0][DW-1:0]  wbs_dma_dat_o ;
    wire [DMA_SLV_N-1:0][4-1:0]   wbs_dma_sel_o ;
    wire [DMA_SLV_N-1:0]          wbs_dma_we_o  ;
    wire [DMA_SLV_N-1:0]          wbs_dma_cyc_o ;
    wire [DMA_SLV_N-1:0]          wbs_dma_stb_o ;
    wire [DMA_SLV_N-1:0][DW-1:0]  wbs_dma_dat_i ;
    wire [DMA_SLV_N-1:0]          wbs_dma_ack_i ;
    wire [DMA_SLV_N-1:0][2:0]     wbs_dma_cti_o ;
    wire [DMA_SLV_N-1:0][1:0]     wbs_dma_bte_o ;

    wb_mux #(
        .dw         ( DW                 ),
        .aw         ( AW                 ),
        .num_slaves ( DMA_SLV_N          ),
        .MATCH_ADDR ( DMA_MUX_MATCH_ADDR ),
        .MATCH_MASK ( DMA_MUX_MATCH_MASK )
    ) dma_mux (
        .wb_clk_i   ( wb_clk     ) ,
        .wb_rst_i   ( wb_rst     ) ,
        // Master interface
        .wbm_adr_i  ( m_wb_adr_o ) ,
        .wbm_dat_i  ( m_wb_dat_o ) ,
        .wbm_sel_i  ( m_wb_sel_o ) ,
        .wbm_we_i   ( m_wb_we_o  ) ,
        .wbm_cyc_i  ( m_wb_cyc_o ) ,
        .wbm_stb_i  ( m_wb_stb_o ) ,
        .wbm_dat_o  ( m_wb_dat_i ) ,
        .wbm_ack_o  ( m_wb_ack_i ) ,
        .wbm_cti_i  ( m_wb_cti_o ) ,
        .wbm_bte_i  ( m_wb_bte_o ) ,
        .wbm_err_o  (            ) ,
        .wbm_rty_o  (            ) ,
        // Slave interfaces
        .wbs_adr_o  ( wbs_dma_adr_o ) ,
        .wbs_dat_o  ( wbs_dma_dat_o ) ,
        .wbs_sel_o  ( wbs_dma_sel_o ) ,
        .wbs_we_o   ( wbs_dma_we_o  ) ,
        .wbs_cyc_o  ( wbs_dma_cyc_o ) ,
        .wbs_stb_o  ( wbs_dma_stb_o ) ,
        .wbs_dat_i  ( wbs_dma_dat_i ) ,
        .wbs_ack_i  ( wbs_dma_ack_i ) ,
        .wbs_cti_o  ( wbs_dma_cti_o ) ,
        .wbs_bte_o  ( wbs_dma_bte_o ) ,
        .wbs_err_i ( '0          ) ,
        .wbs_rty_i ( '0          )
    );

    // ----------------------------------------------------------------
    // WB RAM 0
    // ----------------------------------------------------------------
    //

    localparam WB_RAM0_DEPTH = 16 * 1024;
    localparam WB_RAM0_AW = $clog2(WB_RAM0_DEPTH);

    wb_ram #(
        .dw    (DW),
        .depth (WB_RAM0_DEPTH),
        .aw    (WB_RAM0_AW)
    ) ram0 (
     	.wb_clk_i ( wb_clk ),
      	.wb_rst_i ( wb_rst ),

        .wb_adr_i ( wbs_dma_adr_o [DMA_WB_RAM0_ID][WB_RAM0_AW-1:0] ),
        .wb_dat_i ( wbs_dma_dat_o [DMA_WB_RAM0_ID] ),
        .wb_sel_i ( wbs_dma_sel_o [DMA_WB_RAM0_ID] ),
     	.wb_we_i  ( wbs_dma_we_o  [DMA_WB_RAM0_ID] ),
        .wb_bte_i ( wbs_dma_bte_o [DMA_WB_RAM0_ID] ),
        .wb_cti_i ( wbs_dma_cti_o [DMA_WB_RAM0_ID] ),
        .wb_cyc_i ( wbs_dma_cyc_o [DMA_WB_RAM0_ID] ),
        .wb_stb_i ( wbs_dma_stb_o [DMA_WB_RAM0_ID] ),
        .wb_ack_o ( wbs_dma_ack_i [DMA_WB_RAM0_ID] ),
        .wb_dat_o ( wbs_dma_dat_i [DMA_WB_RAM0_ID] ),
        .wb_err_o ()
    );

    // ----------------------------------------------------------------
    // WB RAM 1
    // ----------------------------------------------------------------
    //

    localparam WB_RAM1_DEPTH = 16 * 1024;
    localparam WB_RAM1_AW = $clog2(WB_RAM0_DEPTH);

    wb_ram #(
        .dw    (DW),
        .depth (WB_RAM1_DEPTH),
        .aw    (WB_RAM1_AW)
    ) ram1 (
     	.wb_clk_i ( wb_clk ),
      	.wb_rst_i ( wb_rst ),

        .wb_adr_i ( wbs_dma_adr_o [DMA_WB_RAM1_ID][WB_RAM0_AW-1:0] ),
        .wb_dat_i ( wbs_dma_dat_o [DMA_WB_RAM1_ID] ),
        .wb_sel_i ( wbs_dma_sel_o [DMA_WB_RAM1_ID] ),
     	.wb_we_i  ( wbs_dma_we_o  [DMA_WB_RAM1_ID] ),
        .wb_bte_i ( wbs_dma_bte_o [DMA_WB_RAM1_ID] ),
        .wb_cti_i ( wbs_dma_cti_o [DMA_WB_RAM1_ID] ),
        .wb_cyc_i ( wbs_dma_cyc_o [DMA_WB_RAM1_ID] ),
        .wb_stb_i ( wbs_dma_stb_o [DMA_WB_RAM1_ID] ),
        .wb_ack_o ( wbs_dma_ack_i [DMA_WB_RAM1_ID] ),
        .wb_dat_o ( wbs_dma_dat_i [DMA_WB_RAM1_ID] ),
        .wb_err_o ()
    );

    // ----------------------------------------------------------------
    // WB FIFO 0, write from SDC to FIFO
    // ----------------------------------------------------------------
    //

    wb_fifo #(.ENABLE_VCD(0)) fifo0 (
        .clk_i    ( wb_clk ) ,
        .rst_i    ( wb_rst ) ,

        .wr_dat_i ( wbs_dma_dat_o [DMA_WB_FIFO0_ID] ),
        .wr_dat_o ( wbs_dma_dat_i [DMA_WB_FIFO0_ID] ),
        .wr_adr_i ( wbs_dma_adr_o [DMA_WB_FIFO0_ID] ),
        .wr_sel_i ( wbs_dma_sel_o [DMA_WB_FIFO0_ID] ),
        .wr_we_i  ( wbs_dma_we_o  [DMA_WB_FIFO0_ID] ),
        .wr_cyc_i ( wbs_dma_cyc_o [DMA_WB_FIFO0_ID] ),
        .wr_stb_i ( wbs_dma_stb_o [DMA_WB_FIFO0_ID] ),
        .wr_ack_o ( wbs_dma_ack_i [DMA_WB_FIFO0_ID] ),

        .rd_dat_i ( wbs_dat_o [WB_FIFO0_ID] ),
        .rd_dat_o ( wbs_dat_i [WB_FIFO0_ID] ),
        .rd_adr_i ( wbs_adr_o [WB_FIFO0_ID] ),
        .rd_sel_i ( wbs_sel_o [WB_FIFO0_ID] ),
        .rd_we_i  ( wbs_we_o  [WB_FIFO0_ID] ),
        .rd_cyc_i ( wbs_cyc_o [WB_FIFO0_ID] ),
        .rd_stb_i ( wbs_stb_o [WB_FIFO0_ID] ),
        .rd_ack_o ( wbs_ack_i [WB_FIFO0_ID] )
    );

    // ----------------------------------------------------------------
    // WB FIFO 1, read from SDC to FIFO
    // ----------------------------------------------------------------
    //

    wb_fifo #(.ENABLE_VCD(0)) fifo1 (
        .clk_i    ( wb_clk ) ,
        .rst_i    ( wb_rst ) ,

        .wr_dat_i ( wbs_dat_o [WB_FIFO1_ID] ),
        .wr_dat_o ( wbs_dat_i [WB_FIFO1_ID] ),
        .wr_adr_i ( wbs_adr_o [WB_FIFO1_ID] ),
        .wr_sel_i ( wbs_sel_o [WB_FIFO1_ID] ),
        .wr_we_i  ( wbs_we_o  [WB_FIFO1_ID] ),
        .wr_cyc_i ( wbs_cyc_o [WB_FIFO1_ID] ),
        .wr_stb_i ( wbs_stb_o [WB_FIFO1_ID] ),
        .wr_ack_o ( wbs_ack_i [WB_FIFO1_ID] ),

        .rd_dat_o ( wbs_dma_dat_i [DMA_WB_FIFO1_ID] ),
        .rd_dat_i ( wbs_dma_dat_o [DMA_WB_FIFO1_ID] ),
        .rd_adr_i ( wbs_dma_adr_o [DMA_WB_FIFO1_ID] ),
        .rd_sel_i ( wbs_dma_sel_o [DMA_WB_FIFO1_ID] ),
        .rd_we_i  ( wbs_dma_we_o  [DMA_WB_FIFO1_ID] ),
        .rd_cyc_i ( wbs_dma_cyc_o [DMA_WB_FIFO1_ID] ),
        .rd_stb_i ( wbs_dma_stb_o [DMA_WB_FIFO1_ID] ),
        .rd_ack_o ( wbs_dma_ack_i [DMA_WB_FIFO1_ID] )
    );

endmodule

`resetall
