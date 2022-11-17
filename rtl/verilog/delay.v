
module delay_pipe #(
    parameter DELAY = 2,
    parameter W = 1,
    parameter [W-1:0] INIT
)(
    input clk,
    input rst,
    input [W-1:0] in,
    output [W-1:0] out
);
    generate
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : u
            reg [DELAY-1:0] rr;

            always @(posedge clk or posedge rst)
                if (rst)
                    rr <= {DELAY{INIT[i]}};
                else
                    rr <= {rr[DELAY-2:0], in[i]};

            assign out[i] = rr[DELAY-1];
        end
    endgenerate

endmodule
