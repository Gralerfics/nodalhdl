from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *

from nodalhdl.py.core import *
from nodalhdl.py.core import _constant


def ufixed(x: ComputeElement, int_width: int, frac_width: int) -> ComputeElement:
    _s = x.s
    target_t = UFixedPoint[int_width, frac_width]
    
    if x.type.belong(FixedPoint):
        L = x.type.W_frac + target_t.W_int - 1
        R = x.type.W_frac - target_t.W_frac
        L_complement = max(L - x.type.W + 1, 0)
        R_complement = max(-R, 0)
        
        u = _s.add_substructure(f"to_ufixed", CustomVHDLOperator(
            {"i": x.type},
            {"o": target_t},
            f"o <= {f"(1 to {L_complement} => '0') & " if L_complement > 0 else ""}i({min(L, x.type.W - 1)} downto {max(R, 0)}){f" & (1 to {R_complement} => '0')" if R_complement > 0 else ""};",
            _unique_name = f"Convert_{x.type}_{target_t}"
        ))
        _s.connect(x.node, u.IO.i)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        raise NotImplementedError


def sfixed(x: ComputeElement, int_width: int, frac_width: int) -> ComputeElement:
    _s = x.s
    target_t = SFixedPoint[int_width, frac_width]
    
    if x.type.belong(FixedPoint):
        L = x.type.W_frac + target_t.W_int - 1
        R = x.type.W_frac - target_t.W_frac
        L_complement = max(L - x.type.W + 1, 0)
        R_complement = max(-R, 0)
        L_complement_bit = "i(i'high)" if x.type.belong(SFixedPoint) else "'0'"
        
        u = _s.add_substructure(f"to_sfixed", CustomVHDLOperator(
            {"i": x.type},
            {"o": target_t},
            f"o <= (1 to {L_complement + 1} => {L_complement_bit}) & i({min(L, x.type.W - 1)} downto {max(R, 0)}){f" & (1 to {R_complement} => '0')" if R_complement > 0 else ""};",
            _unique_name = f"Convert_{x.type}_{target_t}"
        ))
        _s.connect(x.node, u.IO.i)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        raise NotImplementedError


def uint(x: ComputeElement, width: int) -> ComputeElement:
    return ufixed(x, width, 0)


def mux(cond, x: ComputeElement, y: ComputeElement):
    if isinstance(cond, ComputeElement):
        assert x.s == y.s and x.type.equal(y.type) and cond.type.W == 1
        _s = x.s
        
        u = _s.add_substructure("mux", BinaryMultiplexer(x.type))
        _s.connect(cond.node, u.IO.sel)
        _s.connect(x.node, u.IO.i0)
        _s.connect(y.node, u.IO.i1)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        return x if cond else y

