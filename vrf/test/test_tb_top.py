
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from cocotbext.wishbone.driver import WishboneMaster
from cocotbext.wishbone.monitor import WishboneSlave
from cocotbext.wishbone.driver import WBOp

from random import randint
from sdc_wb_ctrl import *
from test_data import TestData
from typing import List
import cocotb.handle

async def wait_reset_release(dut):
    dut.wb_rst._log.info("Waiting reset release...")
    if dut.wb_rst == 1:
        await FallingEdge(dut.wb_rst)
    dut.wb_rst._log.info("Reset done!")


def wishbone_master_init(dut):
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
    return WishboneMaster(dut, "wb", dut.wb_clk,
                          width=32,
                          timeout=10, signals_dict=signals_dict)


BLOCK_SIZE = 512
FLASH_BLOCKS = 0


class WbDmaId(IntEnum):
    RAM0 = 0
    RAM1 = 1
    FIFO0 = 2
    FIFO1 = 3


WB_DMA_BASE_ADDR = {
    WbDmaId.RAM0  : 0x00000000,
    WbDmaId.RAM1  : 0x40000000,
    WbDmaId.FIFO0 : 0x80000000,
    WbDmaId.FIFO1 : 0xc0000000
}


def get_memory_base_address(dut, mem_idx) -> int:
    # AW = int(dut.AW)
    # print(dut.mux_base_addr_export[1:0].value)
    # return dut.mux_base_addr_export[mem_idx].value.integer
    return WB_DMA_BASE_ADDR[mem_idx]


def get_ram_start_block_addr(ram, blocks_num) -> int:
    ram_bytes = pow(2, int(ram.aw))
    blocks_in_ram = ram_bytes // 512
    assert blocks_in_ram >= blocks_num
    return randint(0, blocks_in_ram - blocks_num) * 512


def get_sd_start_addr(sd, blocks_num) -> int:
    sd_blocks_num = int(sd.BLOCKS_NUM)
    assert sd_blocks_num >= blocks_num
    return randint(0, sd_blocks_num - blocks_num) * 512


def ram_backdoor_write(ram, start_adr, wrdat: TestData):
    adr = start_adr // 4
    for blk32 in wrdat.data32:
        for val32 in blk32:
            ram.ram0.mem[adr].value = val32
            adr += 1


