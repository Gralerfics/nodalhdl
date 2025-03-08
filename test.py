from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto
from nodalhdl.core.structure import DiagramType, Diagram, Structure, RuntimeId
from nodalhdl.basic.arith import Addition
from nodalhdl.core.hdl import HDLFileModel


print('哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈')


T: DiagramType = Addition[UInt[8], UInt[8]]

print(T.structure.ports_inside_flipped.op1.origin_signal_type)
print(T.structure.ports_inside_flipped.op2.origin_signal_type)
print(T.structure.ports_inside_flipped.res.origin_signal_type)

rid = RuntimeId()
T.structure.deduction(rid)
print(T.structure.ports_inside_flipped.res.get_type(rid))

