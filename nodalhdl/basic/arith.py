from .bits import *


"""
    TODO
    这里的结构生成函数不是当作自动结构使用的，没有那种一边推导一边自动选择结构版本 (arch) 的功能；
    只是将不同类型的同类操作合并到一个函数，省得写多个名字类似的函数；
    调用时都应该给定类型。
    
    TODO
    要不要在 Structure 元素中加一些方法，例如对两个端口执行 add，自动生成加法器结构和连接这种，方便 hls。
"""


def Constants(**constants) -> Structure:
    """
        Constants({"<constant_name_0>": constant_object_0, ...})
    """
    pairs = list(constants.items()) # fix the order
    
    def _assign(sub_wire_name: str, c: Signal):
        res = []
        if isinstance(c, Bundle):
            for k, v in c._bundle_objects.items():
                res.extend(_assign(sub_wire_name + "." + k, v))
        elif isinstance(c, Bits):
            res.append(f"{sub_wire_name} <= \"{c.to_bits_string()}\";")
        return res
    
    s = Structure()
    
    ports = [s.add_port(name, Output[type(value)]) for name, value in pairs]
    
    opt = s.add_substructure("opt", CustomVHDLOperator[
        {},
        {name: type(value) for name, value in constants.items()},
        "\n".join([line for name, value in pairs for line in _assign(name, value)])
    ])
    
    for port in ports:
        s.connect(opt.IO.access(port.name), port)
    
    return s


def Add(t1: SignalType, t2: SignalType) -> Structure:
    if t1.bases(Bits) and t2.bases(Bits):
        return BitsAdd[t1, t2]
    if t1.bases(UInt) and t2.bases(UInt):
        return BitsAdd[t1, t2]
    elif t1.bases(SInt) and t2.bases(SInt):
        return BitsAdd[t1, t2]
    elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsAdd[t1, t2]
    elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsAdd[t1, t2]
    else:
        raise NotImplementedError


def Subtract(t1: SignalType, t2: SignalType) -> Structure:
    if t1.bases(Bits) and t2.bases(Bits):
        return BitsSubtract[t1, t2]
    if t1.bases(UInt) and t2.bases(UInt):
        return BitsSubtract[t1, t2]
    elif t1.bases(SInt) and t2.bases(SInt):
        return BitsSubtract[t1, t2]
    elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsSubtract[t1, t2]
    elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsSubtract[t1, t2]
    else:
        raise NotImplementedError


# def Multiply(t1: SignalType, t2: SignalType) -> Structure:
#     s = Structure()
#     op1 = s.add_port("op1", Input[t1])
#     op2 = s.add_port("op2", Input[t2])
#     # res = 
    
#     if t1.bases(UInt) and t2.bases(UInt):
#         pass # TODO
#     elif t1.bases(SInt) and t2.bases(SInt):
#         pass # TODO
#     elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
#         pass # TODO
#     elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
#         pass # TODO
#     else:
#         raise NotImplementedError

#     return s