def ram_backdoor_read(ram, start_adr, block_num) -> List[List[int]]:
    adr = start_adr // 4
    data32 = []
    for _ in range(block_num):
        blk32 = []
        for _ in range(BLOCK_SIZE // 4):
            blk32.append(ram.ram0.mem[adr].value.integer)
            adr += 1
        data32.append(blk32)
    return data32


def sd_model_backdoor_read(sd, start_addr, block_num) -> List[List[int]]:
    # adr = lba * 512
    adr = start_addr
    data8 = []
    for _ in range(block_num):
        blk8 = []
        for _ in range(BLOCK_SIZE):
            # print("{:08x} : {:s}".format(adr, str(sd.FLASHmem[adr].value)))
            blk8.append(sd.FLASHmem[adr].value.integer)
            adr += 1
        data8.append(blk8)
    return data8


def sd_model_backdoor_write(sd, start_addr, wrdat: TestData):
    # adr = lba * 512
    adr = start_addr
    for blk8 in wrdat.data8:
        for val8 in blk8:
            sd.FLASHmem[adr].value = val8
            adr += 1


def compare_data(a: List[List[int]], b: List[List[int]]) -> bool:
    assert len(a) == len(b)
    for i in range(len(a)):
        a_blk = a[i]
        b_blk = b[i]
        assert len(a_blk) == len(b_blk)
        for j in range(len(a_blk)):
            assert a_blk[j] == b_blk[j]
    return True


async def ram_backdoor_test(dut, ram_idx, blk_min=1, blk_max=1):
    wrdat = TestData(blk_min, blk_max)
    wrdat.randomize()

    ram = dut.ram0 if (ram_idx == 0) else dut.ram1
    ram_start_adr = get_ram_start_block_addr(ram, wrdat.block_num)

    ram_backdoor_write(ram, ram_start_adr, wrdat)
    await Timer(1, units="us")
    test_data32 = ram_backdoor_read(ram, ram_start_adr, wrdat.block_num)

    assert compare_data(wrdat.data32, test_data32)


async def sd_backdoor_test(dut, blk_min=1, blk_max=1):
    wrdat = TestData(blk_min, blk_max)
    wrdat.randomize()

    sd_start_adr = get_sd_start_addr(dut.sd_model, wrdat.block_num)

    sd_model_backdoor_write(dut.sd_model, sd_start_adr, wrdat)
    await Timer(1, units="us")
    sd_rddat8 = sd_model_backdoor_read(dut.sd_model, sd_start_adr, wrdat.block_num)

    assert compare_data(wrdat.data8, sd_rddat8)


async def write_from_ram_to_sd(dut, wbm, ram_idx, blk_min=1, blk_max=1):
    # Generate test data
    wrdat = TestData(blk_min, blk_max)
    wrdat.randomize()

    # Info
    dut._log.info("Write {:0d} blocks to SD card to RAM{:0d}".format(wrdat.block_num, ram_idx))

    # Write data to choosen RAM
    ram = dut.ram0 if (ram_idx == 0) else dut.ram1
    ram_start_adr = get_ram_start_block_addr(ram, wrdat.block_num)
    ram_base_adr = get_memory_base_address(dut, ram_idx)
    ram_backdoor_write(ram, ram_start_adr, wrdat)

    # SD address
    sd_start_adr = get_sd_start_addr(dut.sd_model, wrdat.block_num)

    # Write data to SD
    await sdc_write_blocks(wbm, sd_start_adr, ram_base_adr+ram_start_adr, wrdat.block_num)
    await Timer(1, units="us")

    # Read data from SD
    sd_rddat8 = sd_model_backdoor_read(dut.sd_model, sd_start_adr, wrdat.block_num)

    # Compare result
    assert compare_data(wrdat.data8, sd_rddat8)


async def read_to_ram_from_sd(dut, wbm, ram_idx, blk_min=1, blk_max=1):
    # Generate test data
    wrdat = TestData(blk_min, blk_max)
    wrdat.randomize()

    # Info
    dut._log.info("Read {:0d} blocks from SD card to RAM{:0d}".format(wrdat.block_num, ram_idx))

    # Write data to SD
    sd_start_adr = get_sd_start_addr(dut.sd_model, wrdat.block_num)
    sd_model_backdoor_write(dut.sd_model, sd_start_adr, wrdat)

    # Select memory address to read
    ram = dut.ram0 if (ram_idx == 0) else dut.ram1
    ram_start_adr = get_ram_start_block_addr(ram, wrdat.block_num)
    ram_base_adr = get_memory_base_address(dut, ram_idx)

    # Write data to SD
    await sdc_read_blocks(wbm, sd_start_adr, ram_base_adr+ram_start_adr, wrdat.block_num)
    await Timer(1, units="us")

    # Read data from RAM
    ram_rddat32 = ram_backdoor_read(ram, ram_start_adr, wrdat.block_num)

    # Compare result
    assert compare_data(wrdat.data32, ram_rddat32)


@cocotb.test()
async def memory_backdoor_test(dut):
    dut._log.info("Memory backdoor test")
    await wait_reset_release(dut)
    await Timer(1, units="us")
    await ram_backdoor_test(dut, WbDmaId.RAM0, 1, 10)
    await ram_backdoor_test(dut, WbDmaId.RAM1, 1, 10)
    await sd_backdoor_test(dut, 1, 10)
    dut._log.info("Done!")


@cocotb.test()
async def write_from_ram_to_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm)
    await sdc_setup_card_to_transfer(wbm)

    for _ in range(5):
        await write_from_ram_to_sd(dut, wbm, WbDmaId.RAM0, 1, 10)
        await write_from_ram_to_sd(dut, wbm, WbDmaId.RAM1, 1, 10)

    dut._log.info("Done!")


