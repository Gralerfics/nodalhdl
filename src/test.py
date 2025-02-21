from nodalhdl.core.signal import UInt, SInt, Bits, Bit, Bundle
from nodalhdl.core.diagram import Diagram, Structure, Addition


class TestNode(Diagram): # 无参 Diagram 示例
    @staticmethod
    def setup(args):
        pass # TODO
        return Structure()


print('=======================================================')
# S = Bundle[{
#     "a": UInt[8],
#     "b": Bit,
#     "c": Bundle[{
#         "x": SInt[3],
#         "y": SInt[5]
#     }]
# }]
# s = S()
# print(S.a)
# print(s.a)
# print(S.c.x)
# print(s.c.x)
# print(S.__bundle_types)
# print(S.c.__bundle_types)

# I = Input[UInt16]
# print(I.__name__)
# print(I.T)
# O = Output[UInt8]
# print(O.__name__)
# print(O.T)

U1 = Addition[UInt[4], UInt[6]]
u1 = U1()
print(U1)
print(u1)

# U2 = Addition[UInt[4], UInt[6]]
# print(U2)

# U3 = Addition[UInt[6], UInt[4]]
# print(U3)

# print(U3.deduction())

# ut = TestNode()
