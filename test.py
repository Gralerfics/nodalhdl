from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto
from nodalhdl.core.structure import Structure, RuntimeId
from nodalhdl.basic.arith import Addition
from nodalhdl.core.hdl import HDLFileModel


print('哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈')


# T: DiagramType = Addition[UInt[8], UInt[8]]

# print(T.structure.ports_inside_flipped.op1.origin_signal_type)
# print(T.structure.ports_inside_flipped.op2.origin_signal_type)
# print(T.structure.ports_inside_flipped.res.origin_signal_type)

# rid = RuntimeId()
# T.structure.deduction(rid)
# print(T.structure.ports_inside_flipped.res.get_type(rid))


# print('=======================================================')


def TestDiagram() -> Structure:
    # 创建结构
    res = Structure()
    
    # 声明 IO Ports, 必须 perfectly IO-wrapped, 类型不确定可使用 Auto 或其他 undetermined 类型待推导
    ab = res.add_port("ab", Bundle[{"a": Input[UInt[8]], "b": Input[UInt[8]]}])
    c = res.add_port("c", Input[UInt[4]])
    z = res.add_port("z", Output[Auto])
    
    # 添加 Substructure
    add_ab = res.add_substructure("add_ab", Addition(UInt[8], UInt[8]))
    print(add_ab.proxy_structure.id)
    add_abc = res.add_substructure("add_abc", Addition(Auto, Auto))
    
    # 添加连接关系 / 非 IO 节点
    res.connect(ab.a, add_ab.IO.op1)
    res.connect(ab.b, add_ab.IO.op2)
    res.connect(add_ab.IO.res, add_abc.IO.op1)
    res.connect(c, add_abc.IO.op2)
    res.connect(add_abc.IO.res, z)
    add_ab.IO.res.set_latency(2)
    add_abc.IO.res.set_latency(1)
    
    rid = RuntimeId()
    res.deduction(rid)
    res.apply_runtime(rid)
    
    return res

testDiagram = TestDiagram()
print(testDiagram.substructures["add_ab"].ports_inside_flipped.res.origin_signal_type)
print(testDiagram.is_originally_determined())


print('A =======================================================')


s = Structure()

bi = s.add_port("bi", Bundle[{"i": Input[UInt[2]], "o": Output[Auto]}])
t = s.add_port("t", Input[UInt]) # 改成 undetermined 测试 Addition 的反向推导 (未实现)
n = s.add_port("n", Input[UInt[8]])
m = s.add_port("m", Input[UInt[8]])

td = s.add_substructure("td", TestDiagram())
add_ti = s.add_substructure("add_ti", Addition(Auto, Auto))
add_o = s.add_substructure("add_o", Addition(UInt[8], UInt[4]))

add_ti_out = s.add_node("add_ti_out", Auto)

s.connect(t, add_ti.IO.op1)
s.connect(bi.i, add_ti.IO.op2)
s.connect(add_ti.IO.res, add_ti_out)

s.connect(n, td.IO.ab.a)
s.connect(m, td.IO.ab.b)
s.connect(add_ti_out, td.IO.c)

s.connect(td.IO.z, add_o.IO.op1)
s.connect(add_ti_out, add_o.IO.op2)

s.connect(add_o.IO.res, bi.o)

# s.connect(t, td.c) # test multi-driven signal exception

print(s.substructures["td"].ports_inside_flipped.z.origin_signal_type)


print('B =======================================================')


rid = RuntimeId()

s.deduction(rid)
s.apply_runtime(rid) # TODO

print(s.substructures["add_ti"].ports_outside[s.id].op1.get_type(rid))
print(s.substructures["add_ti"].ports_outside[s.id].op2.get_type(rid))

print(s.substructures["add_ti"].ports_inside_flipped.op1.get_type(rid))
print(s.substructures["add_ti"].ports_inside_flipped.op2.get_type(rid))

print(s.substructures["td"].substructures["add_ab"].runtimes.keys(), rid)


print('C =======================================================')


from nodalhdl.core.hdl import write_to_files
import shutil

h = s.generation(rid)
# print("2")
# h = s.generation(rid)

shutil.rmtree("C:/Workspace/test_project/test_project.srcs/sources_1/new")
write_to_files(h.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

