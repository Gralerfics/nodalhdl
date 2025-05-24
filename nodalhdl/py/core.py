# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from ..core.signal import *
from ..core.structure import *
from ..basic_arch.bits import *
from ..basic_arch.arith import *

from typing import List
# import functools


# @functools.total_ordering
class ComputeElement:
    """
        TODO ComputeElement (CE).
        暂时先针对组合逻辑，直接在 CE 对象中存 Structure 的引用, 其运算返回的新 CE 对象中继续携带 Structure, 但已经添加了东西.
        
        有一个问题就是这里所有的运算都要求输出类型是 fully-determined 的, 否则就可能会连锁地出现问题;
        这也包括外面的一系列函数, 只要是对 CE 做操作的都需要. 这也是合理的, 因为 HLS 层本身就大量缺乏类型提示, 必须前向推导.
        反过来, 也可以说对于所有操作来说, 输入都一定是 determined 类型.
        
        TODO *1, +0, */2^n 都可以优化; 常数放进一个模块; ...
    """
    def __init__(self, s: Structure, input_port_name: str = None, input_port_type: SignalType = None, runtime_node: Node = None):
        self.s = s
        
        # runtime
        self.node: Node = runtime_node
        if input_port_name is not None and input_port_type is not None: # input port
            if runtime_node is not None:
                raise Exception("runtime_node should be ignored when input_port information is provided")
            self.node = self.s.add_port(input_port_name, Input[input_port_type])
    
    @property
    def type(self):
        return self.node.origin_signal_type.io_clear()
    
    def output(self, output_port_name: str): # output port
        output_port = self.s.add_port(output_port_name, Output[Auto])
        self.s.connect(self.node, output_port)
    
    """
        operations.
    """
    def _arith_op(self, other, func):
        if isinstance(other, ComputeElement):
            return func(self, other)
        elif isinstance(other, (float, int)):
            other_ce: ComputeElement = _constant(self.s, self.type(other))
            return self._arith_op(other_ce, func)
        else:
            return NotImplemented
    
    def _arith_rop(self, other, func):
        if isinstance(other, (float, int)):
            other_ce: ComputeElement = _constant(self.s, self.type(other))
            return other_ce._arith_op(self, func)
        else:
            return NotImplemented
    
    def __add__(self, other): return self._arith_op(other, _add_ce)
    def __sub__(self, other): return self._arith_op(other, _sub_ce)
    def __mul__(self, other): return self._arith_op(other, _mul_ce)
    def __truediv__(self, other): return self._arith_op(other, _div_ce)
    def __mod__(self, other): return self._arith_op(other, _mod_ce)
    def __eq__(self, other): return self._arith_op(other, _eq_ce) # __req__?
    
    def __radd__(self, other): return self._arith_rop(other, _add_ce)
    def __rsub__(self, other): return self._arith_rop(other, _sub_ce)
    def __rmul__(self, other): return self._arith_rop(other, _mul_ce)
    def __rtruediv__(self, other): return self._arith_rop(other, _div_ce)
    def __rmod__(self, other): return self._arith_rop(other, _mod_ce)
    
    def __lshift__(self, other): return _shift_int(self, other)
    def __rshift__(self, other): return _shift_int(self, -other)
    
    def __neg__(self): return 0 - self
    def __pos__(self): return self
    
    def __matmul__(self, other): # concatenation
        if isinstance(other, ComputeElement):
            return _concate_ce(self, other)
        elif isinstance(other, str):
            other_ce: ComputeElement = _constant(self.s, Bits[len(other)](other))
            return _concate_ce(self, other_ce)
        else:
            return NotImplemented
    
    def __rmatmul__(self, other):
        if isinstance(other, str):
            other_ce: ComputeElement = _constant(self.s, Bits[len(other)](other))
            return _concate_ce(other_ce, self)
        else:
            return NotImplemented
    
    def __getitem__(self, item): # slicing, closed interval
        if isinstance(item, slice):
            high = item.start if item.start is not None else self.W - 1
            low = item.stop if item.stop is not None else 0
            if high >= low:
                elements = list(range(high, low - 1, -1))
            else:
                elements = list(range(low, high + 1))
        elif isinstance(item, int):
            elements = [item]
        else:
            raise NotImplementedError
        
        return _slice_ce(self, elements)


