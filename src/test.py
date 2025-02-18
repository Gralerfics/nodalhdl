from nodalhdl.core.signal import *
# from nodalhdl.core.operator import *
from nodalhdl.core.diagram import *

# A = Slice[7, 0]
# print(A.__name__)
# print(A.indices)

# B = And[UInt[8], UInt[4]]
# print(B.__name__)
# print(B.T_op1)
# print(B.T_op2)
# print(B.a)

print('=============================')
C = FloatingPoint[11, 22]()
print(C.W_frac)
