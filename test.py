from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto
from nodalhdl.core.diagram import Diagram, Structure, StructureBox
from nodalhdl.basic.arith import Addition
from nodalhdl.core.hdl import HDLFileModel


print('哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈')


class TestDiagram(Diagram): # 无参 Diagram 示例
    @staticmethod
    def setup(args):
        # 创建结构
        res = Structure("test_diagram")
        
        # 声明 IO Ports, 必须 perfectly IO-wrapped, 类型不确定可使用 Auto 或其他 undetermined 类型待推导
        ab = res.add_port("ab", Bundle[{"a": Input[UInt[8]], "b": Input[UInt[8]]}])
        c = res.add_port("c", Input[UInt[4]])
        z = res.add_port("z", Output[Auto])
        
        # 添加 Box
        add_ab = res.add_box("add_ab", Addition[UInt[8], UInt[8]])
        add_abc = res.add_box("add_abc", Addition[Auto, Auto])
        
        # 添加连接关系 / 非 IO 节点
        res.connect(ab.a, add_ab.IO.op1)
        res.connect(ab.b, add_ab.IO.op2)
        res.connect(add_ab.IO.res, add_abc.IO.op1)
        res.connect(c, add_abc.IO.op2)
        res.connect(add_abc.IO.res, z)
        
        return res


print('=======================================================')


s = Structure("test")

bi = s.add_port("bi", Bundle[{"i": Input[UInt[2]], "o": Output[Auto]}])
t = s.add_port("t", Input[UInt[4]]) # 改成 undetermined 测试 Addition 的反向推导 (未实现)
n = s.add_port("n", Input[UInt[8]])
m = s.add_port("m", Input[UInt[8]])

td = s.add_box("td", TestDiagram)
add_ti = s.add_box("add_ti", Addition[Auto, Auto])
add_o = s.add_box("add_o", Addition[UInt[8], UInt[4]])

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


print('=======================================================')


s.instantiate(in_situ = True, reserve_safe_structure = True)
s.deduction()


print('=======================================================')


# s.apply_runtime() # 注释: update_runtime_id 后 s 的 推导需要重新进行; 不注释: s 上次推导已经 determined, 并被 apply_runtime 固定, 再次推导可直接结束
s.reset_runtime()
s.deduction()


print('=======================================================')


print(add_ti.structure.name)
print(td.structure.boxes['add_abc'].structure.name) # 这俩应该一致, 都是 Addition[Auto, Auto], 所以生成 hdl 时需要有 namespace 机制


print('=======================================================')


from nodalhdl.core.hdl import write_to_files

h = s.generation()
write_to_files(h.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")


# p = Addition[UInt[8], UInt[8]].structure_template.generation()
# p.add_port("op1", "in", UInt[8])
# p.add_port("op2", "in", UInt[8])
# p.add_port("res", "out", UInt[8])
# # print(p.emit_vhdl()["addition_UInt_8_UInt_8.vhd"])

# r = HDLFileModel("test_submodule")
# r.add_port("op1", "in", UInt[8])  
# r.add_port("op2", "in", UInt[8])
# r.add_port("res", "out", UInt[8])
# r.inst_component("add", p, {"op1": "op1", "op2": "op2", "res": "res"})
# # print(r.emit_vhdl()["vhdl_test_submodule.vhd"])

# t = HDLFileModel("test_module")
# t.add_port("a", "in", UInt[8])
# t.add_port("b", "in", Bundle[{"x": SInt[3], "y": Float, "z": Bundle[{"p": UInt[8], "q": Bit}]}])
# t.add_port("c", "out", Bits[8])
# t.add_port("d", "out", UInt[8])
# t.add_signal("node_1", UInt[8])
# t.add_signal("node_2", UInt[8])
# t.add_signal("node_3", UInt[8])
# t.add_signal("node_4", UInt[8])
# t.inst_component("add", p, {"op1": "node_1", "op2": "node_2", "res": "node_3"})
# t.add_assignment("node_1", "a")
# t.add_assignment("node_2", "b.z.p")
# t.add_assignment("c", "node_3")
# t.inst_component("ts", r, {"op1": "node_1", "op2": "node_2", "res": "node_4"})
# t.add_assignment("d", "node_4")
# # print(t.emit_vhdl()["types.vhd"])
# # print(t.emit_vhdl()["vhdl_test_module.vhd"])

# write_to_files(t.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")


# TODO 推导后结构变更, runtime 信息过期, 这一点尚未测试!


# print('=======================================================')


# print(id(s))
# print(id(s.boxes['add_ti'].structure))
# # print(s.boxes['td'].structure.boxes['add_ab'].free)
# # print(s.boxes['td'].structure.boxes['add_ab'])
# print(s.boxes['add_ti'].free)
# print(s.boxes['add_ti'])

# ss = s.instantiate(in_situ = True, reserve_safe_structure = True)

# print(id(ss))
# print(id(ss.boxes['add_ti'].structure))
# # print(ss.boxes['td'].structure.boxes['add_ab'].free)
# # print(ss.boxes['td'].structure.boxes['add_ab'])
# print(ss.boxes['add_ti'].free)
# print(ss.boxes['add_ti'])


# print('=======================================================')


# T = TestDiagram
# s = T.structure_template

# b1: StructureBox = s.boxes['add_ab']
# b2: StructureBox = s.boxes['add_abc']

# print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
# print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

# b1.update_structure(b2.structure)

# print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
# print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

