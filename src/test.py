from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Bundle, UInt8
from nodalhdl.core.diagram import Diagram, Structure, Addition, TestDiagram


print('=======================================================')


# T = Addition[UInt8, UInt8]
# s = T.structure_template

# print(s.EEB.IO.res.signal_type.determined)

T = TestDiagram

print(T.structure_template)

