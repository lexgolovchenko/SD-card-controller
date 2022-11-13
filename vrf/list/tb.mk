
#
# SD card model
#

ifeq ($(SIM), questa)
COMPILE_ARGS += +incdir+$(PRJ_ROOT)/rtl/verilog
else
COMPILE_ARGS += -I$(PRJ_ROOT)/rtl/verilog
endif

VERILOG_SOURCES += \
	$(PRJ_ROOT)/bench/verilog/sdModel.v

#
# TB top componets
#
ifeq ($(SIM), questa)
COMPILE_ARGS += +incdir+$(PRJ_ROOT)/vrf/tb/wb_common
else
COMPILE_ARGS += -I$(PRJ_ROOT)/vrf/tb/wb_common
endif

VERILOG_SOURCES += \
	$(PRJ_ROOT)/vrf/tb/wb_ram/rtl/verilog/wb_ram.v \
	$(PRJ_ROOT)/vrf/tb/wb_ram/rtl/verilog/wb_ram_generic.v \
	$(PRJ_ROOT)/vrf/tb/wb_intercon/rtl/verilog/wb_mux.v \
	$(PRJ_ROOT)/vrf/tb/tb_top.sv


