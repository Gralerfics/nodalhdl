from ..core.signal import *
from ..core.structure import Structure, RuntimeId
from .bits import BitsAdd, BitsSubtract, CustomVHDLOperator

import textwrap


ariths_pool: Dict[str, Structure] = {} # TODO 写个装饰器用函数


"""
    这里的结构生成函数不是当作自动结构使用的，没有那种一边推导一边自动选择结构版本 (arch) 的功能；
        TODO 重要：这种功能得想办法加上，不然自动类型推导能力就有点受限（无法根据运行时类型决定结构的构造），主要问题就是推导和结构构造的先后问题。
            但，先放着，还有别的。
    只是将不同类型的同类操作合并到一个函数，省得写多个名字类似的函数；
    调用时都应该给定态类型（部分例如 Add 等给 Auto 其实也不会有问题，但还是定死吧）。
    这里有点像用类型携带一些配置信息的意思。
        比如原始一点可以用一个参数表示乘法器输出是否要截断，下面则是通过判断传入的是 Bits 还是 XInt 决定，前者完整，后者要求输入等长并且输出截断。
        这样合理吗? 是否显得多余还降低了灵活性? 但这样比设定原始的参数简洁, 后者光给参数命名就很抽象了（但 IP 核貌似就算这种路子）。
        没事反正 arith 里不是唯一的生成方式，需要的话可以到别处创建个 HighlyParameterizedMultiplier 之流，这里只提供基本的。
    
    TODO 要不要在 Structure 元素中加一些方法，例如对两个端口执行 add，自动生成加法器结构和连接这种，方便 hls。
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
    
    opt = s.add_substructure("opt", CustomVHDLOperator(
        {},
        {name: type(value) for name, value in constants.items()},
        "\n".join([line for name, value in pairs for line in _assign(name, value)])
    ))
    
    for port in ports:
        s.connect(opt.IO.access(port.name), port)
    
    return s


def Add(t1: SignalType, t2: SignalType) -> Structure:
    assert t1.determined and t2.determined
    
    if t1.bases(Bits) and t2.bases(Bits):
        return BitsAdd(t1, t2)
    if t1.bases(UInt) and t2.bases(UInt) and t1.W == t2.W:
        return BitsAdd(t1, t2)
    elif t1.bases(SInt) and t2.bases(SInt) and t1.W == t2.W:
        return BitsAdd(t1, t2)
    elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsAdd(t1, t2)
    elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsAdd(t1, t2)
    else:
        raise NotImplementedError


def Subtract(t1: SignalType, t2: SignalType) -> Structure:
    assert t1.determined and t2.determined
    
    if t1.bases(Bits) and t2.bases(Bits):
        return BitsSubtract[t1, t2]
    if t1.bases(UInt) and t2.bases(UInt) and t1.W == t2.W:
        return BitsSubtract[t1, t2]
    elif t1.bases(SInt) and t2.bases(SInt) and t1.W == t2.W:
        return BitsSubtract[t1, t2]
    elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsSubtract[t1, t2]
    elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return BitsSubtract[t1, t2]
    else:
        raise NotImplementedError


# ConstantMul? HLS?


def Multiply(t1: SignalType, t2: SignalType) -> Structure:
    assert t1.determined and t2.determined
    
    unique_name = f"Arith_Multiply_{t1}_{t2}" # should be a valid string and unique across all operators
    if unique_name in ariths_pool: # return existed reusable structure (will not be in the pool if not reusable)
        return ariths_pool[unique_name]
    
    s = Structure()
    a = s.add_port("a", Input[t1])
    b = s.add_port("b", Input[t2])
    
    if t1.bases(Bits) and t2.bases(Bits): # no truncation
        r = s.add_port("r", Output[Bits[t1.W + t2.W]])
        
        lW, sW = max(t1.W, t2.W), min(t1.W, t2.W)
        lP, sP = (a, b) if t1.W > t2.W else (b, a)
        
        gen = s.add_substructure("gen_addends", CustomVHDLOperator(
            {"long": Bits[lW], "short": Bits[sW]},
            {f"addend_{idx}": Bits[lW + idx + 1] for idx in range(sW)}, # plus 1 to avoid overflow
            f"long_shifted <= long & \"{"0" * (sW - 1)}\";" +
                "\n".join([f"addend_{idx} <= \"0\" & long_shifted({lW + sW - 2} downto {sW - idx - 1}) when short({idx}) = '1' else (others => '0');" for idx in range(sW)]),
            f"signal long_shifted: std_logic_vector({lW + sW - 2} downto 0);"
        ))
        
        s.connect(lP, gen.IO.long)
        s.connect(sP, gen.IO.short)
        
        adder_idx = 0
        last_P = []
        P = [gen.IO.access(f"addend_{idx}") for idx in range(sW)]
        while len(P) > 1:
            last_P, P = P, []
            
            for i in range(1, len(last_P), 2): # add adjacent ports
                new_adder = s.add_substructure(
                    f"adder_{adder_idx}",
                    BitsAdd(last_P[i - 1].origin_signal_type.T, last_P[i].origin_signal_type.T)
                )
                
                s.connect(last_P[i - 1], new_adder.IO.a)
                s.connect(last_P[i], new_adder.IO.b)
                P.append(new_adder.IO.r)
                
                adder_idx += 1
            
            if len(last_P) % 2 == 1: # fallout port
                P.append(last_P[-1])
        
        s.connect(P[0], r)
    
    elif t1.bases(UInt) and t2.bases(UInt) and t1.W == t2.W: # truncation ([NOTICE] 用 Bits 的版本后截断有点浪费, 实际上可以省去很多, 不过不知道多余的是不是能被优化, 但如果有进寄存器那估计没的优化吧; 下同)
        r = s.add_port("r", Output[UInt[t1.W]])
        
        bits_mul = s.add_substructure("bits_mul", Multiply(Bits[t1.W], Bits[t2.W]))
        tc = s.add_substructure("tc", CustomVHDLOperator(
            {"i": Bits[t1.W + t2.W]},
            {"o": Bits[t1.W]},
            f"o <= i({t1.W - 1} downto 0)"
        ))
        
        s.connect(a, bits_mul.IO.a)
        s.connect(b, bits_mul.IO.b)
        s.connect(bits_mul.IO.r, tc.IO.i)
        s.connect(tc.IO.o, r)
    
    elif t1.bases(SInt) and t2.bases(SInt) and t1.W == t2.W:
        pass # TODO
    
    elif t1.bases(UFixedPoint) and t2.bases(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        r = s.add_port("r", Output[UInt[t1.W]])
        
        bits_mul = s.add_substructure("bits_mul", Multiply(Bits[t1.W], Bits[t2.W]))
        tc = s.add_substructure("tc", CustomVHDLOperator(
            {"i": Bits[t1.W + t2.W]},
            {"o": Bits[t1.W]},
            f"o <= i({t1.W_frac + t1.W - 1} downto {t1.W_frac})"
        ))
        
        s.connect(a, bits_mul.IO.a)
        s.connect(b, bits_mul.IO.b)
        s.connect(bits_mul.IO.r, tc.IO.i)
        s.connect(tc.IO.o, r)
    
    elif t1.bases(SFixedPoint) and t2.bases(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        pass # TODO
    
    else:
        raise NotImplementedError

    rid = RuntimeId.create()
    s.deduction(rid)
    if s.is_runtime_applicable:
        s.apply_runtime(rid)
    
    if s.is_reusable: # only save reusable structures
        s.unique_name = unique_name
        ariths_pool[unique_name] = s
    
    return s

