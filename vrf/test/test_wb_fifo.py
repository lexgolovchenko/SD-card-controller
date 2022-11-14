
import cocotb
import cocotb.clock
from cocotb.triggers import Timer, Combine
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

#
# Concurent and random write-read test
#

async def get_wb_fifo_write_stat(wbm):
    stat = await wb_read(wbm, WrFifoAddr.STATUS)
    count = stat >> 1
    full = stat & 1
    return count, full


async def get_wb_fifo_read_stat(wbm):
    stat = await wb_read(wbm, RdFifoAddr.STATUS)
    count = stat >> 1
    empty = stat & 1
    return count, empty


async def wb_fifo_write_thread(dut, data_amount, data_buf):
    wbm_wr = wb_master_write_port(dut)
    fifo_size = get_fifo_length(dut)
    data_rest = data_amount

    await Timer(randint(1, 1000) * CLOCK_PERIOD_NS, "ns")

    while data_rest != 0:
        count, full = await get_wb_fifo_write_stat(wbm_wr)
        if full:
            await Timer(randint(1, 1000) * CLOCK_PERIOD_NS, "ns")
        else:
            wr_amount = randint(1, (fifo_size - count))
            if wr_amount > data_rest:
                wr_amount = data_rest
            wbm_wr.log.info("Write {:d} words to fifo".format(wr_amount))
            for _ in range(wr_amount):
                data_buf.append(randint(0, 2 ** 32 - 1))
                await wb_write(wbm_wr, WrFifoAddr.DATA, data_buf[-1])
            data_rest -= wr_amount


async def wb_fifo_read_thread(dut, data_amount, data_buf):
    wbm_rd = wb_master_read_port(dut)
    data_rest = data_amount

    await Timer(randint(1, 1000) * CLOCK_PERIOD_NS, "ns")

    while data_rest != 0:
        count, empty = await get_wb_fifo_read_stat(wbm_rd)
        if empty:
            await Timer(randint(1, 1000) * CLOCK_PERIOD_NS, "ns")
        else:
            rd_amount = randint(1, count)
            wbm_rd.log.info("Read {:d} words from fifo".format(rd_amount))
            for _ in range(rd_amount):
                data_buf.append(await wb_read(wbm_rd, RdFifoAddr.DATA))
            data_rest -= rd_amount


@cocotb.test()
async def wb_fifo_random_test(dut):
    await clock_and_reset(dut)

    fifo_size = get_fifo_length(dut)

    for _ in range(10):
        transfer_len = randint(1 * fifo_size, 5 * fifo_size)
        dut._log.info("Transfer {:0d} words through fifo".format(transfer_len))
        await Timer(CLOCK_PERIOD_NS, "ns")
        wr_data = []
        rd_data = []
        wr_trhead = cocotb.start_soon(wb_fifo_write_thread(dut, transfer_len, wr_data))
        rd_trhead = cocotb.start_soon(wb_fifo_read_thread(dut, transfer_len, rd_data))
        await Combine(wr_trhead, rd_trhead)
        dut._log.info("Done. Compare data")
        assert compare_data(wr_data, rd_data)
