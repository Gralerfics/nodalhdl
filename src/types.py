# +--------------------------------------------------------------------+
#   Signal Types:
#       Signal;
#       Bits[width], Bit;
#       Number[width];
#       UInt[width];
#       SInt[width];
#       FixedPoint[integer_width, fraction_width];
#       FloatingPoint[exponent_width, fraction_width], Float, Double.
#   Examples:
#       a = UInt[8]()
#       print(isinstance(a, UInt[8]))       # True
#       print(isinstance(a, UInt))          # True
#       print(isinstance(a, UInt[9]))       # False
#       print(isinstance(a, BitsType))      # False
#       print(isinstance(a, Bits))          # True
#       print(isinstance(a, Signal))        # True
#       print(type(a).width)                # 8
#
#       print(Float.__name__)               # FloatingPoint_8_23
#       print(UInt.__name__)                # UInt
#       print(SInt[8].__name__)             # SInt_8
#
#       print(type(Signal))                                 # <class '__main__.SignalType'>
#       print(type(UInt[8]))                                # <class '__main__.BitsType'>
#       print(issubclass(UInt[8], UInt))                    # True
#       print(issubclass(UInt[8], BitsType))                # False
#       print(issubclass(type(UInt[8]), BitsType))          # True
#       print(issubclass(type(UInt[8]), SignalType))        # True
#
#       print(UInt[8].belongs(Number))                      # True
#       print(UInt[8].belongs(Number[8]))                   # False
#       print(UInt[8].equals(UInt[8]))                      # True
#       print(UInt[8].equals(UInt[7]))                      # False
#
#       print(UInt.instant_type)                            # False
#       print(UInt[8].instant_type)                         # True
# +--------------------------------------------------------------------+
#   Comments:
#       0.  下文的 `Meta` 皆指 `Type`。
#       1.  `Meta` 为创建类型的类型，区分以表示不同类的创建格式，
#           例如 BitsMeta 用于创建具有单个 width 属性的类型，
#           而 FixedPointMeta 用于创建具有 width, integer_width, fraction_width 属性的类型。
#           `SignalType` 是信号类型的类型，是所有 `Meta` 类型的基类。
#       2.  类型本身之间的从属关系由多继承实现，和 `Meta` 无关，
#           但如果希望某类型继承某类型，则其 `Meta` 也应该继承对应的 `Meta`，
#           至于创建方式，可以被覆写；
#           为了清晰，这里类型的继承以及 `Meta` 的继承关系保持一致。
# +--------------------------------------------------------------------+
#   TODO:
#       1. 实现仿真模拟时考虑使用类型类实例的属性 (self.xxx)
#       2. FixedPoint 和 FloatingPoint 暂不考虑使用
# +--------------------------------------------------------------------+

"""
    Exceptions
"""

class SignalTypeException(Exception): pass

"""
    Metaclasses (theoretically can not be referenced by user code, except in type hints)
"""

class SignalType(type):
    type_pool = {} # 保证创建的类型单例化；子类的 type_pool 都共用，例如 UInt.type_pool 和 SInt.type_pool 是一致的

    def instantiate_type(cls, new_type_name, properties = {}): # 关于类与元类的关系：例如此处的 cls 的 type 是 SignalType 或其子类
        if not new_type_name in cls.type_pool.keys():
            cls.type_pool[new_type_name] = type(f"{new_type_name}", (cls, ), {})
        new_cls = cls.type_pool.get(new_type_name)
        for key, value in properties.items():
            setattr(new_cls, key, value)
        setattr(new_cls, "instant_type", True)
        return new_cls

class BitsType(SignalType):
    def __getitem__(cls, item):
        if isinstance(item, int):
            width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{width}",
                {
                    "width": width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter \'{item}\'.")

class NumberType(BitsType): pass

class UIntType(NumberType): pass

class SIntType(NumberType): pass

class FixedPointType(NumberType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            integer_width, fraction_width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{integer_width}_{fraction_width}",
                {
                    "width": integer_width + fraction_width,
                    "integer_width": integer_width,
                    "fraction_width": fraction_width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter \'{item}\'.")

class FloatingPointType(NumberType):
    def __getitem__(cls, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            exponent_width, fraction_width = item
            return cls.instantiate_type(
                f"{cls.__name__}_{exponent_width}_{fraction_width}",
                {
                    "width": 1 + exponent_width + fraction_width,
                    "exponent_width": exponent_width,
                    "fraction_width": fraction_width
                }
            )
        else:
            raise SignalTypeException(f"Invalid parameter \'{item}\'.")

"""
    Classes
"""

class Signal(metaclass = SignalType):
    instant_type = False

    @classmethod
    def to_hdl(cls, hdl: str):
        if not hasattr(cls, "width"):
            raise SignalTypeException(f"\'{cls.__name__}\' is not width-determined.")
        if hdl == "vhdl":
            return f"std_logic_vector({cls.width - 1} downto 0)"
        elif hdl == "verilog":
            return f"[{cls.width - 1}:0]"
        else:
            raise SignalTypeException(f"Unsupported HDL \'{hdl}\'.")
    
    @classmethod
    def equals(cls, other: SignalType):
        return cls == other
    
    @classmethod
    def belongs(cls, other: SignalType):
        return issubclass(cls, other)

class Bits(Signal, metaclass = BitsType): pass
Bit = Bits[1]

class Number(Bits, metaclass = NumberType): pass

class UInt(Number, metaclass = UIntType): pass

class SInt(Number, metaclass = SIntType): pass

class FixedPoint(Number, metaclass = FixedPointType): pass

class FloatingPoint(Number, metaclass = FloatingPointType): pass
Float = FloatingPoint[8, 23]
Double = FloatingPoint[11, 52]

