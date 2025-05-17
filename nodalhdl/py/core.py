from ..core.signal import *
from ..core.structure import *

from .std import ce_shift


class ComputeElement:
    """
        TODO ComputeElement (CE).
        暂时先针对组合逻辑，直接在 CE 对象中存 Structure 的引用, 其运算返回的新 CE 对象中继续携带 Structure, 但已经添加了东西.
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
        ori_type = self.node.origin_signal_type
        return ori_type.T if ori_type.base_belong(IOWrapper) else ori_type
    
    def output(self, output_port_name: str): # output port
        self.s.add_port(output_port_name, Output[Auto])
    
    """
        operations
    """
    def __add__(self, other):
        pass
    
    def __sub__(self, other):
        pass
    
    def __lshift__(self, other):
        pass
    
    def __rshift__(self, other):
        pass


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]


"""
    TODO
    类型基本都用指定的，不指定直接字面量的话自动转，例如小数就变 Float(...) 之类（能不能实现类似 1.0f 的写法啊），整数变 SInt32 之类。
    CE有几种情况：
        表示端口信号（输入）的；
        表示信号（中间结果）的；
        表示常数的；
            常数和变量运算得到常数模块和变量连到算子的结构🤔，
            常数执行可以直接读；
    算符与高级语言特性的运算符直接对应，
        算符内部再去考虑不同类型的行为，
            高级语言运算符也可以重载得到不同的算符情况，
"""

# def mul(a, b):
#     a.concat(suffix = "0" * (b.T.W - 1))
#     r = uint(a.T.W + b.T.W)(0) # ComputeElement, .T.name = "uint", .T.W = a.T.W + b.T.W, .V = 0 TODO ?
#     for i in range(b.T.W):
#         r += a[:i]
#     return r