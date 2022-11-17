
from enum import IntEnum
from random import randint
from cocotbext.wishbone.driver import WishboneMaster, WBOp
from cocotb.triggers import Timer

class SdcRegs(IntEnum):
    ARGUMENT          = 0x0
    COMMAND           = 0x4
    RESPONSE0         = 0x8
    RESPONSE1         = 0xC
    RESPONSE2         = 0x10
    RESPONSE3         = 0x14
    DATA_TIMEOUT      = 0x18
    CONTROL           = 0x1C
    CMD_TIMEOUT       = 0x20
    CLOCK_DIVIDER     = 0x24
    RESET             = 0x28
    VOLTAGE           = 0x2C
    CAPABILITIES      = 0x30
    CMD_EVENT_STATUS  = 0x34
    CMD_EVENT_ENABLE  = 0x38
    DATA_EVENT_STATUS = 0x3C
    DATA_EVENT_ENABLE = 0x40
    BLKOCK_SIZE       = 0x44
    BLKOCK_COUNT      = 0x48
    DST_SRC_ADDRESS   = 0x60


class SdcCommands(IntEnum):
    CMD0   = 0x0000     # GO_TO_IDLE_STATE
    CMD2   = 0x0200     # ALL_SEND_CID
    CMD3   = 0x0300     # SEND_RELATIVE_ADDR
    CMD7   = 0x0700     # SELECT_CARD
    CMD8   = 0x0800     # SEND_IF_COND
    CMD9   = 0x0900     # SEND_CSD
    CMD55  = 0x3700     # APP_CMD
    ACMD41 = 0x2900     # SD_SEND_OP_COND
    ACMD6  = 0x0600     # SET_BUS_WIDTH
    CMD12  = 0x0C00     # STOP_TRANSMISSION
    CMD16  = 0x1000     #
    CMD17  = 0x1100     # READ_SINGLE_BLOCK
    CMD18  = 0x1200     # READ_MULTIPLE_BLOCK
    CMD24  = 0x1800     # READ_SINGLE_BLOCK
    CMD25  = 0x1900     # WRITE_MULTIPLE_BLOCK


class SdcRspCfg(IntEnum):
    RSP__48  = 0x0001   # rsp size 48 bit
    RSP_136  = 0x0002   # rsp size 136 bit
    RSP_BUSY = 0x0004   # check busy signal on data line
    RSP_CRC  = 0x0008   # rsp contains CRC
    RSP_IDX  = 0x0010   # rsp contains cmd index (opcode)


class SdcRspType(IntEnum):
    NO_RSP  =  0x0000
    RSP_R1	= (SdcRspCfg.RSP__48|SdcRspCfg.RSP_CRC|SdcRspCfg.RSP_IDX)
    RSP_R1b	= (SdcRspCfg.RSP__48|SdcRspCfg.RSP_CRC|SdcRspCfg.RSP_IDX|SdcRspCfg.RSP_BUSY)
    RSP_R2	= (SdcRspCfg.RSP_136|SdcRspCfg.RSP_CRC)
    RSP_R3	= (SdcRspCfg.RSP__48)
    RSP_R6	= (SdcRspCfg.RSP__48|SdcRspCfg.RSP_CRC|SdcRspCfg.RSP_IDX)
    RSP_R7	= (SdcRspCfg.RSP__48|SdcRspCfg.RSP_CRC|SdcRspCfg.RSP_IDX)


class SdcDataTransCfg(IntEnum):
    RD = 0x0020
    WR = 0x0040


class SdcCmdEventStatus(IntEnum):
    OK      = (1 << 0)
    ERR     = (1 << 1)
    TIMEOUT = (1 << 2)
    CRC     = (1 << 3)
    INDEX   = (1 << 4)


class SdcDataEventStatus(IntEnum):
    OK      = (1 << 0)
    ERR     = (1 << 1)
    TIMEOUT = (1 << 2)
    CRC     = (1 << 3)
    INDEX   = (1 << 4)


class SdcOcrFlds(IntEnum):
    BUSY = 0x80000000
    HCS  = 0x40000000
    VDD  = 0x00ff8000


class SdcException(Exception):
    pass


