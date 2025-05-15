from nodalhdl.core.signal import Bundle
from nodalhdl.py.core import Engine

from typing import List


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


def shader(x, y):
    return x + y


if __name__ == "__main__":
    engine = Engine()
    
    s = engine.combinational_to_structure(shader)
    
    pass

