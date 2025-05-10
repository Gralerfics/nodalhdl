from ..core.signal import *
from .operator import *


def Add(t1: SignalType, t2: SignalType) -> Structure:
    return Adder[t1, t2]

def Subtract(t1: SignalType, t2: SignalType) -> Structure:
    return Subtracter[t1, t2]

def Multiplier(t1: SignalType, t2: SignalType) -> Structure:
    s = Structure()
    op1 = s.add_port("op1", Input[t1])
    op2 = s.add_port("op2", Input[t2])
    
    if t1.belongs(UFixedPoint) and t2.belongs(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        raise NotImplementedError
    elif t1.belongs(SFixedPoint) and t2.belongs(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        pass
    else:
        raise NotImplementedError

    return s

