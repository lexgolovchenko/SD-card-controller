
import cocotb
import cocotb.clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.wishbone.driver import WishboneMaster, WBOp
from random import randint
from enum import IntEnum
from typing import List

CLOCK_PERIOD_NS = 10

async def clock_and_reset(dut):
    dut.clk_i.value = 0
    dut.rst_i.value = 0

    # Start clock
    c = cocotb.clock.Clock(dut.clk_i, CLOCK_PERIOD_NS, "ns")
    await cocotb.start(c.start())

    # Generate reset
    await Timer(2 * CLOCK_PERIOD_NS, "ns")
    dut.rst_i.value = 1
    await Timer(5 * CLOCK_PERIOD_NS, "ns")
    dut.rst_i.value = 0
    await Timer(2 * CLOCK_PERIOD_NS, "ns")


def wb_master_write_port(dut):
    signals_dict={
        "cyc":  "cyc_i",
        "stb":  "stb_i",
        "we":   "we_i",
        "sel":  "sel_i",
        "adr":  "adr_i",
        "datwr":"dat_i",
        "datrd":"dat_o",
        "ack":  "ack_o"
    }
    return WishboneMaster(dut, "wr", dut.clk_i, width=32,
                          timeout=10, signals_dict=signals_dict)


def wb_master_read_port(dut):
    signals_dict={
        "cyc":  "cyc_i",
        "stb":  "stb_i",
        "we":   "we_i",
        "sel":  "sel_i",
        "adr":  "adr_i",
        "datwr":"dat_i",
        "datrd":"dat_o",
        "ack":  "ack_o"
    }
    return WishboneMaster(dut, "rd", dut.clk_i, width=32,
                          timeout=10, signals_dict=signals_dict)


async def wb_write(wbm: WishboneMaster, adr: int, data: int):
    await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5), dat=data, sel=0xF)])


async def wb_read(wbm: WishboneMaster, adr: int) -> int:
    result = await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5))])
    return result[0].datrd.integer


class WrFifoAddr(IntEnum):
    DATA   = 0x00000000
    STATUS = 0x01000000


class RdFifoAddr(IntEnum):
    DATA   = 0x00000000
    STATUS = 0x01000000


def get_fifo_length(dut):
    count = 2 ** int(dut.FIFO_ADR_W)
    return count


def compare_data(a: List[int], b: List[int]) -> bool:
    assert len(a) == len(b)
    for i in range(len(a)):
        assert a[i] == b[i]
    return True


@cocotb.test()
async def wb_fifo_hello_test(dut):
    dut._log.info("Hello!")


@cocotb.test()
async def wb_fifo_write_full_read_empty_test(dut):
    await clock_and_reset(dut)
    wbm_wr = wb_master_write_port(dut)
    wbm_rd = wb_master_read_port(dut)

    wr_data = []
    rd_data = []

    wr_stat = await wb_read(wbm_wr, WrFifoAddr.STATUS)
    rd_stat = await wb_read(wbm_rd, RdFifoAddr.STATUS)
    assert wr_stat == 0
    assert rd_stat == 1

    wbm_wr.log.info("WR status : count={:d} full={:d}".format(wr_stat >> 1, wr_stat & 0x1))
    wbm_rd.log.info("RD status : count={:d} empty={:d}".format(rd_stat >> 1, rd_stat & 0x1))

    while not (wr_stat & 0x1):
        wr_data.append(randint(0, 2 ** 32 - 1))
        await wb_write(wbm_wr, WrFifoAddr.DATA, wr_data[-1])
        wr_stat = await wb_read(wbm_wr, WrFifoAddr.STATUS)

    rd_stat = await wb_read(wbm_rd, RdFifoAddr.STATUS)
    assert (wr_stat & 0x1) == 1
    assert (wr_stat >> 1) == get_fifo_length(dut)
    assert (rd_stat & 0x1) == 0
    assert (rd_stat >> 1) == get_fifo_length(dut)
    wbm_wr.log.info("WR status : count={:d} full={:d}".format(wr_stat >> 1, wr_stat & 0x1))
    wbm_rd.log.info("RD status : count={:d} empty={:d}".format(rd_stat >> 1, rd_stat & 0x1))

    while not (rd_stat & 0x1):
        rd_data.append(await wb_read(wbm_rd, RdFifoAddr.DATA))
        rd_stat = await wb_read(wbm_rd, RdFifoAddr.STATUS)

    wr_stat = await wb_read(wbm_wr, WrFifoAddr.STATUS)
    assert wr_stat == 0
    assert rd_stat == 1

    wbm_wr.log.info("WR status : count={:d} full={:d}".format(wr_stat >> 1, wr_stat & 0x1))
    wbm_rd.log.info("RD status : count={:d} empty={:d}".format(rd_stat >> 1, rd_stat & 0x1))

    assert compare_data(wr_data, rd_data)
