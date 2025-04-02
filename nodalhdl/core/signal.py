"""
+--------------------------------------------------------------------+
    Signal Types:
        Signal;
        Auto;
        Bits[<width>], Bit, Byte;
        UInt[<width>], UInt8, UInt16, UInt32, UInt64;
        SInt[<width>], SInt8, SInt16, SInt32, SInt64;
        FixedPoint[<integer_width>, <fraction_width>];
        FloatingPoint[<exponent_width>, <fraction_width>], Float, Double;
        Bundle[<members>].
    Examples:
        a = UInt[8]()
        print(isinstance(a, UInt[8]))       # True
        print(isinstance(a, UInt))          # True
        print(isinstance(a, UInt[9]))       # False
        print(isinstance(a, BitsType))      # False
        print(isinstance(a, Bits))          # True
        print(isinstance(a, Signal))        # True
        print(type(a).W)                    # 8

        print(Float.__name__)               # FloatingPoint_8_23
        print(UInt.__name__)                # UInt
        print(SInt[8].__name__)             # SInt_8

        print(isinstance(UInt, SignalType))                 # True (*)
        print(isinstance(UInt[8], SignalType))              # True

        print(type(Signal))                                 # <class '...SignalType'>
        print(type(UInt[8]))                                # <class '...BitsType'>
        print(issubclass(UInt[8], UInt))                    # True
        print(issubclass(UInt[8], BitsType))                # False
        print(issubclass(type(UInt[8]), BitsType))          # True
        print(issubclass(type(UInt[8]), SignalType))        # True

        print(UInt[8].belongs(Bits))                        # True
        print(UInt[8].belongs(Bits[8]))                     # False (*)
        print(UInt[8].equals(UInt[8]))                      # True
        print(UInt[8].equals(UInt[7]))                      # False

        print(UInt.determined)                              # False
        print(UInt[8].determined)                           # True
        print(Bundle[{"a": Input[UInt]}].determined)        # False

        S = Bundle[{
            "a": UInt[8],
            "b": Bit,
            "c": Bundle[{
                "x": SInt[3],
                "y": SInt[5]
            }]
        }]
        s = S()
        print(S.a)                                          # <class '...UInt_8'>
        print(s.a)                                          # <...UInt_8 object at ...>
        print(S.c.x)                                        # <class '...SInt_3'>
        print(s.c.x)                                        # <...SInt_3 object at ...>
        print(S._bundle_types)                              # {'a': <class '...UInt_8'>, 'b': <class '...Bits_1'>, 'c': <class '...Bundle_...'>}
        print(S.c._bundle_types)                            # {'x': <class '...SInt_3'>, 'y': <class '...SInt_5'>}
        
        Input[Bundle[{
            "x": Input[SInt[3]],
            "y": Output[SInt[5]]
        }]]                                                 # SignalTypeException: Nesting is not allowed for IO Wrappers
        
        S = Bundle[{
            "a": Input[UInt[8]],
            "b": Bit
        }]
        print(S.perfectly_io_wrapped)                       # False
        print(S.flip_io())                                  # SignalTypeException: Imperfect IO-wrapped signal type cannot be flipped
        
        S = Bundle[{
            "a": Input[UInt[8]],
            "b": Output[Bit],
            "c": Bundle[{
                "x": Input[SInt[3]],
                "y": Output[SInt[5]]
            }],
            "d": Input[Bundle[{
                "t": Float
            }]]
        }]
        print(S.perfectly_io_wrapped)                       # True
        print(S.flip_io()._bundle_types)                    # {'a': <class '...Output_UInt_8'>, 'b': <class '...Input_Bits_1'>, 'c': <class '...Bundle_...'>, 'd': <class '...Output_Bundle_...'>}
        print(S.flip_io().c._bundle_types)                  # {'x': <class '...Output_SInt_3'>, 'y': <class '...Input_SInt_5'>}
        print(S.flip_io().flip_io() == S)                   # True
        print(S.clear_io()._bundle_types)                   # {'a': <class '...UInt_8'>, 'b': <class '...Bits_1'>, 'c': <class '...Bundle_...'>, 'd': <class '...Bundle_...'>}
        print(S.clear_io().c._bundle_types)                 # {'x': <class '...SInt_3'>, 'y': <class '...SInt_5'>}
    TODO:
        单元测试.
+--------------------------------------------------------------------+
"""

