
ifeq ($(SIM), questa)
COMPILE_ARGS += +incdir+$(PRJ_ROOT)/rtl/verilog
else
COMPILE_ARGS += -I$(PRJ_ROOT)/rtl/verilog -D VENDOR_FPGA
endif

VERILOG_SOURCES += \
	$(PRJ_ROOT)/rtl/verilog/delay.v \
	$(PRJ_ROOT)/rtl/verilog/bistable_domain_cross.v \
	$(PRJ_ROOT)/rtl/verilog/byte_en_reg.v \
	$(PRJ_ROOT)/rtl/verilog/edge_detect.v \
	$(PRJ_ROOT)/rtl/verilog/generic_dpram.v \
	$(PRJ_ROOT)/rtl/verilog/generic_fifo_dc_gray.v \
	$(PRJ_ROOT)/rtl/verilog/monostable_domain_cross.v \
	$(PRJ_ROOT)/rtl/verilog/sdc_controller.v \
	$(PRJ_ROOT)/rtl/verilog/sd_clock_divider.v \
	$(PRJ_ROOT)/rtl/verilog/sd_cmd_master.v \
	$(PRJ_ROOT)/rtl/verilog/sd_cmd_serial_host.v \
	$(PRJ_ROOT)/rtl/verilog/sd_controller_wb.v \
	$(PRJ_ROOT)/rtl/verilog/sd_crc_16.v \
	$(PRJ_ROOT)/rtl/verilog/sd_crc_7.v \
	$(PRJ_ROOT)/rtl/verilog/sd_data_master.v \
	$(PRJ_ROOT)/rtl/verilog/sd_data_serial_host.v \
	$(PRJ_ROOT)/rtl/verilog/sd_data_xfer_trig.v \
	$(PRJ_ROOT)/rtl/verilog/sd_fifo_filler.v \
	$(PRJ_ROOT)/rtl/verilog/sd_wb_sel_ctrl.v
