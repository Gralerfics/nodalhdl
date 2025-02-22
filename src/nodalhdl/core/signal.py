"""
+--------------------------------------------------------------------+
    Signal Types:
        Signal;
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
        print(S._bundle_types)                              # {'a': <class '...UInt_8'>, 'b': <class '...Bits_1'>, 'c': <class '...Bundle_0cbbdef73dff1f7318ab831e99b5216d'>}
        print(S.c._bundle_types)                            # {'x': <class '...SInt_3'>, 'y': <class '...SInt_5'>}
+--------------------------------------------------------------------+
"""

from .utils import class_attribute_isolator

import hashlib


""" Exceptions """
class SignalTypeException(Exception): pass


""" Metatypes """
class SignalType(type):
    def __call__(self, *args, **kwds):
        if not self.determined:
            raise TypeError("Undetermined types cannot be instantiated.")
        else:
            return super().__call__(*args, **kwds)
    
    type_pool = {} # ensuring singularity, `type_pool`` for SignalType and its subclasses are all the same one

    def instantiate_type(cls, new_type_name, properties = {}): # `cls` here is the generated class, type(cls) is SignalType or its subclasses
        if not new_type_name in cls.type_pool.keys():
            cls.type_pool[new_type_name] = type(f"{new_type_name}", (cls, ), {
                "determined": True, # guarantee that all types that are correctly generated have the attribute `determined: True`
                **properties
            })
        return cls.type_pool.get(new_type_name)

class BitsType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, int):
            width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{width}",
                {
                    "W": width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<width (int)>]")

class FixedPointType(BitsType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            integer_width, fraction_width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{integer_width}_{fraction_width}",
                {
                    "W": integer_width + fraction_width,
                    "W_int": integer_width,
                    "W_frac": fraction_width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<integer_width (int)>, <fraction_width (int)>]")

class FloatingPointType(BitsType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            exponent_width, fraction_width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{exponent_width}_{fraction_width}",
                {
                    "W": 1 + exponent_width + fraction_width,
                    "W_exp": exponent_width,
                    "W_frac": fraction_width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<exponent_width (int)>, <fraction_width (int)>]")

class IOWrapperType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, SignalType):
            # TODO: 限制不能 IOWrapper 套 IOWrapper (注意可能存在 Bundle 下的递归结构)
            return cls.instantiate_type(
                f"{cls.__name__}_{item.__name__}",
                {
                    "T": item
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<signal_type (SignalType)>]")

class BundleType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, dict) and all([isinstance(x, SignalType) for x in item.values()]):
            return cls.instantiate_type(
                f"{cls.__name__}_{hashlib.md5(str(item).encode('utf-8')).hexdigest()}",
                {
                    "_bundle_types": item, # 信号名到类型的映射, 维护子信号的名称信息, **item 展开后会和一些内建方法混在一起
                    **item # 方便直接按索引引用信号类型
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<members (dict[str, SignalType])>]")


""" Types """
class Signal(metaclass = SignalType):
    determined = False # i.e. width-determined w.r.t. signals
    
    @classmethod
    def equals(cls, other: SignalType):
        return cls == other
    
    @classmethod
    def belongs(cls, other: SignalType):
        return issubclass(cls, other)

class Auto(Signal): pass # undetermined

class Bits(Signal, metaclass = BitsType): pass
Bit = Bits[1]
Byte = Bits[8]

class UInt(Bits): pass
UInt8 = UInt[8]
UInt16 = UInt[16]
UInt32 = UInt[32]
UInt64 = UInt[64]

class SInt(Bits): pass
Int8 = SInt[8]
Int16 = SInt[16]
Int32 = SInt[32]
Int64 = SInt[64]

class FixedPoint(Bits, metaclass = FixedPointType): pass

class FloatingPoint(Bits, metaclass = FloatingPointType): pass
Float = FloatingPoint[8, 23]
Double = FloatingPoint[11, 52]

class Input(Signal, metaclass = IOWrapperType): pass
class Output(Signal, metaclass = IOWrapperType): pass

class Bundle(Signal, metaclass = BundleType):
    def __init__(self): # 递归式地实例化内部信号
        super().__init__()
        bundle_types = getattr(type(self), "_bundle_types")
        for key, T in bundle_types.items():
            setattr(self, key, T())