from typing import Dict, List, Union
import hashlib

""" Exceptions """
class SignalTypeException(Exception): pass


""" Metatypes """
class SignalType(type):
    def __call__(cls, *args, **kwds):
        if not cls.determined:
            raise TypeError("Undetermined types cannot be instantiated.")
        else:
            return super().__call__(*args, **kwds)
    
    def __repr__(cls):
        return cls.def_str()
    
    determined = False # i.e. width-determined w.r.t. signals
    io_wrapper_included = False # i.e. whether IO Wrapper is included
    perfectly_io_wrapped = False # i.e. whether is perfectly IO-wrapped
    
    type_pool = {} # ensuring singularity
    
    def instantiate_type(cls, new_cls_name, properties = {}) -> 'SignalType': # `cls` here is the generated class, type(cls) is SignalType or its subclasses
        if not new_cls_name in cls.type_pool.keys():
            new_cls = SignalType(f"{new_cls_name}", (cls, ), {
                **properties,
                "base": cls
            })
            cls.type_pool[new_cls_name] = new_cls
        
        return cls.type_pool.get(new_cls_name)
    
    """
        有关信号类型关系的方法.
        以下这些第一个参数为 signal_type 的方法被 Signal 类型和其子类继承后, 第一个参数相当于 self.
    """
    def normalize(signal_type: 'SignalType'):
        """
            使用 dill 在不同运行中保存和读取 Structure 后, 读取所得 SignalType 和 .signal 中创建的类型虽然内容相同但不再是同一对象,
            导致 ==, is, issubclass 等方法判断结果有误, 这里将 SignalType 转字符串后重新求值得到新环境中的 SignalType 对象以解决这个问题.
            TODO 是否还有其他潜在问题有待发现.
        """
        return eval(str(signal_type))
    
    def equals(signal_type: 'SignalType', other: 'SignalType'):
        signal_type, other = signal_type.normalize(), other.normalize()
        
        return signal_type is other
    
    def belongs(signal_type: 'SignalType', other: 'SignalType'): # 要求从属于 other, 即比 other 更具体 (子类型) 或等同
        signal_type, other = signal_type.normalize(), other.normalize()
        
        return issubclass(signal_type, other)
    
    def merges(signal_type: 'SignalType', other: 'SignalType'): # 合并两个信号类型的信息, 去 IO Wrapper
        """
            IO-ignored.
            applys 本质上是将二者类型信息合并, 并保留 signal_type 的 IO Wrapper 结构.
            merges 传入无 IO Wrapper 的 signal_type, 就使其成为单纯的信息合并.
        """
        t1 = signal_type.clear_io() if signal_type.io_wrapper_included else signal_type
        t2 = other.clear_io() if other.io_wrapper_included else other
        
        return t1.applys(t2)
    
    def applys(signal_type: 'SignalType', other: 'SignalType'): # 将 other 的信息应用到 signal_type 上, other 是忽略 IO 的
        """
            用在需要将无 IO 类型推导结果应用到 port 信号类型上的情况.
        """
        if other.io_wrapper_included:
            other = other.clear_io()
        
        def _apply(d_port: SignalType, d_rtst: SignalType):
            if d_port.equals(Auto):
                return d_rtst
            elif d_rtst.equals(Auto):
                return d_port
            elif d_port.belongs(Input):
                return Input[_apply(d_port.T, d_rtst)]
            elif d_port.belongs(Output):
                return Output[_apply(d_port.T, d_rtst)]
            elif d_port.belongs(Bundle) and d_rtst.belongs(Bundle):
                if d_port._bundle_types.keys() != d_rtst._bundle_types.keys():
                    return None
                
                return Bundle[{key: _apply(T1, T2) for (key, T1), (_, T2) in zip(d_port._bundle_types.items(), d_rtst._bundle_types.items())}]
            elif not d_port.belongs(Bundle) and not d_rtst.belongs(Bundle):
                if d_port.belongs(d_rtst):
                    return d_port
                elif d_rtst.belongs(d_port):
                    return d_rtst
                else:
                    return None
            else:
                return None
        
        res = _apply(signal_type, other)
        if res is None:
            raise SignalTypeException(f"Signal types {signal_type.__name__} and {other.__name__} are conflicting")
        
        return res

    """
        有关 IO Wrapper 的方法.
        Signal type 根据是否有 IO Wrapper 分类:
            (1.) 完全无 IO Wrapper, 为 Non-IO-wrapped.
            (2.) 所有信号上溯皆有且仅有一个 IO Wrapper, 称 Perfectly IO-wrapped.
            (3.) 不完整包裹的, 以及 IO Wrapper 存在嵌套的, 皆为非法.
        在构建 IOWrapper 和 Bundle 时会逐级检查, 并给 io_wrapper_included 和 perfectly_io_wrapped 属性赋值.
        
        flip_io 方法用于翻转 IO Wrapper, 返回翻转后的类型, 并要求输入的信号类型 perfectly_io_wrapped = True.
    """
    def flip_io(signal_type: 'SignalType'): # 递归翻转 IO Wrapper
        if not signal_type.perfectly_io_wrapped:
            raise SignalTypeException(f"Imperfect IO-wrapped signal type cannot be flipped")
        
        def _flip(t: SignalType):
            if t.belongs(Input):
                return Output[t.T]
            elif t.belongs(Output):
                return Input[t.T]
            else: # 一定是 Bundle, 如果是未被包裹的普通信号, 必然通不过 perfectly_io_wrapped 检查
                return Bundle[{key: _flip(T) for key, T in t._bundle_types.items()}]
        
        return _flip(signal_type)
    
    def clear_io(signal_type: 'SignalType'):
        if not signal_type.io_wrapper_included:
            return signal_type
        
        if signal_type.belongs(Input) or signal_type.belongs(Output):
            return signal_type.T
        elif signal_type.belongs(Bundle):
            return Bundle[{key: T.clear_io() for key, T in signal_type._bundle_types.items()}]
        else: # 普通信号
            return signal_type

