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
            "b": UInt[8],
            "c": Bit
        }]
        s = S()
        print(S.T)                                          # {'a': <class '...UInt_8'>, 'b': <class '...UInt_8'>, 'c': <class '...Bits_1'>}
        print(s.a)                                          # <...UInt_8 object at ...>
+--------------------------------------------------------------------+
    Comments:
        1.  `Type` 为创建类型的类型，区分以表示不同类的创建格式，
            例如 BitsType 用于创建具有单个 width 属性的类型，
            而 FixedPointType 用于创建具有 width, integer_width, fraction_width 属性的类型。
            `SignalType` 是信号类型的类型，是所有 `Type` 类型的基类，继承自 `type`。
            具体，本来类 (class) 的类型是 type，现在更具体一点变成 SignalType 等继承自 type 的新 type。
        2.  类型本身之间的从属关系由多继承实现，和 `Type` 无关，
            但如果希望某类型继承某类型，则其 `Type` 也应该继承对应的 `Type`，
            至于创建方式，可以被覆写；
            为了清晰，这里类型的继承以及 `Type` 的继承关系保持一致。
        3.  硬件结构记录中主要使用的应当是类型类本身，例如 `in_type = UInt[8]`，而不用使用其实例 `UInt[8]()`。
            实例将实现运算重载，但应当是用于仿真目的，因为其对应的硬件功能需要单独实现。
            或可在某处实现一成员方法，用于给出两种类型间某运算的名称，以便后续生成对应的硬件模块文件的命名。
        4.  或许运算也应该定义为类，本身记录参与运算的类型和必要参数，不涉具体值，用于构建运算结构。
            也便于实现 (3.) 中的最后一句话。仿真运算的实现也可置于其中，解耦两个文件。
        5.  TODO 实例需不需要能获取到类属性?
+--------------------------------------------------------------------+
"""

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
        def __is_all_signal_type(item: dict):
            for x in item.values():
                if not isinstance(x, SignalType):
                    return False
            return True
        
        if isinstance(item, dict) and __is_all_signal_type(item):
            return cls.instantiate_type(
                f"{cls.__name__}_{hashlib.md5(str(item).encode('utf-8')).hexdigest()}",
                {
                    "T": item
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<members (dict)>]")


""" Types """
class Signal(metaclass = SignalType):
    determined = False # i.e. width-determined w.r.t. signals
    
    @classmethod
    def equals(cls, other: SignalType):
        return cls == other
    
    @classmethod
    def belongs(cls, other: SignalType):
        return issubclass(cls, other)

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
    def __init__(self):
        super().__init__()
        bundle_types = type(self).T
        for key, T in bundle_types.items():
            setattr(self, key, T())
    
    def __getattribute__(self, name): # TODO 将该功能包装为一个装饰器吧, 起名关于屏蔽/隔离对象对类属性的访问
        """
            若 Bundle 对象不包含恰好名为 T 的信号, 而用户希望访问保存信号类型的类属性 T, 则建议其使用 `type(...).T`.
            若 Bundle 对象下恰好有名为 T 的信号, 则 object.T 访问的就是该信号的对象, 覆盖了对类属性 T 的访问.
        """
        if name == "T" and "T" not in self.__dict__.keys(): # type(self).T.keys():
            raise AttributeError(f"\'type(object).T\' or \'s.__class__.T\' is recommended if you want to access the class attribute \'T\'")
        return super().__getattribute__(name)

