from nodalhdl.core.signal import *
from nodalhdl.core.diagram import *


class TestNode(Diagram): # 无参 Diagram 示例
    @staticmethod
    def setup(args) -> DiagramStructure:
        pass # TODO
        return DiagramStructure()


print('=======================================================')
U1 = Addition[UInt[4], UInt[6]]
# u1 = U1()

# u2 = TestNode()