def _constant(_s: Structure, constant: SignalValue) -> 'ComputeElement':
    u = _s.add_substructure("constant", Constants(o = constant))
    return ComputeElement(_s, runtime_node = u.IO.o)

def _shift_int(x: 'ComputeElement', n: int) -> 'ComputeElement': # left: n > 0
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
        _unique_name = f"Shift_{str(n).replace("-", "Neg")}_{x.type}"
    ))
    _s.connect(x.node, u.IO.i)
    return ComputeElement(_s, runtime_node = u.IO.o)

def _add_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type # should be equivalent
    _s = x.s

    if x.type.belong(FixedPoint):
        u = _s.add_substructure(f"adder", BitsAdd(x.type))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        u.IO.r.update_origin_type(x.type) # TODO determined-input-fully-determined-output 约束的要求来自 hls 层, 故在这里直接修改新子结构实例的外部端口实例类型
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _sub_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type # should be equivalent
    _s = x.s
    
    if x.type.belong(FixedPoint):
        u = _s.add_substructure(f"subtractor", BitsSubtract(x.type))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        u.IO.r.update_origin_type(x.type)
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _mul_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type # should be equivalent TODO Bits? 某些不用截断的需求
    _s = x.s
    
    if x.type.belong(FixedPoint):
        # u = _s.add_substructure(f"multiplier", FixedPointMultiply(x.type))
        u = _s.add_substructure(f"multiplier", FixedPointMultiplyVHDL(x.type)) # TODO 模块有点太多, 用整个的试一下; DSP 数量有限
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _div_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type
    _s = x.s
    
    if x.type.belong(FixedPoint):
        u = _s.add_substructure(f"divider", FixedPointDivide(x.type))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _mod_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type
    _s = x.s
    
    if x.type.belong(FixedPoint):
        u = _s.add_substructure(f"divider", FixedPointModulus(x.type))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _eq_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s and x.type == y.type
    _s = x.s
    
    if x.type.belong(Bits):
        u = _s.add_substructure(f"equal", BitsEqualTo(x.type))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.r)
    else:
        raise NotImplementedError

def _concate_ce(x: 'ComputeElement', y: 'ComputeElement') -> 'ComputeElement':
    assert x.s == y.s
    _s = x.s
    
    if x.type.belong(Bits):
        u = _s.add_substructure(f"concatenator", CustomVHDLOperator(
            {"a": x.type, "b": y.type},
            {"o": Bits[x.type.W + y.type.W]},
            "o <= a & b;",
            _unique_name = f"Concatenate_{x.type}_{y.type}"
        ))
        _s.connect(x.node, u.IO.a)
        _s.connect(y.node, u.IO.b)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        raise NotImplementedError

def _slice_ce(x: 'ComputeElement', elements: List[int]):
    _s = x.s
    
    if x.type.belong(Bits):
        u = _s.add_substructure(f"slicer", CustomVHDLOperator(
            {"i": x.type},
            {"o": Bits[len(elements)]},
            f"o <= {" & ".join([f"i({idx})" for idx in elements])};" if len(elements) > 1 else f"o <= (0 => i({elements[0]}));",
            _unique_name = f"Slice_{"_".join(map(str, elements))}"
        ))
        _s.connect(x.node, u.IO.i)
        return ComputeElement(_s, runtime_node = u.IO.o)
    else:
        raise NotImplementedError


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]


# def mul(a, b):
#     a.concat(suffix = "0" * (b.T.W - 1))
#     r = uint(a.T.W + b.T.W)(0) # ComputeElement, .T.name = "uint", .T.W = a.T.W + b.T.W, .V = 0 TODO ?
#     for i in range(b.T.W):
#         r += a[:i]
#     return r