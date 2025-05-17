from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.basic.arith import *
from nodalhdl.py.core import *


def sfixed(x: ComputeElement, int_width: int, frac_width: int) -> ComputeElement:
    _s = x.s
    target_t = SFixedPoint[int_width, frac_width]
    
    if x.type.belong(UFixedPoint):
        u = _s.add_substructure(f"sfixed", CustomVHDLOperator(
            {"i": x.type},
            {"o": target_t},
            f"o <= '0' & i({x.type.W_frac + target_t.W_int - 1} downto {x.type.W_frac - target_t.W_frac});",
            _unique_name = f"{x.type}_To_{target_t}_Convertor"
        ))
        _s.connect(x.node, u.IO.i)
        return ComputeElement(_s, runtime_node = u.IO.o)
    
    else:
        raise NotImplementedError


def ce_shift(x: ComputeElement, n: int) -> ComputeElement: # left: n > 0
    _s = x.s
    vhdl_func = "shift_left" if n >= 0 else "shift_right"
    
    if x.type.belong(SFixedPoint): # arithmetic shifting
        vhdl_type = "signed"
    elif x.type.belong(Bits): # logic shifting
        vhdl_type = "unsigned"
    else:
        raise NotImplementedError
    
    u = _s.add_substructure(f"shifter", CustomVHDLOperator(
        {"i": x.type},
        {"o": x.type},
        f"o <= std_logic_vector({vhdl_func}({vhdl_type}(i), {abs(n)}));",
        _unique_name = f"Shifter_{str(n).replace("-", "Neg")}_{x.type}"
    ))
    _s.connect(x.node, u.IO.i)
    return ComputeElement(_s, runtime_node = u.IO.o)


def ce_add(x, y) -> ComputeElement:
    if isinstance(x, ComputeElement) and isinstance(y, ComputeElement):
        assert x.s == y.s
        _s = x.s
        
        u = _s.add_substructure(f"adder", Add(T, T))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    
    elif isinstance(x, ComputeElement) and isinstance(y, (float, int)):
        _s = x.s
        
        # TODO
        
        u = _s.add_substructure(f"adder", Add(T, T))
        _s.connect(x.node, u.IO.a)
        _s.connect(, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    
    elif isinstance(y, ComputeElement) and isinstance(x, (float, int)):
        return ce_add(y, x) # add is commutative
    else:
        raise NotImplementedError

