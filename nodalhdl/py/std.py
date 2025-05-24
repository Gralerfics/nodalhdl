# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from ..core.signal import *
from ..core.structure import *
from ..basic_arch.bits import *

from .core import *
from .core import _constant


def _fixed(x: ComputeElement, target_t: SignalType) -> ComputeElement:
    _s = x.s
    
    if x.type.belong(FixedPoint):
        L = x.type.W_frac + target_t.W - target_t.W_frac - 1
        R = x.type.W_frac - target_t.W_frac
        L_complement = max(L - x.type.W + 1, 0)
        R_complement = max(-R, 0)
        L_complement_bit = "i(i'high)" if x.type.belong(SFixedPoint) else "'0'"
        
        u = _s.add_substructure(f"to_sfixed", CustomVHDLOperator(
            {"i": x.type},
            {"o": target_t},
            f"o <= " +
                (f"(1 to {L_complement} => {L_complement_bit}) & " if L_complement > 0 else "") +
                f"i({min(L, x.type.W - 1)} downto {max(R, 0)})" +
                (f" & (1 to {R_complement} => '0')" if R_complement > 0 else "") +
                ";",
            _unique_name = f"Convert_{x.type}_{target_t}"
        ))
        _s.connect(x.node, u.IO.i)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        raise NotImplementedError

def ufixed(x: ComputeElement, int_width: int, frac_width: int) -> ComputeElement:
    return _fixed(x, UFixedPoint[int_width, frac_width])

def sfixed(x: ComputeElement, int_width: int, frac_width: int) -> ComputeElement:
    return _fixed(x, SFixedPoint[int_width, frac_width])


def uint(x: ComputeElement, width: int) -> ComputeElement:
    return ufixed(x, width, 0)

def sint(x: ComputeElement, width: int) -> ComputeElement:
    return sfixed(x, width - 1, 0)


def mux(cond, false_value: ComputeElement, true_value: ComputeElement):
    if isinstance(cond, ComputeElement):
        assert isinstance(false_value, ComputeElement) or isinstance(false_value, ComputeElement) # 都不是 CE 的话无法确定输出的位宽
        _s = cond.s
        
        if isinstance(false_value, (float, int)):
            false_value = _constant(_s, true_value.type(false_value))
        elif isinstance(true_value, (float, int)):
            true_value = _constant(_s, false_value.type(true_value))
        
        assert false_value.s == true_value.s and false_value.type == true_value.type and cond.type.W == 1
        
        u = _s.add_substructure("mux", BinaryMultiplexer(false_value.type))
        _s.connect(cond.node, u.IO.sel)
        _s.connect(false_value.node, u.IO.i0)
        _s.connect(true_value.node, u.IO.i1)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        return false_value if cond else true_value

