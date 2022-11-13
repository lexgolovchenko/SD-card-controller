
`default_nettype none

module tb_top (
    // WISHBONE slave
    input  wire [31:0] wb_dat_i ,
    output wire [31:0] wb_dat_o ,
    input  wire [7:0]  wb_adr_i ,
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

    localparam time T_CLK_NS = 10ns;

    logic wb_clk = 1'b0;
    logic wb_rst = 1'b1;

    always  #(T_CLK_NS / 2) wb_clk = ~wb_clk;
    initial #(100 * T_CLK_NS) wb_rst = 1'b0;

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
        .wb_dat_i ,
        .wb_dat_o ,
        .wb_adr_i ,
        .wb_sel_i ,
        .wb_we_i  ,
        .wb_cyc_i ,
        .wb_stb_i ,
        .wb_ack_o ,

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

        .sd_clk_i_pad (wb_clk),
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
    // Wishbone MUX
    // ----------------------------------------------------------------
    //

    localparam DW = 32;
    localparam AW = 32;
    localparam SLV_N = 2;

    // Slave IDs
    localparam WB_RAM0_ID  = 0;
    localparam WB_RAM1_ID  = 1;
    localparam WB_FIFO0_ID = 2;
    localparam WB_FIFO1_ID = 3;

    localparam [SLV_N*AW-1:0] MUX_MATCH_ADDR = {
        {  1'b1, {(AW-1){1'b0}}  },
        {  1'b0, {(AW-1){1'b0}}  }
    };

    localparam [SLV_N*AW-1:0] MUX_MATCH_MASK = {
        {  1'b1, {(AW-1){1'b0}}  },
        {  1'b1, {(AW-1){1'b0}}  }
    };

    wire [SLV_N-1:0][AW-1:0] mux_base_addr_export;
    assign mux_base_addr_export = MUX_MATCH_ADDR;

    // Wishbone Slave interface
    wire [SLV_N-1:0][AW-1:0]  wbs_adr_o ;
    wire [SLV_N-1:0][DW-1:0]  wbs_dat_o ;
    wire [SLV_N-1:0][4-1:0]   wbs_sel_o ;
    wire [SLV_N-1:0]          wbs_we_o  ;
    wire [SLV_N-1:0]          wbs_cyc_o ;
    wire [SLV_N-1:0]          wbs_stb_o ;
    wire [SLV_N-1:0][DW-1:0]  wbs_dat_i ;
    wire [SLV_N-1:0]          wbs_ack_i ;
    wire [SLV_N-1:0][2:0]     wbs_cti_o ;
    wire [SLV_N-1:0][1:0]     wbs_bte_o ;

    wb_mux #(
        .dw         ( DW             ),
        .aw         ( AW             ),
        .num_slaves ( SLV_N          ),
        .MATCH_ADDR ( MUX_MATCH_ADDR ),
        .MATCH_MASK ( MUX_MATCH_MASK )
    ) mux (
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
        .wbs_adr_o                 ,
        .wbs_dat_o                 ,
        .wbs_sel_o                 ,
        .wbs_we_o                  ,
        .wbs_cyc_o                 ,
        .wbs_stb_o                 ,
        .wbs_dat_i                 ,
        .wbs_ack_i                 ,
        .wbs_cti_o                 ,
        .wbs_bte_o                 ,
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

        .wb_adr_i ( wbs_adr_o [WB_RAM0_ID][WB_RAM0_AW-1:0] ),
        .wb_dat_i ( wbs_dat_o [WB_RAM0_ID] ),
        .wb_sel_i ( wbs_sel_o [WB_RAM0_ID] ),
     	.wb_we_i  ( wbs_we_o  [WB_RAM0_ID] ),
        .wb_bte_i ( wbs_bte_o [WB_RAM0_ID] ),
        .wb_cti_i ( wbs_cti_o [WB_RAM0_ID] ),
        .wb_cyc_i ( wbs_cyc_o [WB_RAM0_ID] ),
        .wb_stb_i ( wbs_stb_o [WB_RAM0_ID] ),
        .wb_ack_o ( wbs_ack_i [WB_RAM0_ID] ),
        .wb_dat_o ( wbs_dat_i [WB_RAM0_ID] ),
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

        .wb_adr_i ( wbs_adr_o [WB_RAM1_ID][WB_RAM0_AW-1:0] ),
        .wb_dat_i ( wbs_dat_o [WB_RAM1_ID] ),
        .wb_sel_i ( wbs_sel_o [WB_RAM1_ID] ),
     	.wb_we_i  ( wbs_we_o  [WB_RAM1_ID] ),
        .wb_bte_i ( wbs_bte_o [WB_RAM1_ID] ),
        .wb_cti_i ( wbs_cti_o [WB_RAM1_ID] ),
        .wb_cyc_i ( wbs_cyc_o [WB_RAM1_ID] ),
        .wb_stb_i ( wbs_stb_o [WB_RAM1_ID] ),
        .wb_ack_o ( wbs_ack_i [WB_RAM1_ID] ),
        .wb_dat_o ( wbs_dat_i [WB_RAM1_ID] ),
        .wb_err_o ()
    );

endmodule

`resetall
