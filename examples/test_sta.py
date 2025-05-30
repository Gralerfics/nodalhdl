# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic_arch.bits import *
from nodalhdl.basic_arch.arith import *
from nodalhdl.core.hdl import *
from nodalhdl.timing.sta import VivadoSTA
from nodalhdl.timing.pipelining import pipelining

from typing import List

import time


def AddU4U4U4() -> Structure:
    s = Structure(unique_name = "Add_UInt_4_UInt_4_UInt_4")
    
    op1 = s.add_port("op1", Input[UInt[4]])
    op2 = s.add_port("op2", Input[UInt[4]])
    op3 = s.add_port("op3", Input[UInt[4]])
    res = s.add_port("res", Output[Auto])
    
    add_12 = s.add_substructure("add_12", BitsAdd(UInt[4], UInt[4]))
    add_123 = s.add_substructure("add_123", BitsAdd(UInt[4], UInt[4]))
    
    s.connect(op1, add_12.IO.a)
    s.connect(op2, add_12.IO.b)
    s.connect(add_12.IO.r, add_123.IO.a)
    s.connect(op3, add_123.IO.b)
    s.connect(add_123.IO.r, res)
    
    return s

add_u4_u4_u4 = AddU4U4U4()

add_auto_auto = BitsAdd(Auto, Auto)

def M1() -> Structure:
    s = Structure("m1")
    
    a = s.add_port("a", Input[UInt[4]])
    b = s.add_port("b", Input[UInt[4]])
    c = s.add_port("c", Input[UInt[4]])
    o = s.add_port("o", Output[Auto])
    
    x = s.add_substructure("x", BitsAdd(UInt[4], UInt[4]))
    y = s.add_substructure("y", add_u4_u4_u4)
    z = s.add_substructure("z", Constants(c0 = UInt[4](10)))
    
    s.connect(z.IO.c0, x.IO.a)
    s.connect(a, y.IO.op1)
    s.connect(b, y.IO.op2)
    s.connect(c, y.IO.op3)
    s.connect(y.IO.res, x.IO.b)
    s.connect(x.IO.r, o)
    
    return s

m1 = M1()

def AddWrapper(t1: SignalType, t2: SignalType) -> Structure:
    s = Structure()
    
    i1 = s.add_port("i1", Input[t1])
    i2 = s.add_port("i2", Input[t2])
    o = s.add_port("o", Output[Auto])
    
    adder = s.add_substructure("adder", add_auto_auto)
    
    s.connect(i1, adder.IO.a)
    s.connect(i2, adder.IO.b)
    s.connect(o, adder.IO.r)

    return s

addw = AddWrapper(Auto, Auto)

def M2() -> Structure:
    s = Structure()
    
    B_t = Bundle[{"xy": Bundle[{"x": UInt[4], "y": UInt[5]}], "z": UInt[6]}]
    
    a = s.add_port("a", Input[UInt[4]])
    b = s.add_port("b", Input[UInt[4]])
    c = s.add_port("c", Input[UInt[4]])
    x = s.add_port("x", Input[UInt[4]]) # 8
    o = s.add_port("o", Output[Auto])
    u1o = s.add_port("u1o", Output[Auto])
    Bi = s.add_port("Bi", Input[B_t])
    Bo = s.add_port("Bo", Output[Auto])
    
    u1 = s.add_substructure("u1", m1)
    u2 = s.add_substructure("u2", addw)
    u3 = s.add_substructure("u3", CustomVHDLOperator(
        {"i": B_t},
        {"o": UInt[5]},
        "o <= i.xy.y;"
    )) # Decomposition(B_t, ".xy.y", "z"))
    
    s.connect(a, u1.IO.a)
    s.connect(b, u1.IO.b)
    s.connect(c, u1.IO.c)
    s.connect(u1.IO.o, u2.IO.i1)
    s.connect(x, u2.IO.i2)
    s.connect(u2.IO.o, o)
    s.connect(u1.IO.o, u1o)
    s.connect(Bi, u3.IO.i)
    s.connect(u3.IO.o, Bo) # s.connect(u3.IO.o.xy.y, Bo)

    return s


m2 = M2()

m2.singletonize()
m2.expand()
rid = RuntimeId.create()
m2.deduction(rid)
print(m2.runtime_info(rid))

t = time.time()
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_test", vivado_executable_path = "vivado.bat")
sta.analyse(m2, rid)
print(f"STA : {time.time() - t}")

for subs_inst_name, subs in m2.substructures.items():
    print(subs_inst_name, subs.get_runtime(rid.next(subs_inst_name)).timing_info)