class BitsType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, int):
            width = item
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{width}",
                {
                    "W": width
                }
            )
            new_cls.determined = True
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<width (int)>]")

class FixedPointType(BitsType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            integer_width, fraction_width = item
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{integer_width}_{fraction_width}",
                {
                    "W": integer_width + fraction_width,
                    "W_int": integer_width,
                    "W_frac": fraction_width
                }
            )
            new_cls.determined = True
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<integer_width (int)>, <fraction_width (int)>]")

class FloatingPointType(BitsType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            exponent_width, fraction_width = item
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{exponent_width}_{fraction_width}",
                {
                    "W": 1 + exponent_width + fraction_width,
                    "W_exp": exponent_width,
                    "W_frac": fraction_width
                }
            )
            new_cls.determined = True
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<exponent_width (int)>, <fraction_width (int)>]")

class IOWrapperType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, SignalType):
            if item.io_wrapper_included: # 不允许 IO Wrapper 套 IO Wrapper
                raise SignalTypeException(f"Nesting is not allowed for IO Wrappers")
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{item.__name__}",
                {
                    "T": item
                }
            )
            new_cls.determined = item.determined # IO Wrapping 后的确定性由内部信号决定
            new_cls.io_wrapper_included = True # 套上后即包含 IO Wrapper
            new_cls.perfectly_io_wrapped = True # 内部无 IO Wrapper 故套上后就是最小单位
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<signal_type (SignalType)>]")

