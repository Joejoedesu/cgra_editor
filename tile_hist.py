from enum import Enum
from pnr_graph import TileType

th1 = {(1, 0) : [[TileType.IO16,TileType.IO1],["I0","i1"]],(1, 1) : [[TileType.REG],["r6"]],(0, 0) : [[TileType.IO16],["I3"]],(0, 1) : [[TileType.REG],["r4"]],(3, 1) : [[TileType.MEM],["m2"]],(0, 2) : [[TileType.PE],["p5"]],(2, 1) : [[TileType.REG],["r7"]]}

def get_th():
    return th1