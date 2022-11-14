
`default_nettype none

module wb_32bit_sfifo #(
    parameter ADR_W
)(
    input  wire            clk_i         ,
    input  wire            rst_i         ,

    // Write data
    input  wire  [31:0]    wr_wbd_dat_i  ,
    input  wire            wr_wbd_we_i   ,
    input  wire            wr_wbd_cyc_i  ,
    input  wire            wr_wbd_stb_i  ,
    output logic           wr_wbd_ack_o  ,
    // Write status
    input  wire            wr_wbs_cyc_i  ,
    input  wire            wr_wbs_stb_i  ,
    output logic           wr_wbs_ack_o  ,
    output logic [31:0]    wr_wbs_dat_o  ,
    // Read data
    input  wire            rd_wbd_cyc_i  ,
    input  wire            rd_wbd_stb_i  ,
    output logic           rd_wbd_ack_o  ,
    output logic [31:0]    rd_wbd_dat_o  ,
    // Read status
    input  wire            rd_wbs_cyc_i  ,
    input  wire            rd_wbs_stb_i  ,
    output logic           rd_wbs_ack_o  ,
    output logic [31:0]    rd_wbs_dat_o
);

    wire [31:0]    wdat   ;
    wire           wena   ;
    wire           wfull  ;
    wire           rena   ;
    wire    [31:0] rdat   ;
    wire           rempty ;
    wire [ADR_W:0] count  ;

    wb_32bit_fifo_writer #(.ADR_W (ADR_W)) writer (
        .clk_i      ,
        .rst_i      ,

        .wbd_dat_i (wr_wbd_dat_i) ,
        .wbd_we_i  (wr_wbd_we_i ) ,
        .wbd_cyc_i (wr_wbd_cyc_i) ,
        .wbd_stb_i (wr_wbd_stb_i) ,
        .wbd_ack_o (wr_wbd_ack_o) ,

        .wbs_cyc_i (wr_wbs_cyc_i) ,
        .wbs_stb_i (wr_wbs_stb_i) ,
        .wbs_ack_o (wr_wbs_ack_o) ,
        .wbs_dat_o (wr_wbs_dat_o) ,

        .wr_dat_o  (wdat  ) ,
        .wr_ena_o  (wena  ) ,
        .wr_full_i (wfull ) ,
        .wr_num_i  (count )
    );

    fifo_gav #(.DEPTH_WIDTH (ADR_W), .DATA_WIDTH(32)) fifo (
        .clk       (clk_i)   ,
        .rst       (rst_i)  ,

        .wr_data_i (wdat)  ,
        .wr_en_i   (wena)  ,
        .full_o    (wfull) ,

        .rd_data_o (rdat)    ,
        .rd_en_i   (rena)    ,
        .empty_o   (rempty)  ,

        .count_o   (count)
    );

    wb_32bit_fifo_reader #(.ADR_W(ADR_W)) reader (
        .clk_i        ,
        .rst_i        ,

        .wbd_cyc_i (rd_wbd_cyc_i) ,
        .wbd_stb_i (rd_wbd_stb_i) ,
        .wbd_ack_o (rd_wbd_ack_o) ,
        .wbd_dat_o (rd_wbd_dat_o) ,

        .wbs_cyc_i (rd_wbs_cyc_i) ,
        .wbs_stb_i (rd_wbs_stb_i) ,
        .wbs_ack_o (rd_wbs_ack_o) ,
        .wbs_dat_o (rd_wbs_dat_o) ,

        .rd_dat_i   (rdat)   ,
        .rd_ena_o   (rena)   ,
        .rd_empty_i (rempty) ,
        .rd_num_i   (count)
    );

endmodule

`resetall
