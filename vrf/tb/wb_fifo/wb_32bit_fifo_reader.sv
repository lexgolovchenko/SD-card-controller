
`default_nettype none

module wb_32bit_fifo_reader #(
    parameter ADR_W
)(
    input  wire           clk_i        ,
    input  wire           rst_i        ,

    // Wishbone data
    input  wire            wbd_cyc_i  ,
    input  wire            wbd_stb_i  ,
    output logic           wbd_ack_o  ,
    output logic [31:0]    wbd_dat_o  ,

    // Wishbone status
    input  wire            wbs_cyc_i  ,
    input  wire            wbs_stb_i  ,
    output logic           wbs_ack_o  ,
    output logic [31:0]    wbs_dat_o  ,

    // FIFO
    input  wire  [31:0]   rd_dat_i     ,
    output logic          rd_ena_o     ,
    input  wire           rd_empty_i   ,
    input  wire [ADR_W:0] rd_num_i
);

    //
    // Read data from FIFO
    //

    enum {
        IDLE, ACK
    } state;

    always_ff @(posedge clk_i, posedge rst_i)
        if (rst_i)
            state <= IDLE;
        else begin
            case (state)
                IDLE: if (wbd_cyc_i && wbd_stb_i) begin
                    state <= ACK;
                end

                ACK: begin
                    state <= IDLE;
                end
            endcase
        end

    assign rd_ena_o  = (state == IDLE) && (wbd_cyc_i && wbd_stb_i);
    assign wbd_dat_o = rd_dat_i;
    assign wbd_ack_o = (state == ACK);

    //
    // Read FIFO status
    //

    assign wbs_dat_o = {'0, rd_num_i, rd_empty_i};

    always_ff @(posedge clk_i, posedge rst_i)
        if (rst_i)
		    wbs_ack_o <= 1'b0;
	    else if (wbs_ack_o)
		    wbs_ack_o <= 1'b0;
	    else if (wbs_cyc_i && wbs_stb_i && !wbs_ack_o)
		    wbs_ack_o <= 1'b1;


endmodule

`resetall
