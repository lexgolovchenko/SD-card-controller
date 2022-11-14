
export PRJ_ROOT = $(PWD)/../..

export PYTHONPATH := $(PWD)/../test:$(PYTHONPATH)

SIM  ?= icarus
TOPLEVEL_LANG ?= verilog
TOPLEVEL = tb_top
MODULE = test_tb_top

ifeq ($(SIM), questa)
SIM_ARGS += -onfinish stop
endif

# include ../list/afifo.mk
include ../list/dut.mk
include ../list/tb.mk

include $(shell cocotb-config --makefiles)/Makefile.sim
