
export PRJ_ROOT = $(PWD)/../../..

export PYTHONPATH := $(PRJ_ROOT)/vrf/test:$(PYTHONPATH)

SIM  ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = tb_top
MODULE = test_tb_top

ifeq ($(SIM), questa)
SIM_ARGS += -onfinish stop
endif

include $(PRJ_ROOT)/vrf/list/dut.mk
include $(PRJ_ROOT)/vrf/list/wb.mk
include $(PRJ_ROOT)/vrf/list/fifo.mk
include $(PRJ_ROOT)/vrf/list/tb.mk

include $(shell cocotb-config --makefiles)/Makefile.sim
