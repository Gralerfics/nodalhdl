from ..core.signal import *
from ..core.structure import *
from ..core.reusable import *
from .bits import *


"""
    这里的结构生成函数不是当作自动结构使用的，没有那种一边推导一边自动选择结构版本 (arch) 的功能；
        TODO 重要：这种功能得想办法加上，不然自动类型推导能力就有点受限（无法根据运行时类型决定结构的构造），主要问题就是推导和结构构造的先后问题。
            但，先放着，还有别的。
    只是将不同类型的同类操作合并到一个函数，省得写多个名字类似的函数；
    调用时都应该给定态类型（部分例如 Add 等给 Auto 其实也不会有问题，但还是定死吧）。
    这里有点像用类型携带一些配置信息的意思。
            就是说这里参数的类型不见得是和类型推导有关系，只是给用户当信息传入。
            TODO 要不不用类型传了用字符串传省得混淆，然后全 Bits。
        比如原始一点可以用一个参数表示乘法器输出是否要截断，下面则是通过判断传入的是 Bits 还是 XInt 决定，前者完整，后者要求输入等长并且输出截断。
        这样合理吗? 是否显得多余还降低了灵活性? 但这样比设定原始的参数简洁, 后者光给参数命名就很抽象了（但 IP 核貌似就算这种路子）。
        没事反正 arith 里不是唯一的生成方式，需要的话可以到别处创建个 HighlyParameterizedMultiplier 之流，这里只提供基本的。
"""


class Constants(UniquelyNamedReusable):
    """
        要求确保 DIDO.
    """
    @staticmethod
    def setup(**constants) -> Structure:
        """
            Constants({"<constant_name_0>": constant_object_0, ...})
        """
        pairs: List[Tuple[str, SignalValue]] = list(constants.items()) # fix the order
        
        def _assign(sub_wire_name: str, c: SignalValue):
            res = []
            if isinstance(c, BundleValue):
                raise NotImplementedError # TODO
                # for k, v in c._bundle_objects.items():
                #     res.extend(_assign(sub_wire_name + "." + k, v))
            elif isinstance(c, BitsValue):
                res.append(f"{sub_wire_name} <= \"{c.to_bits_string()}\";")
            return res
        
        s = Structure()
        
        ports = [s.add_port(name, Output[value.type]) for name, value in pairs]
        
        opt = s.add_substructure("opt", CustomVHDLOperator(
            {},
            {name: value.type for name, value in pairs},
            "\n".join([line for name, value in pairs for line in _assign(name, value)]),
            _unique_name = Constants.naming(**constants) + "_Core"
        ))
        
        for port in ports:
            s.connect(opt.IO.access(port.name), port)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_md5_16()


class EqualTypesAdd(BitsAdd):
    deduction = OperatorDeductionTemplates.equal_types("a", "b", "r")

