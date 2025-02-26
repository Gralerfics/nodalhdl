from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Bundle, UInt8, Input, Output, Auto
from nodalhdl.core.diagram import Diagram, Structure, StructureBox
from nodalhdl.basic.arith import Addition


class TestDiagram(Diagram): # 带参 Diagram 示例
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
t = s.add_port("t", Input[UInt[4]])
n = s.add_port("n", Input[UInt[8]])
m = s.add_port("m", Input[UInt[8]])

td = s.add_box("td", TestDiagram)
add_ti = s.add_box("add_ti", Addition[Auto, Auto])
add_o = s.add_box("add_o", Addition[UInt[8], UInt[8]])

s.connect(n, td.IO.ab.a)
s.connect(m, td.IO.ab.b)
s.connect(add_ti.IO.res, td.IO.c)

s.connect(t, add_ti.IO.op1)
s.connect(bi.i, add_ti.IO.op2)

s.connect(td.IO.z, add_o.IO.op1)
s.connect(add_ti.IO.res, add_o.IO.op2)

s.connect(add_o.IO.res, bi.o)


print('=======================================================')


print(s.boxes['td'].structure.boxes['add_ab'].free)
print(s.boxes['td'].structure.boxes['add_ab'])

ss = s.instantiate(in_situ = False, reserve_safe_structure = False)

print(ss.boxes['td'].structure.boxes['add_ab'].free)
print(ss.boxes['td'].structure.boxes['add_ab'])


print('=======================================================')


# T = TestDiagram
# s = T.structure_template

# b1: StructureBox = s.boxes['add_ab']
# b2: StructureBox = s.boxes['add_abc']

# print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
# print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

# b1.update_structure(b2.structure)

# print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
# print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

