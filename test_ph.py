from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.operator import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


s = Structure()

a = s.add_port("a", Input[Bits[3]])
b = s.add_port("b", Input[UInt[7]])
c = s.add_port("c", Input[SInt[4]])
# z = s.add_port("z", Output[Bits[14]])
z = s.add_port("z", Output[Auto])

uc = s.add_substructure("uc", BitsOperator[(3, 7, 4), (14, ), "VHDL", "o0 <= i0 & i1 & i2;"])

s.connect(a, uc.IO.i0)
s.connect(b, uc.IO.i1)
s.connect(c, uc.IO.i2)
s.connect(uc.IO.o0, z)



rid_s = RuntimeId.create()
s.deduction(rid_s)
print(s.runtime_info(rid_s))

model_s = s.generation(rid_s)
emit_to_files(model_s.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