@cocotb.test()
async def read_to_ram_from_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm)
    await sdc_setup_card_to_transfer(wbm)

    for _ in range(5):
        await read_to_ram_from_sd(dut, wbm, WbDmaId.RAM0, 1, 10)
        await read_to_ram_from_sd(dut, wbm, WbDmaId.RAM1, 1, 10)

    dut._log.info("Done!")


# ------------------------------------------------------------------
# Testcases with fifo
# ------------------------------------------------------------------
#

class WbId(IntEnum):
    SDC   = 0
    FIFO0 = 1
    FIFO1 = 2


WB_BASE_ADDR = {
    WbId.SDC   : 0x00000000,
    WbId.FIFO0 : 0x40000000,
    WbId.FIFO1 : 0x80000000,
}


class FifoAddr(IntEnum):
    DATA   = 0x00000000
    STATUS = 0x01000000


async def wb_write(wbm: WishboneMaster, adr: int, data: int):
    await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5), dat=data, sel=0xF)])


async def wb_read(wbm: WishboneMaster, adr: int) -> int:
    result = await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5))])
    return result[0].datrd.integer


async def read_data_from_wb_fifo(wbm, block_num):
    fifo_base_adr = WB_BASE_ADDR[WbId.FIFO0]
    expected_count = block_num * (BLOCK_SIZE // 4)

    stat_adr = fifo_base_adr | FifoAddr.STATUS
    rd_stat = await wb_read(wbm, stat_adr)
    count = rd_stat >> 1
    assert count == expected_count

    data32 = []
    for _ in range(block_num):
        blk32 = []
        for _ in range(BLOCK_SIZE // 4):
            val32 = await wb_read(wbm, fifo_base_adr | FifoAddr.DATA)
            blk32.append(val32)
        data32.append(blk32)

    return data32


async def read_to_fifo_from_sd(dut, wbm, blk_min=1, blk_max=1):
    # Generate test data
    wrdat = TestData(blk_min, blk_max)
    wrdat.randomize()

    # Info
    dut._log.info("Read {:0d} blocks from SD card to FIFO0".format(wrdat.block_num))

    # Write data to SD
    sd_start_adr = get_sd_start_addr(dut.sd_model, wrdat.block_num)
    sd_model_backdoor_write(dut.sd_model, sd_start_adr, wrdat)

    # Write data to SD
    await sdc_read_blocks(wbm, sd_start_adr, WB_DMA_BASE_ADDR[WbDmaId.FIFO0], wrdat.block_num)
    await Timer(1, units="us")

    # Read data from WB FIFO
    fifo_rddat32 = await read_data_from_wb_fifo(wbm, wrdat.block_num)

    # Compare result
    assert compare_data(wrdat.data32, fifo_rddat32)


@cocotb.test()
async def read_to_fifo_from_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm)
    await sdc_setup_card_to_transfer(wbm)

    for _ in range(10):
        await read_to_fifo_from_sd(dut, wbm, 1, 4)


async def write_data_to_wb_fifo(wbm: WishboneMaster, wdata: TestData):
    data_adr = WB_BASE_ADDR[WbId.FIFO1] | FifoAddr.DATA
    for blk32 in wdata.data32:
        for val32 in blk32:
            await wb_write(wbm, data_adr, val32)


async def write_from_fifo_to_sd_direct(dut, wbm):
    # Generate test data
    wrdat = TestData(4, 4)
    wrdat.randomize()

    await write_data_to_wb_fifo(wbm, wrdat)

    # Write data to SD
    sd_rddat8 = []
    for _ in range(4):
        sd_start_adr = get_sd_start_addr(dut.sd_model, wrdat.block_num)
        await sdc_write_blocks(wbm, sd_start_adr, WB_DMA_BASE_ADDR[WbDmaId.FIFO1], 1)
        await Timer(1, units="us")
        rddat8 = sd_model_backdoor_read(dut.sd_model, sd_start_adr, 1)
        sd_rddat8.append(rddat8[0])

    # Compare result
    assert compare_data(wrdat.data8, sd_rddat8)


@cocotb.test()
async def write_from_fifo_to_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm)
    await sdc_setup_card_to_transfer(wbm)

    await write_from_fifo_to_sd_direct(dut, wbm)
