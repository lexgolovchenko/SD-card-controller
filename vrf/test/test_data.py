
from cocotb_coverage.crv import Randomized
from random import randint

from typing import List

class TestData(Randomized):
    BLOCK_SIZE = 512

    def __init__(self, blk_min=1, blk_max=1):
        Randomized.__init__(self)
        self.BLK_NUM_MIN = blk_min
        self.BLK_NUM_MAX = blk_max
        self.block_num = 0
        self.add_rand("block_num", list(range(self.BLK_NUM_MIN, self.BLK_NUM_MAX+1)))
        self.data8 = []
        self.data32 = []

    def post_randomize(self):
        # print("block_num : " + str(self.block_num))
        for _ in range(self.block_num):
            new_block = []
            for _ in range(self.BLOCK_SIZE):
                new_block.append(randint(0, 255))
            self.data8.append(new_block)
        self.data32 = self.__convert_to_words32()

    def __convert_to_words32(self) -> List[List[int]]:
        """
        LSB first! Because of SD card memory
        """
        data32 = []
        for blk8 in self.data8:
            blk32 = []
            for i in range(0, len(blk8), 4):
                w32 = blk8[i+3] | (blk8[i+2] << 8) | (blk8[i+1] << 16) | (blk8[i] << 24)
                blk32.append(w32)
            data32.append(blk32)
        return data32

    def hexstr8(self) -> str:
        s = ""
        for blk8 in self.data8:
            for w8 in blk8:
                sval = "{:02x} ".format(w8)
                s += sval
            s += "\n"
        return s

    def hexstr32(self) -> str:
        s = ""
        idx = 0
        for blk32 in self.data32:
            for w32 in blk32:
                sval = "{:08x} ".format(w32)
                s += sval
            s += "\n"
        return s