def Add(t1: SignalType, t2: SignalType) -> Structure: # [NOTICE] 不需要套一层 UniquelyNamedReusable, 就用里面的 BitsAdd 即可
    """
        1. 任意宽 Bits 相加, 按较长操作数位宽截断 (即忽略最高位进位).
        2. 同宽 UInt 相加, 同宽度截断 (即忽略最高位进位).
        3. 同宽 SInt 相加, 同宽度截断 (即忽略最高位进位).
        4. 同格式 UFixedPoint 相加, 同格式截断 (即忽略最高位进位).
        5. 同格式 SFixedPoint 相加, 同格式截断 (即忽略最高位进位).
        
        要求确保 DIDO.
    """
    assert t1.is_determined and t2.is_determined
    
    if t1.base_equal(Bits) and t2.base_equal(Bits):
        return BitsAdd(t1, t2)
    if t1.base_equal(UInt) and t2.base_equal(UInt) and t1.W == t2.W:
        return EqualTypesAdd(t1, t2)
    elif t1.base_equal(SInt) and t2.base_equal(SInt) and t1.W == t2.W:
        return EqualTypesAdd(t1, t2)
    elif t1.base_equal(UFixedPoint) and t2.base_equal(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return EqualTypesAdd(t1, t2)
    elif t1.base_equal(SFixedPoint) and t2.base_equal(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return EqualTypesAdd(t1, t2)
    else:
        raise NotImplementedError


class EqualTypesSubtract(BitsSubtract):
    deduction = OperatorDeductionTemplates.equal_types("a", "b", "r")

def Subtract(t1: SignalType, t2: SignalType) -> Structure:
    """
        要求确保 DIDO.
    """
    assert t1.is_determined and t2.is_determined
    
    if t1.base_equal(Bits) and t2.base_equal(Bits):
        return BitsSubtract(t1, t2)
    if t1.base_equal(UInt) and t2.base_equal(UInt) and t1.W == t2.W:
        return EqualTypesSubtract(t1, t2)
    elif t1.base_equal(SInt) and t2.base_equal(SInt) and t1.W == t2.W:
        return EqualTypesSubtract(t1, t2)
    elif t1.base_equal(UFixedPoint) and t2.base_equal(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return EqualTypesSubtract(t1, t2)
    elif t1.base_equal(SFixedPoint) and t2.base_equal(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
        return EqualTypesSubtract(t1, t2)
    else:
        raise NotImplementedError


# ConstantMul?


class Multiply(UniquelyNamedReusable): # TODO 改: https://blog.csdn.net/m0_51783792/article/details/123970639
    """
        1. 任意宽 Bits 相乘, 当作无符号乘法, 输出位宽为输入位宽之和, 即不截断.
        2. 任意宽 UInt 相乘, 同 Bits, int_truncate 决定是否截断 (若截断则按较长操作数位宽截断).
        3. 任意宽 SInt 相乘, 有符号乘法, int_truncate 决定是否截断 (若截断则按较长操作数位宽截断).
        4. 同形式 UFixedPoint 相乘, 按 Bits (或 UInt 不截断) 相乘后原格式截断.
        5. 同形式 SFixedPoint 相乘, 按 SInt 相乘后原格式截断.
        
        要求确保 DIDO.
    """
    @staticmethod
    def setup(t1: SignalType, t2: SignalType, int_truncate: bool = True) -> Structure:
        # [NOTICE] 用 Bits 的版本后截断有点浪费, 实际上可以省去很多, 不过不知道多余的是不是能被优化, 但如果有进寄存器那估计没的优化吧; 下同
        assert t1.is_determined and t2.is_determined
        
        s = Structure()
        a = s.add_port("a", Input[t1])
        b = s.add_port("b", Input[t2])
        
        lW, sW = max(t1.W, t2.W), min(t1.W, t2.W)
        lP, sP = (a, b) if t1.W > t2.W else (b, a)
        
        this_setup_unique_name = Multiply.naming(t1, t2, int_truncate)
        
        if t1.base_equal(Bits) and t2.base_equal(Bits): # no truncation
            r = s.add_port("r", Output[Bits[t1.W + t2.W]])
            
            gen = s.add_substructure("gen_addends", CustomVHDLOperator(
                {"long": Bits[lW], "short": Bits[sW]},
                {f"addend_{idx}": Bits[lW + idx + 1] for idx in range(sW)}, # plus 1 to avoid overflow
                f"long_shifted <= '0' & long & (1 to {sW - 1} => '0');\n" +
                    "\n".join([f"addend_{idx} <= long_shifted({lW + sW - 1} downto {sW - idx - 1}) when short({idx}) = '1' else (others => '0');" for idx in range(sW)]),
                f"signal long_shifted: std_logic_vector({lW + sW - 1} downto 0);",
                _unique_name = this_setup_unique_name + "_AddendsGenerator"
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
        
        elif t1.base_equal(UInt) and t2.base_equal(UInt):
            r = s.add_port("r", Output[UInt[lW if int_truncate else t1.W + t2.W]]) # 输出位宽与截断与否有关
                
            sint_mul = s.add_substructure("bits_mul", Multiply(Bits[t1.W], Bits[t2.W]))
            s.connect(a, sint_mul.IO.a)
            s.connect(b, sint_mul.IO.b)
            
            if int_truncate: # 按高位截断
                tc = s.add_substructure("tc", CustomVHDLOperator(
                    {"i": Bits[t1.W + t2.W]},
                    {"o": Bits[lW]},
                    f"o <= i({lW - 1} downto 0);",
                    _unique_name = this_setup_unique_name + "_Truncator"
                ))
                s.connect(sint_mul.IO.r, tc.IO.i)
                s.connect(tc.IO.o, r)
            else: # 不截断直接连接
                s.connect(sint_mul.IO.r, r)
        
        elif t1.base_equal(SInt) and t2.base_equal(SInt): # https://www.cnblogs.com/jiaotaiyang/p/17576277.html
            r = s.add_port("r", Output[SInt[lW if int_truncate else t1.W + t2.W]]) # 同上
            
            gen = s.add_substructure("gen_addends", CustomVHDLOperator(
                {"long": Bits[lW], "short": Bits[sW]},
                {
                    **{f"addend_{idx}": SInt[lW + sW] for idx in range(sW - 1)},
                    "subend": SInt[lW + sW]
                },
                f"long_shifted <= long & (1 to {sW - 1} => '0');\n" +
                    f"long_sign <= long(long'high);\n" +
                    "\n".join([
                        (f"addend_{idx}" if idx < sW - 1 else "subend") + 
                        f" <= (1 to {sW - idx} => long_sign) & long_shifted({lW + sW - 2} downto {sW - idx - 1}) when short({idx}) = '1' else (others => '0');"
                    for idx in range(sW)]),
                f"signal long_shifted: std_logic_vector({lW + sW - 2} downto 0);\n" +
                    f"signal long_sign: std_logic;",
                _unique_name = this_setup_unique_name + "_AddendsGenerator"
            ))
            s.connect(lP, gen.IO.long)
            s.connect(sP, gen.IO.short)
            
            adder_idx = 0
            last_P = []
            P = [gen.IO.access(f"addend_{idx}") for idx in range(sW - 1)]
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
            
            subtractor = s.add_substructure(
                f"subtractor",
                BitsSubtract(last_P[i - 1].origin_signal_type.T, last_P[i].origin_signal_type.T)
            )
            s.connect(P[0], subtractor.IO.a)
            s.connect(gen.IO.access("subend"), subtractor.IO.b)
            
            if int_truncate: # 按高位截断
                tc = s.add_substructure("tc", CustomVHDLOperator(
                    {"i": Bits[t1.W + t2.W]},
                    {"o": Bits[lW]},
                    f"o <= i({lW - 1} downto 0);",
                    _unique_name = this_setup_unique_name + "_Truncator"
                ))
                s.connect(subtractor.IO.r, tc.IO.i)
                s.connect(tc.IO.o, r)
            else: # 不截断直接连接
                s.connect(subtractor.IO.r, r)
        
        elif t1.base_equal(UFixedPoint) and t2.base_equal(UFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
            r = s.add_port("r", Output[t1])
            
            bits_mul = s.add_substructure("bits_mul", Multiply(Bits[t1.W], Bits[t2.W]))
            s.connect(a, bits_mul.IO.a)
            s.connect(b, bits_mul.IO.b)
            
            tc = s.add_substructure("tc", CustomVHDLOperator(
                {"i": Bits[t1.W + t2.W]},
                {"o": t1},
                f"o <= i({t1.W_frac + t1.W - 1} downto {t1.W_frac});",
                _unique_name = this_setup_unique_name + "_Truncator"
            ))
            s.connect(bits_mul.IO.r, tc.IO.i)
            s.connect(tc.IO.o, r)
        
        elif t1.base_equal(SFixedPoint) and t2.base_equal(SFixedPoint) and t1.W_int == t2.W_int and t1.W_frac == t2.W_frac:
            r = s.add_port("r", Output[t1])
            
            sint_mul = s.add_substructure("sint_mul", Multiply(SInt[t1.W], SInt[t2.W], int_truncate = False))
            s.connect(a, sint_mul.IO.a)
            s.connect(b, sint_mul.IO.b)
            
            tc = s.add_substructure("tc", CustomVHDLOperator(
                {"i": Bits[t1.W + t2.W]},
                {"o": Bits[t1.W]},
                f"o <= i({t1.W_frac + t1.W - 1} downto {t1.W_frac});",
                _unique_name = this_setup_unique_name + "_Truncator"
            ))
            s.connect(sint_mul.IO.r, tc.IO.i)
            s.connect(tc.IO.o, r)
        
        else:
            raise NotImplementedError
        
        return s
    
    @classmethod
    def naming(cls, t1: SignalType, t2: SignalType, int_truncate: bool = True):
        return f"{cls.__name__}_{t1}_{t2}{"_Truncated" if int_truncate else ""}"
    # naming = UniqueNamingTemplates.args_kwargs_all_values()


class Division(UniquelyNamedReusable):
    """
        # 1. 任意宽 Bits 相乘, 当作无符号乘法, 输出位宽为输入位宽之和, 即不截断.
        # 2. 任意宽 UInt 相乘, 同 Bits, int_truncate 决定是否截断 (若截断则按较长操作数位宽截断).
        # 3. 任意宽 SInt 相乘, 有符号乘法, int_truncate 决定是否截断 (若截断则按较长操作数位宽截断).
        # 4. 同形式 UFixedPoint 相乘, 按 Bits (或 UInt 不截断) 相乘后原格式截断.
        # 5. 同形式 SFixedPoint 相乘, 按 SInt 相乘后原格式截断.
        TODO
        1. 
        
        要求确保 DIDO.
    """
    @staticmethod
    def setup(t1: SignalType, t2: SignalType) -> Structure:
        pass
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

