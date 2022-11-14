
`default_nettype none

module wb_32bit_fifo_writer #(
    parameter ADR_W
)(
    input  wire            clk_i      ,
    input  wire            rst_i      ,

    // Wishbone data
    input  wire  [31:0]    wbd_dat_i  ,
    input  wire            wbd_we_i   ,
    input  wire            wbd_cyc_i  ,
    input  wire            wbd_stb_i  ,
    output logic           wbd_ack_o  ,

    // Wishbone status
    input  wire            wbs_cyc_i  ,
    input  wire            wbs_stb_i  ,
    output logic           wbs_ack_o  ,
    output logic [31:0]    wbs_dat_o  ,

    // FIFO
    output logic [31:0]    wr_dat_o   ,
    output logic           wr_ena_o   ,
    input  wire            wr_full_i  ,
    input  wire  [ADR_W:0] wr_num_i
);

    //
    // Write data to FIFO
    //

    enum {
        IDLE, ACK_WR, ACK_RD
    } state;

    always_ff @(posedge clk_i, posedge rst_i)
        if (rst_i)
            state <= IDLE;
        else case (state)
            IDLE: if (wbd_cyc_i && wbd_stb_i)
                    state <= wbd_we_i
                           ? ACK_WR
                           : ACK_RD;
            ACK_WR: state <= IDLE;
            ACK_RD: state <= IDLE;
        endcase

    assign wr_ena_o  = (state == ACK_WR);
    assign wr_dat_o  = wbd_dat_i;
    assign wbd_ack_o = (state == ACK_WR) || (state == ACK_RD);

    //
    // Read FIFO status
    //

    assign wbs_dat_o = {'0, wr_num_i, wr_full_i};

    always_ff @(posedge clk_i, posedge rst_i)
        if (rst_i)
		    wbs_ack_o <= 1'b0;
	    else if (wbs_ack_o)
		    wbs_ack_o <= 1'b0;
	    else if (wbs_cyc_i && wbs_stb_i && !wbs_ack_o)
		    wbs_ack_o <= 1'b1;

endmodule

`resetall
