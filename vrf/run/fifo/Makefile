
export PRJ_ROOT = $(PWD)/../../..

export PYTHONPATH := $(PRJ_ROOT)/vrf/test:$(PYTHONPATH)

SIM  ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = wb_fifo
MODULE = test_wb_fifo

ifeq ($(SIM), questa)
SIM_ARGS += -onfinish stop
endif

include $(PRJ_ROOT)/vrf/list/wb.mk
include $(PRJ_ROOT)/vrf/list/fifo.mk

include $(shell cocotb-config --makefiles)/Makefile.sim
