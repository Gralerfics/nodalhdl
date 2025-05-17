from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.basic.arith import *
from nodalhdl.py.core import *


def us_to_s(us: ComputeElement, T: SignalType) -> ComputeElement:
    assert us.type.belong(UInt[64])
    
    _s = us.s
    u = _s.add_substructure(f"itime_convertor", CustomVHDLOperator(
        {"i": UInt[64]},
        {"o": T},
        f"o <= '0' & i({20 + T.W_int - 1} downto {20 - T.W_frac});",
        _unique_name = f"ITimeConvertor_UInt_64_{T}"
    ))
    _s.connect(us.node, u.IO.i)
    return ComputeElement(_s, runtime_node = u.IO.o)

