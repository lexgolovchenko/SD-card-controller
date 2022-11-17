
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


# @cocotb.test()
# async def change_clock_test(dut):
#     await Timer(5, units="us")
#     dut.T_CLK_NS.value = 20
#     await Timer(5, units="us")
#     dut.T_CLK_NS.value = 100
#     await Timer(5, units="us")
#     dut.T_CLK_NS.value = 2
#     await Timer(5, units="us")
#     dut.T_CLK_NS.value = 10
#     await Timer(5, units="us")

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
    dut._log.info("Write {:0d} blocks to SD card from RAM{:0d}".format(wrdat.block_num, ram_idx))

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
    await sdc_initial_core_setup(wbm, divider=randint(0, 6))
    await sdc_setup_card_to_transfer(wbm)

    for i in range(10):
        divider = 0 if (i % 2 == 1) else randint(1, 6)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await write_from_ram_to_sd(dut, wbm, WbDmaId.RAM0, 1, 10)
        await Timer(20, units="us")

        divider = 0 if (i % 2 == 0) else randint(1, 6)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await write_from_ram_to_sd(dut, wbm, WbDmaId.RAM1, 1, 10)
        await Timer(20, units="us")

    dut._log.info("Done!")


@cocotb.test()
async def read_to_ram_from_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm, divider=randint(0, 6))
    await sdc_setup_card_to_transfer(wbm)

    for i in range(5):
        divider = 0 if (i % 2 == 1) else randint(1, 1)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await read_to_ram_from_sd(dut, wbm, WbDmaId.RAM0, 1, 10)
        await Timer(20, units="us")

        divider = 0 if (i % 2 == 0) else randint(1, 3)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await read_to_ram_from_sd(dut, wbm, WbDmaId.RAM1, 1, 10)
        await Timer(20, units="us")

    dut._log.info("Done!")


# ------------------------------------------------------------------
# Testcases with fifo
# ------------------------------------------------------------------
#

def get_fifo_size_in_blocks(dut, fifo_idx):
    if fifo_idx == 0:
        return (2 ** int(dut.fifo0.FIFO_ADR_W)) // (BLOCK_SIZE // 4)
    elif fifo_idx == 1:
        return (2 ** int(dut.fifo1.FIFO_ADR_W)) // (BLOCK_SIZE // 4)
    else:
        raise ValueError("Fifo Index must be 0 or 1")


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

    rd_stat = await wb_read(wbm, stat_adr)
    count = rd_stat >> 1
    empty = rd_stat & 1
    assert count == 0
    assert empty == 1

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
    blocks_max = get_fifo_size_in_blocks(dut, 0)

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm, divider=randint(0, 6))
    await sdc_setup_card_to_transfer(wbm)

    for i in range(10):
        divider = 0 if (i % 2) else randint(1, 6)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await read_to_fifo_from_sd(dut, wbm, 1, blocks_max)
        await Timer(20, units="us")


async def write_data_to_wb_fifo(wbm: WishboneMaster, wdata: TestData):
    data_adr = WB_BASE_ADDR[WbId.FIFO1] | FifoAddr.DATA
    for blk32 in wdata.data32:
        for val32 in blk32:
            await wb_write(wbm, data_adr, val32)


async def write_from_fifo_to_sd_direct(dut, wbm):
    # Generate test data
    blocks_max = get_fifo_size_in_blocks(dut, 1)
    wrdat = TestData(blocks_max, blocks_max)
    wrdat.randomize()

    dut._log.info("Write {:0d} blocks to WB FIFO1".format(wrdat.block_num))
    await write_data_to_wb_fifo(wbm, wrdat)

    # Write data to SD by 1 block
    sd_rddat8 = []
    blk_rest = blocks_max
    while blk_rest != 0:
        blk_num = randint(1, 2)
        if blk_num > blk_rest:
            blk_num = blk_rest
        dut._log.info("Write {:0d} blocks to SD card from FIFO1".format(blk_num))
        sd_start_adr = get_sd_start_addr(dut.sd_model, blk_num)
        await sdc_write_blocks(wbm, sd_start_adr, WB_DMA_BASE_ADDR[WbDmaId.FIFO1], blk_num)
        await Timer(1, units="us")
        rddat8 = sd_model_backdoor_read(dut.sd_model, sd_start_adr, blk_num)
        for blk in rddat8:
            sd_rddat8.append(blk)

        blk_rest -= blk_num

    # Compare result
    assert compare_data(wrdat.data8, sd_rddat8)


async def write_from_fifo_to_sd_random(dut, wbm):
    # Generate test data
    blocks_max = get_fifo_size_in_blocks(dut, 1)
    wrdat = TestData(1, blocks_max)
    wrdat.randomize()

    dut._log.info("Write {:0d} blocks to WB FIFO1".format(wrdat.block_num))
    await write_data_to_wb_fifo(wbm, wrdat)

    blk_num = wrdat.block_num
    dut._log.info("Write {:0d} blocks to SD card from FIFO1".format(blk_num))
    sd_start_adr = get_sd_start_addr(dut.sd_model, blk_num)
    await sdc_write_blocks(wbm, sd_start_adr, WB_DMA_BASE_ADDR[WbDmaId.FIFO1], blk_num)
    await Timer(1, units="us")
    sd_rddat8 = sd_model_backdoor_read(dut.sd_model, sd_start_adr, blk_num)

    # Compare result
    assert compare_data(wrdat.data8, sd_rddat8)


@cocotb.test()
async def write_from_fifo_to_sd_test(dut):
    await wait_reset_release(dut)
    await Timer(1, units="us")
    blocks_max = get_fifo_size_in_blocks(dut, 1)

    wbm = wishbone_master_init(dut)
    await sdc_initial_core_setup(wbm, divider=randint(0, 6))
    await sdc_setup_card_to_transfer(wbm)

    for i in range(10):
        divider = 0 if (i % 2) else randint(1, 6)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await write_from_fifo_to_sd_direct(dut, wbm)
        await Timer(20, units="us")

    for i in range(10):
        divider = 0 if (i % 2) else randint(1, 6)
        await sdc_set_sd_clk_divider(wbm, divider)
        await Timer(20, units="us")
        await write_from_fifo_to_sd_random(dut, wbm)
        await Timer(20, units="us")

    await Timer(10, units="us")
