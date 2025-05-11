from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto, SignalType
from nodalhdl.core.structure import Structure, RuntimeId, StructureProxy
from nodalhdl.basic.bits import *
from nodalhdl.core.hdl import HDLFileModel
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
    
    add_12 = s.add_substructure("add_12", Adder[UInt[4], UInt[4]])
    add_123 = s.add_substructure("add_123", Adder[UInt[4], UInt[4]])
    
    s.connect(op1, add_12.IO.op1)
    s.connect(op2, add_12.IO.op2)
    s.connect(add_12.IO.res, add_123.IO.op1)
    s.connect(op3, add_123.IO.op2)
    s.connect(add_123.IO.res, res)
    
    return s

add_u4_u4_u4 = AddU4U4U4()

def M1() -> Structure:
    s = Structure("m1")
    
    a = s.add_port("a", Input[UInt[4]])
    b = s.add_port("b", Input[UInt[4]])
    c = s.add_port("c", Input[UInt[4]])
    o = s.add_port("o", Output[Auto])
    
    x = s.add_substructure("x", Adder[UInt[4], UInt[4]])
    y = s.add_substructure("y", add_u4_u4_u4)
    z = s.add_substructure("z", Constant[UInt[4](10)])
    
    s.connect(z.IO.c0, x.IO.op1)
    s.connect(a, y.IO.op1)
    s.connect(b, y.IO.op2)
    s.connect(c, y.IO.op3)
    s.connect(y.IO.res, x.IO.op2)
    s.connect(x.IO.res, o)

    return s

m1 = M1()

def AddWrapper(t1: SignalType, t2: SignalType) -> Structure:
    s = Structure()
    
    i1 = s.add_port("i1", Input[t1])
    i2 = s.add_port("i2", Input[t2])
    o = s.add_port("o", Output[Auto])
    
    adder = s.add_substructure("adder", Adder[Auto, Auto])
    
    s.connect(i1, adder.IO.op1)
    s.connect(i2, adder.IO.op2)
    s.connect(o, adder.IO.res)

    return s

addw = AddWrapper(Auto, Auto)

def M2() -> Structure:
    s = Structure()
    
    B_t = Bundle[{"xy": Bundle[{"x": UInt[4], "y": UInt[5]}], "z": UInt[6]}]
    
    a = s.add_port("a", Input[UInt[4]])
    b = s.add_port("b", Input[UInt[4]])
    c = s.add_port("c", Input[UInt[4]])
    x = s.add_port("x", Input[UInt[8]])
    o = s.add_port("o", Output[Auto])
    u1o = s.add_port("u1o", Output[Auto])
    Bi = s.add_port("Bi", Input[B_t])
    Bo = s.add_port("Bo", Output[Auto])
    
    u1 = s.add_substructure("u1", m1)
    u2 = s.add_substructure("u2", addw)
    u3 = s.add_substructure("u3", Decomposition[B_t, ".xy.y", "z"])
    
    s.connect(a, u1.IO.a)
    s.connect(b, u1.IO.b)
    s.connect(c, u1.IO.c)
    s.connect(u1.IO.o, u2.IO.i1)
    s.connect(x, u2.IO.i2)
    s.connect(u2.IO.o, o)
    s.connect(u1.IO.o, u1o)
    s.connect(Bi, u3.IO.i)
    s.connect(u3.IO.o.xy.y, Bo)

    return s

m2 = M2()

rid_m2 = RuntimeId.create()
m2.deduction(rid_m2)

print(m2.runtime_info(rid_m2))


def M3() -> Structure:
    s = Structure()
    
    ipq = s.add_port("ipq", Input[UInt[2]])
    ip = s.add_port("ip", Input[UInt[6]])
    iq = s.add_port("iq", Input[UInt[1]])
    ir1 = s.add_port("ir1", Input[UInt[4]])
    ir2 = s.add_port("ir2", Input[UInt[4]])
    qo = s.add_port("qo", Output[Auto])
    po = s.add_port("po", Output[Auto])
    ro = s.add_port("ro", Output[Auto])
    
    p = s.add_substructure("p", addw)
    q = s.add_substructure("q", Adder[Auto, Auto])
    r = s.add_substructure("r", Adder[UInt[4], UInt[4]])
    
    Nipq = s.add_node("Nipq", Auto)
    s.connect(ipq, Nipq)
    
    s.connect(Nipq, p.IO.i1)
    s.connect(ip, p.IO.i2)
    s.connect(p.IO.o, po)
    
    s.connect(iq, q.IO.op1)
    s.connect(Nipq, q.IO.op2)
    s.connect(q.IO.res, qo)
    
    s.connect(ir1, r.IO.op1)
    s.connect(ir2, r.IO.op2)
    s.connect(r.IO.res, ro)

    return s

