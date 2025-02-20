from nodalhdl.core.signal import *
from nodalhdl.core.diagram import *


class TestNode(Diagram): # 无参 Diagram 示例
    @staticmethod
    def setup(args) -> DiagramStructure:
        pass # TODO
        return DiagramStructure()


print('=======================================================')
S = Bundle[{
    "a": UInt[8],
    "b": Bit,
    "c": Bundle[{
        "x": SInt[3],
        "y": SInt[5]
    }],
    "T": Float
}]
s = S()
print(s.a)
print(s.c)
print(s.c.x)
print(s.T)
print(S.T)
print(S.T["c"].T)
# print(s.c.T)

# I = Input[UInt16]
# print(I.__name__)
# print(I.T)
# O = Output[UInt8]
# print(O.__name__)
# print(O.T)

# U1 = Addition[UInt[4], UInt[6]]
# u1 = U1()
# print(U1)

# U2 = Addition[UInt[4], UInt[6]]
# print(U2)

# U3 = Addition[UInt[6], UInt[4]]
# print(U3)

# print(U3.deduction())

# ut = TestNode()
