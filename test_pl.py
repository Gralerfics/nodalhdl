from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto, SignalType
from nodalhdl.core.structure import Structure, RuntimeId
from nodalhdl.basic.arith import Add, GetAttribute
from nodalhdl.core.hdl import HDLFileModel

import dill


m2: Structure = dill.load(open("m2.dill", "rb"))

rid = RuntimeId.create()
m2.deduction(rid)

# print(m2.runtime_info(rid))