class BundleType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, dict) and all([isinstance(x, SignalType) for x in item.values()]):
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{hashlib.md5(str(item).encode('utf-8')).hexdigest()}",
                {
                    "_bundle_types": item, # 信号名到类型的映射, 维护子信号的名称信息, **item 展开后会和一些内建方法混在一起
                    **item # 方便直接按索引引用信号类型
                }
            )
            new_cls.determined = all([x.determined for x in item.values()]) # 子信号全部确定才确定
            new_cls.io_wrapper_included = any([x.io_wrapper_included for x in item.values()]) # 子信号中有一个包含 IO Wrapper 就包含
            new_cls.perfectly_io_wrapped = all([x.perfectly_io_wrapped for x in item.values()]) # 子信号全部完美包裹才完美包裹
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<members (dict[str, SignalType])>]")


""" Types """
class Signal(metaclass = SignalType): pass

class Auto(Signal):
    @classmethod
    def def_str(cls):
        return "Auto"

class Bits(Auto, metaclass = BitsType):
    @classmethod
    def def_str(cls):
        return f"Bits[{cls.W}]" if hasattr(cls, 'W') else "Bits"

Bit = Bits[1]
Byte = Bits[8]

class UInt(Bits):
    @classmethod
    def def_str(cls):
        return f"UInt[{cls.W}]" if hasattr(cls, 'W') else "UInt"

UInt8 = UInt[8]
UInt16 = UInt[16]
UInt32 = UInt[32]
UInt64 = UInt[64]

class SInt(Bits):
    @classmethod
    def def_str(cls):
        return f"SInt[{cls.W}]" if hasattr(cls, 'W') else "SInt"

Int8 = SInt[8]
Int16 = SInt[16]
Int32 = SInt[32]
Int64 = SInt[64]

class FixedPoint(Bits, metaclass = FixedPointType):
    @classmethod
    def def_str(cls):
        return f"FixedPoint[{cls.W_int}, {cls.W_frac}]" if hasattr(cls, 'W_int') and hasattr(cls, 'W_frac') else "FixedPoint"

class FloatingPoint(Bits, metaclass = FloatingPointType):
    @classmethod
    def def_str(cls):
        return f"FloatingPoint[{cls.W_exp}, {cls.W_frac}]" if hasattr(cls, 'W_exp') and hasattr(cls, 'W_frac') else "FloatingPoint"

Float = FloatingPoint[8, 23]
Double = FloatingPoint[11, 52]

class Bundle(Auto, metaclass = BundleType):
    @classmethod
    def def_str(cls):
        return "Bundle[{" + ", ".join([f"\"{k}\": {v.def_str()}" for k, v in cls._bundle_types.items()]) + "}]" if hasattr(cls, '_bundle_types') else "Bundle"

class IOWrapper(Signal, metaclass = IOWrapperType):
    @classmethod
    def def_str(cls):
        return f"IOWrapper[{cls.T.def_str()}]" if hasattr(cls, 'T') else "IOWrapper"

class Input(IOWrapper):
    @classmethod
    def def_str(cls):
        return f"Input[{cls.T.def_str()}]" if hasattr(cls, 'T') else "Input"

class Output(IOWrapper):
    @classmethod
    def def_str(cls):
        return f"Output[{cls.T.def_str()}]" if hasattr(cls, 'T') else "Output"



# S = Bundle[{
#     "a": Input[Auto],
#     "b": Output[UInt[8]],
#     "c": Auto,
#     "d": Output[Bundle[{
#         "t": Float
#     }]]
# }]

# T = Bundle[{
#     "a": Output[Auto],
#     "b": Output[Bits],
#     "c": Bundle[{
#         "x": Input[SInt[3]],
#         "y": Output[SInt]
#     }],
#     "d": Input[Bundle[{
#         "t": Auto
#     }]]
# }]

# P = Bundle[{
#     "a": Auto,
#     "b": Bits,
#     "c": Bundle[{
#         "x": SInt[3],
#         "y": SInt
#     }],
#     "d": Auto
# }]

# print(S)
# print(T)
# print(S.merges(T))
# print('---')
# print(S)
# print(P)
# print(S.applys(P))



# T = Bundle[{
#     "a": Output[Auto],
#     "b": Output[Bits],
#     "c": Bundle[{
#         "x": Input[SInt[3]],
#         "y": Output[SInt]
#     }],
#     "d": Input[Bundle[{
#         "t": Auto
#     }]]
# }]

# print(eval(str(T)))