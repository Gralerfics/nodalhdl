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


# T = Addition[UInt8, UInt8]
# s = T.structure_template

# print(Addition[Auto, Auto].structure_template.EEB.IO)

T = TestDiagram
s = T.structure_template
print(s.boxes)

eeb = s.EEB
b1: StructureBox = s.boxes['add_ab']
b2: StructureBox = s.boxes['add_abc']

print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

b1.set_structure(b2.structure)

print("b1: ", b1.IO, '\n', b1.structure.EEB.IO)
print("b2: ", b2.IO, '\n', b2.structure.EEB.IO)

# print("s eeb IO: ", eeb.IO)
# print("b1 IO: ", b1.IO)
# print("b1 eeb IO: ", b1.structure.EEB.IO)
# print("b2 IO: ", b2.IO)

# print(b1.IO.op1.located_net.nodes)
# print(b1.IO.res.located_net.nodes)

# print(b2.IO.op1.located_box.name)

# print(b1.structure.determined)

# Addition[UInt8, UInt8].structure_template.custom_vhdl(None)

# print(Addition[UInt8, UInt8].structure_template.EEB.IO_dict)

