from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto, SignalType
from nodalhdl.core.structure import Structure, RuntimeId
from nodalhdl.basic.operator import Adder, GetAttribute
from nodalhdl.core.hdl import HDLFileModel


m2: Structure = Structure.load_dill("m2.dill")

rid = RuntimeId.create()
m2.deduction(rid)

print(m2.runtime_info(rid))