class SdcCmdEventStatusException(SdcException):
    def __init__(self, code):
        self.msg = ""
        if code & SdcCmdEventStatus.TIMEOUT:
            self.msg = "Timeout error"
        elif code & SdcCmdEventStatus.CRC:
            self.msg = "CRC error"
        elif code & SdcCmdEventStatus.INDEX:
            self.msg = "CRC error"
        super().__init__(self.msg)


class SdcDataEventStatusException(SdcException):
    def __init__(self, code):
        self.msg = ""
        if code & SdcCmdEventStatus.TIMEOUT:
            self.msg = "Timeout error"
        elif code & SdcCmdEventStatus.CRC:
            self.msg = "CRC error"
        elif code & SdcCmdEventStatus.INDEX:
            self.msg = "CRC error"
        super().__init__(self.msg)


async def sdc_reg_write(wbm: WishboneMaster, adr: int, data: int):
    await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5), dat=data, sel=0xF)])


async def sdc_reg_read(wbm: WishboneMaster, adr: int) -> int:
    result = await wbm.send_cycle([WBOp(adr=adr, idle=randint(0, 5))])
    return result[0].datrd


async def sdc_initial_core_setup(wbm, divider=0):
    wbm.log.info("Set clock divider value {:d}".format(divider))
    # Reset core
    await sdc_reg_write(wbm, SdcRegs.RESET, 1)
    # Setup timeouts
    await sdc_reg_write(wbm, SdcRegs.CMD_TIMEOUT, 0x3FFFF)
    await sdc_reg_write(wbm, SdcRegs.DATA_TIMEOUT, 0x3FFFF)
    # Setup clock divider
    await sdc_reg_write(wbm, SdcRegs.CLOCK_DIVIDER, divider)
    # Enable all interrupt
    await sdc_reg_write(wbm, SdcRegs.CMD_EVENT_ENABLE, 0x1f)
    await sdc_reg_write(wbm, SdcRegs.DATA_EVENT_ENABLE, 0x1f)
    # 4-bit bus
    await sdc_reg_write(wbm, SdcRegs.CONTROL, 1)
    # Start core
    await sdc_reg_write(wbm, SdcRegs.RESET, 0)
    await Timer(20, units="us")


async def sdc_set_sd_clk_divider(wbm, divider):
    await sdc_reg_write(wbm, SdcRegs.CLOCK_DIVIDER, divider)


async def sdc_send_cmd(wbm: WishboneMaster, cmd: int, arg: int):
    await sdc_reg_write(wbm, SdcRegs.COMMAND, cmd)
    await sdc_reg_write(wbm, SdcRegs.ARGUMENT, arg)

    result = 0
    while result == 0:
        result = await sdc_reg_read(wbm, SdcRegs.CMD_EVENT_STATUS)

    if result != SdcCmdEventStatus.OK:
        raise SdcCmdEventStatusException(result)

    # Clear IRQ
    await sdc_reg_write(wbm, SdcRegs.CMD_EVENT_STATUS, 0)


async def sdc_go_to_idle(wbm: WishboneMaster):
    wbm.log.info("SD go to idle")
    await sdc_send_cmd(wbm, SdcCommands.CMD0 | SdcRspType.NO_RSP, 0)


class SdcExceptionUnusable(SdcException):
    pass


async def sdc_send_if_cond(wbm: WishboneMaster):
    wbm.log.info("SD send if condition")
    IF_COND_VOLT_27_33 = 0x01
    IF_COND_CHK_PTRN   = 0x00
    # IF_COND_CHK_PTRN   = 0xAA
    arg = (IF_COND_VOLT_27_33 << 8) | IF_COND_CHK_PTRN
    cmd = SdcCommands.CMD8 | SdcRspType.RSP_R7
    await sdc_send_cmd(wbm, cmd, arg)

    wbm.log.info("Check pattern")
    rsp0 = await sdc_reg_read(wbm, SdcRegs.RESPONSE0)
    if (rsp0 & 0xFF) != IF_COND_CHK_PTRN:
        raise SdcExceptionUnusable()


class SdcToutException(SdcException):
    pass


async def sdc_send_op_cond(wbm: WishboneMaster):
    tout = 1
    busy_flag = True
    while busy_flag and tout:
        await sdc_send_cmd(wbm, SdcCommands.CMD55 | SdcRspType.RSP_R1, 0)
        await sdc_delay_us(10)
        await sdc_send_cmd(wbm, SdcCommands.ACMD41 | SdcRspType.RSP_R3, 0)

        rsp0 = await sdc_reg_read(wbm, SdcRegs.RESPONSE0)
        busy_flag = not (rsp0 & SdcOcrFlds.BUSY)
        tout -= 1
    # if tout == 0:
    #     raise SdcToutException()


