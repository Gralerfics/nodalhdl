from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Float, Bundle, Input, Output, Auto
from nodalhdl.core.structure import DiagramType, Diagram, Structure, RuntimeId
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
        add_ab = res.add_substructure("add_ab", Addition[UInt[8], UInt[8]].structure)
        add_abc = res.add_substructure("add_abc", Addition[Auto, Auto].structure)
        
        # 添加连接关系 / 非 IO 节点
        res.connect(ab.a, add_ab.IO.op1)
        res.connect(ab.b, add_ab.IO.op2)
        res.connect(add_ab.IO.res, add_abc.IO.op1)
        res.connect(c, add_abc.IO.op2)
        res.connect(add_abc.IO.res, z)
        
        return res


print('=======================================================')


s = Structure("test")

print(TestDiagram.structure.substructures["add_ab"].ports_inside_flipped.res.origin_signal_type)