m3 = M3()

rid_m3 = RuntimeId.create()
m3.deduction(rid_m3)

print(m2.runtime_info(rid_m2))
print(m3.runtime_info(rid_m3))


print('m2.gen ==============================================================================================================')


from nodalhdl.core.hdl import emit_to_files

model = m2.generation(rid_m2)

emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")


print('m2.dup ==============================================================================================================')


m2_dup = m2.duplicate()

rid_m2_dup = RuntimeId.create()
m2_dup.deduction(rid_m2_dup)

print(m2.runtime_info(rid_m2))
print(m2_dup.runtime_info(rid_m2_dup))

print(m2.get_nets())
print(m2_dup.get_nets())

# print(m2_dup.substructures["u1"].ports_outside[(m2_dup.id, "u1")].t.located_net)
# print(m2_dup.ports_inside_flipped.t.located_net)
# print([x for x in m2_dup.ports_inside_flipped.t.located_net.nodes_weak])
# print([x for x in m2_dup.ports_inside_flipped.t.located_net.runtimes.keys()])


print('m2.strip ==============================================================================================================')


print(m2.runtime_info(rid_m2))
print(m2.substructures["u2"].ports_outside.keys())
print(m3.substructures["p"].ports_outside.keys())
print("")

del rid_m2
m2.strip()

rid_m2_strip = RuntimeId.create()
m2.deduction(rid_m2_strip)

print(m2.runtime_info(rid_m2_strip))
print(m2.substructures["u2"].ports_outside.keys())
print(m3.substructures["p"].ports_outside.keys())


print('m2.singletonize ==============================================================================================================')


del rid_m2_strip
m2.singletonize()

rid_m2_sin = RuntimeId.create()
m2.deduction(rid_m2_sin)

print(m2.runtime_info(rid_m2_sin))
print(m3.runtime_info(rid_m3))

print(m2.is_flattened)


print('m2.singletonize.gen ==============================================================================================================')


model = m2.generation(rid_m2_sin)

emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")


print('m2.singletonize.expand ==============================================================================================================')


del rid_m2_sin
m2.expand(shallow = False)

rid_m2_exp = RuntimeId.create()
m2.deduction(rid_m2_exp)

print(m2.runtime_info(rid_m2_exp))


print('m2.singletonize.gen ==============================================================================================================')


model = m2.generation(rid_m2_exp)

emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")


print('m2.singletonize (sta) ==============================================================================================================')


sta = VivadoSTA(part_name = "xc7a200tfbg484-1", vivado_executable_path = "vivado.bat")
# sta.analyse(m2, rid_m2_exp)
sta.analyse(m2, rid_m2_exp, skip_emitting_and_script_running = True)

for subs_inst_name, subs in m2.substructures.items():
    print(f"{subs_inst_name}: {subs.get_runtime(rid_m2_exp.next(subs_inst_name)).timing_info}")


print('m2.singletonize (pipelining) ==============================================================================================================')


print("Phi_Gr", pipelining(m2, rid_m2_exp, 2, model = "simple")) # , model = "extended"))

# for net in m2.get_nets():
#     for load in net.get_loads():
#         print(net.driver(), "--", net.driver().latency + load.latency, "->", load)


# print('rid test ==============================================================================================================')


# a = RuntimeId("7df1902c04d6541aa0c81a4c9258e0b1")
# b = a.next("u1")
# c = a.next("u3")
# d = a.next("u2")
# e = b.next("z")
# f = b.next("y")
# g = d.next("adder")

# h1 = b.next("x")
# h2 = f.next("add_12")
# h3 = f.next("add_123")

# print(a.id_str[:8])
# print(b.id_str[:8])
# print(c.id_str[:8])
# print(d.id_str[:8])
# print(e.id_str[:8])
# print(f.id_str[:8])
# print(g.id_str[:8])
# print(h1.id_str[:8])
# print(h2.id_str[:8])
# print(h3.id_str[:8])