async def sdc_delay_us(delay_us):
    await Timer(delay_us, units="us")


async def sdc_setup_card_to_transfer(wbm: WishboneMaster):
    sdc_rca = 0
    await sdc_go_to_idle(wbm)
    await sdc_delay_us(10)

    await sdc_send_if_cond(wbm)
    await sdc_delay_us(10)

    # await sdc_send_op_cond(wbm)
    # await sdc_delay_us(10)

    wbm.log.info("CMD2")
    await sdc_send_cmd(wbm, SdcCommands.CMD2 | SdcRspType.RSP_R2, 0)
    await sdc_delay_us(10)

    wbm.log.info("CMD3")
    await sdc_send_cmd(wbm, SdcCommands.CMD3 | SdcRspType.RSP_R6, 0)
    rsp0 = await sdc_reg_read(wbm, SdcRegs.RESPONSE0)
    sdc_rca = (rsp0.integer >> 16) & 0xffff
    wbm.log.info("SD card RCA  : {:04x}".format(sdc_rca))
    await sdc_delay_us(10)

    wbm.log.info("CMD7")
    await sdc_send_cmd(wbm, SdcCommands.CMD7 | SdcRspType.RSP_R1, (sdc_rca << 16))
    await sdc_delay_us(10)

    wbm.log.info("CMD55")
    await sdc_send_cmd(wbm, SdcCommands.CMD55 | SdcRspType.RSP_R1, 0)

    wbm.log.info("ACMD6")
    await sdc_delay_us(10)
    await sdc_send_cmd(wbm, SdcCommands.ACMD6 | SdcRspType.RSP_R1, 2)


async def sdc_wait_for_data_finish(wbm: WishboneMaster):
    result = 0
    while result == 0:
        result = await sdc_reg_read(wbm, SdcRegs.DATA_EVENT_STATUS)

    if result != SdcDataEventStatus.OK:
        raise SdcDataEventStatusException(result)

    # Clear IRQ
    await sdc_reg_write(wbm, SdcRegs.DATA_EVENT_STATUS, 0)


async def sdc_stop_data_trans(wbm: WishboneMaster):
    await sdc_send_cmd(wbm, SdcCommands.CMD12 | SdcRspType.RSP_R1b, 0)


async def sdc_write_blocks(wbm: WishboneMaster, dst_lba: int, src_adr: int, blk_n: int):
    await sdc_reg_write(wbm, SdcRegs.DST_SRC_ADDRESS, src_adr)
    await sdc_reg_write(wbm, SdcRegs.BLKOCK_SIZE, 512 - 1)
    await sdc_reg_write(wbm, SdcRegs.BLKOCK_COUNT, blk_n - 1)

    arg = dst_lba
    cmd = SdcRspType.RSP_R1 | SdcDataTransCfg.WR
    if blk_n > 1:
        cmd = cmd | SdcCommands.CMD25
    else:
        cmd = cmd | SdcCommands.CMD24

    await sdc_send_cmd(wbm, cmd, arg)
    await sdc_wait_for_data_finish(wbm)

    if blk_n > 1:
        await sdc_stop_data_trans(wbm)


async def sdc_read_blocks(wbm: WishboneMaster, src_lba: int, dst_adr: int, blk_n: int):
    await sdc_reg_write(wbm, SdcRegs.DST_SRC_ADDRESS, dst_adr)
    await sdc_reg_write(wbm, SdcRegs.BLKOCK_SIZE, 512 - 1)
    await sdc_reg_write(wbm, SdcRegs.BLKOCK_COUNT, blk_n - 1)

    arg = src_lba
    cmd = SdcRspType.RSP_R1 | SdcDataTransCfg.RD
    if blk_n > 1:
        cmd = cmd | SdcCommands.CMD18
    else:
        cmd = cmd | SdcCommands.CMD17

    await sdc_send_cmd(wbm, cmd, arg)
    await sdc_wait_for_data_finish(wbm)

    if blk_n > 1:
        await sdc_stop_data_trans(wbm)
