# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

"""
    Notes:
        base 仅一个, 合并时为最下的、与二者都有从属关系的类型.
            (不同支类型都有的话说明就是强制转换, 取最近公共祖先; 同支的话往下走更具体)
            (信息给了就是合理的! 出现不合理就是给的问题!)
        
        TODO 是否还应有一条设计原则: 子类型必须至少需要填入父类型的所有属性, 然后 belong 就可以判断这种关系.
        
        类型 (type) 指 SignalType 及其子类的对象
        类型的基类型 (base) 指 SignalType 及其子类本身的引用
        但显示基类型的名字 (base_name) 时用类型基础名, 也就是基类型的名称去掉最后的 "Type"
        所以下面为了方便用而定义的一系列对象和衍生对象命名最好就是基类型的名称
        
        Auto 下 Bundle 代表所有结构化类型, Bits 代表所有单类型; Signal 下 IOWrapper 代表所有 IO 包装.
        这三者应该完全覆盖除 Auto 和 Signal 之外所有类型的祖先.
        Bundle 下继承的新类型必须以类似的 dict 作为 derive 的第一个参数并拥有 bundle_types (一系列递归遍历操作导致的要求);
        IOWrapper 下继承的新类型类似, 必须拥有 wrapped_type 并且作为 derive 第一个参数.
        
        其实可以 IOWrapper 直接返回的是其他类型对象, 只是为其添加 wrapper_type (in or out) 属性,
        这样就把 IOWrapper 整合进了常规类型, 各类操作中可以省去很多判断, Signal 和 Auto 似乎也就可以合并.
        目前是将其单独列为 Signal 下的一类, 优点是明确一些, 并且 IOWrapperType 也更标准一些.
        TODO 之后可以考虑重构.
        
        更激进一点则是将 Bundle 视为一系列 Bits 的拼接, 类似 C struct 中的 union, 将其归入 Bits 下,
        则 Bits 就可以作为顶层类型, 且各类判断几乎全都不需要了.
        缺点是实现起来有点问题; 或许, Bundle 的信息并不是 dict 这样 "Bits 怎么构成 Bundle", 而是 "Bits 怎么划分为子 Bits".
        TODO 也可以考虑哈.
"""
import hashlib

from typing import Dict, Union


""" SignalType """
class SignalTypeException(Exception): pass
class SignalTypeInstantiationException(Exception): pass

_info_abbreviation_mapping = {
    "W": "width",
    "W_int": "width_integer",
    "W_frac": "width_fraction",
    "W_exp": "width_exponent",
    "W_mant": "width_mantissa",
    "BT": "bundle_types",
    "T": "wrapped_type"
} # try not to use abbrs inside SignalType(s)

class SignalType:
    """
        for signal types.
        should not be modified, i.e. operations return new objects.
    """
    def __init__(self, info: dict = {}): # do not call by yourself
        self.info = info
    
    def __getitem__(self, item): # derive type by passing arguments into "[]"
        if not isinstance(item, list) and not isinstance(item, tuple):
            item = [item]
        return self.derive(*item)
    
    def __getattr__(self, name): # __getattr__ is only called when the property not exists; __getattribute__ is called every time
        name = _info_abbreviation_mapping.get(name, name)
        return self.info.get(name, None)
    
    def __repr__(self):
        return self.validal()
    
    """ @override """
    def __call__(self, *args, **kwds) -> 'SignalValue': # type instantiation
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    """ @override """
    def derive(self, *args, **kwargs) -> 'SignalType': # derived type
        raise SignalTypeException(f"{self.__name__} has no derived types")
    
    """ @override """
    def validal(self) -> str: # valid string
        return "Signal"
    
    """ @override """
    def exhibital(self) -> str: # display string
        return self.validal()
    
    @property
    def base(self): # xxxType
        return self.__class__
    
    @property
    def base_name(self) -> str: # "xxxType" -> "xxx"
        return self.base.__name__[:-4]
    
    @property
    def base_type(self) -> 'SignalType':
        return self.base()
    
    @property
    def uid(self) -> str: # consistent hash of (base, info), for comparison
        return hashlib.md5(self.validal().encode('utf-8')).hexdigest() # [NOTICE] 这样要求 validal 是唯一的
    
    @property
    def is_determined(self) -> bool: # width-determined or subtype determined
        if self.base_belong(Bits):
            return "width" in self.info.keys()
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
            return bundle_types is not None and all([t.is_determined for t in bundle_types.values()])
        elif self.base_belong(IOWrapper):
            wrapped_type: SignalType = self.info.get("wrapped_type", None)
            return wrapped_type is not None and wrapped_type.is_determined
    
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined
    
    @property
    def is_io_perfect(self) -> bool:
        if self.base_belong(Bits):
            return False
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
            return bundle_types is not None and all([t.is_io_perfect for t in bundle_types.values()]) # Bundle base type is not perfectly IO-wrapped
        elif self.base_belong(IOWrapper):
            wrapped_type: SignalType = self.info.get("wrapped_type", None)
            return wrapped_type is not None # should have wrapped types
    
    @property
    def is_io_existing(self) -> bool:
        if self.base_belong(Bits):
            return False
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", {})
            return any([t.is_io_existing for t in bundle_types.values()])
        elif self.base_belong(IOWrapper):
            return True
    
    def _info_check(self, *keys):
        for key in keys:
            value = self.info.get(key, None)
            if value is None:
                raise SignalTypeInstantiationException(f"missing `{key}` when instantiating {self.base_name}")
    
    @staticmethod
    def _base_equal(base_0: type, base_1: type) -> bool:
        return base_0.__name__ == base_1.__name__
    
    def base_equal(self, other: 'SignalType') -> bool:
        return SignalType._base_equal(self.base, other.base)
    
    @staticmethod
    def _base_belong(base_0: type, base_1: type) -> bool:
        base_0_norm = eval(base_0.__name__)
        base_1_norm = eval(base_1.__name__)
        return issubclass(base_0_norm, base_1_norm)
    
    def base_belong(self, other: 'SignalType') -> bool:
        # why not use isinstance(self, other.base)? type consistence in persistence need to be considered, see _base_belong().
        return SignalType._base_belong(self.base, other.base)
    
    def belong(self, other: 'SignalType') -> bool: # base_belong, and self has all (same) properties in other
        return self.base_belong(other) and all([self.info.get(other_key, None) == other_v for other_key, other_v in other.info.items()])

    def equal(self, other: 'SignalType') -> bool:
        return self.uid == other.uid # [NOTICE] uid 相等, uid 和 validal 表示相关, 故不用担心 info 中有奇怪的信息, 只会取需要的
    
    def match(self, other: 'SignalType') -> bool:
        raise NotImplementedError
    
    def isomorphic(self, other: 'SignalType') -> bool:
        raise NotImplementedError
    
    @staticmethod
    def _base_merge(base_0: type, base_1: type):
        if SignalType._base_belong(base_0, base_1):
            return base_0
        elif SignalType._base_belong(base_1, base_0):
            return base_1
        else: # or find "LCA" ([NOTICE] if multi-inheritance, use the first base, i.e. __base__)
            current_base = base_0
            while SignalType._base_belong(current_base, SignalType):
                if SignalType._base_belong(base_1, current_base):
                    return current_base
                current_base = current_base.__base__
            
            raise SignalTypeException(f"Failed to merge base {base_0.__name__} and {base_0.__name__}")
    
    def _single_merge(self, other: 'SignalType') -> 'SignalType': # only for single types, i.e. (sub-)Bits
        assert self.base_belong(Bits) and other.base_belong(Bits)
        
        keys = set(self.info.keys()) | set(other.info.keys())
        new_info = {}
        for key in keys:
            self_value, other_value = self.info.get(key, None), other.info.get(key, None)
            if self_value == other_value:
                new_info[key] = self_value
            elif self_value is None:
                new_info[key] = other_value
            elif other_value is None:
                new_info[key] = self_value
            elif key != "width":
                pass # deprecate the conflicting property
            else: # width
                raise SignalTypeException(f"Width-conflicing types {self} and {other}")
        
        merged_base = SignalType._base_merge(self.base, other.base)
        return merged_base(new_info)
    
    def apply(self, other: 'SignalType') -> 'SignalType': # merge base and all properties in info (different)
        other = other.io_clear() # ignore other's IO-wrappers
        
        if self.base_equal(Auto):
            return other
        elif other.base_equal(Auto):
            return self
        elif self.base_belong(IOWrapper): # and self.info.get("wrapped_type", None) is not None:
            wrapped_type: SignalType = self.info.get("wrapped_type", None)
            if wrapped_type is not None:
                return self.base({"wrapped_type": wrapped_type.apply(other)})
            else:
                return self.base()
        elif self.base_belong(Bundle) and other.base_belong(Bundle):
            self_bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
            other_bundle_types: Dict[str, SignalType] = other.info.get("bundle_types", None)
            if self_bundle_types is None and other_bundle_types is None:
                return self.base()
            elif self_bundle_types is not None and other_bundle_types is not None and self_bundle_types.keys() == other_bundle_types.keys():
                return self.base({
                    "bundle_types": {k: self_t.apply(other_bundle_types.get(k)) for k, self_t in self_bundle_types.items()}
                })
            else:
                raise SignalTypeException("Non-isomorphic types cannot be merged")
        elif self.base_belong(Bits) and other.base_belong(Bits):
            return self._single_merge(other)
        else:
            raise SignalTypeException("Non-isomorphic types cannot be merged")
    
    def merge(self, other: 'SignalType') -> 'SignalType':
        return self.io_clear().apply(other.io_clear())
    
    def io_clear(self) -> 'SignalType':
        if not self.is_io_existing:
            return self
        elif self.base_belong(IOWrapper):
            wrapped_type: SignalType = self.info.get("wrapped_type", None)
            if wrapped_type is not None:
                return wrapped_type
            else:
                raise SignalTypeException("There exists IOWrapper base type that cannot be eliminated")
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
            if bundle_types is not None:
                return self.base({
                    "bundle_types": {k: t.io_clear() for k, t in bundle_types.items()}
                })
            else:
                return self.base()
    
    def io_flip(self) -> 'SignalType':
        if not self.is_io_perfect:
            raise SignalTypeException("Imperfectly IO-wrapped signal type cannot be flipped")
        elif isinstance(self, IOWrapperType): # self.base_belong(IOWrapper):
            return self.flip()
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
            # bundle_types will not be None because `self.is_io_perfect` is True here.
            return self.base({
                "bundle_types": {k: t.io_flip() for k, t in bundle_types.items()}
            })
        else:
            raise SignalTypeException("This should not happen")


class AutoType(SignalType):
    def validal(self) -> str:
        return "Auto"


class BitsType(AutoType):
    def __call__(self, *args, **kwds):
        self._info_check("width")
        return BitsValue(self, *args, **kwds)
    
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return self.base({"width": width})
    
    def validal(self) -> str:
        width = self.info.get("width", None)
        return f"{self.base_name}_{width}" if width is not None else "Bits"


class FixedPointType(BitsType):
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined and self.info.get("width_integer", None) is not None and self.info.get("width_fraction", None)
    
    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return self.base({"width_integer": width_integer, "width_fraction": width_fraction})
    
    def validal(self) -> str:
        width_integer = self.info.get("width_integer", None)
        width_fraction = self.info.get("width_fraction", None)
        return f"{self.base_name}_{width_integer}_{width_fraction}" if width_integer is not None and width_fraction is not None else self.base_name


class UFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._info_check("width_integer", "width_fraction")
        return UFixedPointValue(self, *args, **kwds)

    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return self.base({"width_integer": width_integer, "width_fraction": width_fraction, "width": width_integer + width_fraction})


class SFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._info_check("width_integer", "width_fraction")
        return SFixedPointValue(self, *args, **kwds)

    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return self.base({"width_integer": width_integer, "width_fraction": width_fraction, "width": 1 + width_integer + width_fraction})


class IntegerType(FixedPointType):
    def __init__(self, info = {}):
        super().__init__(info)
        info["width_fraction"] = 0
    
    # @property
    # def is_fully_determined(self) -> bool:
    #     return self.is_determined
    
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def validal(self):
        width = self.info.get("width", None)
        return f"{self.base_name}_{width}" if width is not None else self.base_name


class UIntType(IntegerType, UFixedPointType):
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return self.base({"width": width, "width_integer": width}) # , "width_fraction": 0})
    
    def __call__(self, *args, **kwds):
        self._info_check("width")
        return UFixedPointValue(self, *args, **kwds)


class SIntType(IntegerType, SFixedPointType):
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return self.base({"width": width, "width_integer": width - 1}) # , "width_fraction": 0})
    
    def __call__(self, *args, **kwds):
        self._info_check("width")
        return SFixedPointValue(self, *args, **kwds)


class FloatingPointType(BitsType):
    def __call__(self, *args, **kwds):
        self._info_check("width_exponent", "width_mantissa")
        return FloatingPointValue(self, *args, **kwds)
    
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined and self.info.get("width_exponent", None) is not None and self.info.get("width_mantissa", None)
    
    def derive(self, width_exponent: int, width_mantissa: int) -> 'SignalType':
        assert isinstance(width_exponent, int) and isinstance(width_mantissa, int)
        return self.base({"width_exponent": width_exponent, "width_mantissa": width_mantissa})
    
    def validal(self) -> str:
        width_exponent = self.info.get("width_exponent", None)
        width_mantissa = self.info.get("width_mantissa", None)
        return f"{self.base_name}_{width_exponent}_{width_mantissa}" if width_exponent is not None and width_mantissa is not None else self.base_name


class BundleType(AutoType):
    def __call__(self, *args, **kwds):
        self._info_check("bundle_types")
        return BundleValue(self, *args, **kwds)
    
    def derive(self, bundle_types: Dict[str, SignalType]) -> 'SignalType':
        assert isinstance(bundle_types, dict)
        return self.base({"bundle_types": bundle_types})
    
    def validal(self) -> str:
        bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
        if bundle_types is not None:
            return self.base_name + "_" + hashlib.md5(str(bundle_types).encode('utf-8')).hexdigest() # used in core.hdl
        else:
            return self.base_name
    
    def exhibital(self) -> str:
        bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", None)
        if bundle_types is not None:
            return self.base_name + "{" + ", ".join([f"{k}: {t.exhibital()}" for k, t in bundle_types.items()]) + "}"
        else:
            return self.base_name


class IOWrapperType(SignalType):
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def derive(self, wrapped_type: SignalType) -> 'SignalType':
        assert isinstance(wrapped_type, SignalType) and not wrapped_type.is_io_existing
        return self.base({"wrapped_type": wrapped_type})
    
    def validal(self) -> str:
        wrapped_type: SignalType = self.info.get("wrapped_type", None)
        return f"{self.base_name}_{wrapped_type}" if wrapped_type is not None else self.base_name
    
    def exhibital(self) -> str:
        wrapped_type: SignalType = self.info.get("wrapped_type", None)
        return f"{self.base_name}[{wrapped_type.exhibital()}]" if wrapped_type is not None else self.base_name
    
    def flip(self):
        raise SignalTypeException("IOWrapper base type cannot be flipped")


class InputType(IOWrapperType):
    def flip(self):
        wrapped_type: SignalType = self.info.get("wrapped_type", None)
        if wrapped_type is not None:
            return Output[wrapped_type]
        else:
            return Output


class OutputType(IOWrapperType):
    def flip(self):
        wrapped_type: SignalType = self.info.get("wrapped_type", None)
        if wrapped_type is not None:
            return Input[wrapped_type]
        else:
            return Input


Signal = SignalType()

Auto = AutoType()

Bits = BitsType()
Bit = Bits[1]
Byte = Bits[8]

FixedPoint = FixedPointType()
UFixedPoint = UFixedPointType()
SFixedPoint = SFixedPointType()

Integer = IntegerType()
UInt = UIntType()
UInt8 = UInt[8]
UInt16 = UInt[16]
UInt32 = UInt[32]
UInt64 = UInt[64]
SInt = SIntType()
Int8 = SInt[8]
Int16 = SInt[16]
Int32 = SInt[32]
Int64 = SInt[64]

FloatingPoint = FloatingPointType()
Float = FloatingPoint[8, 23]
Double = FloatingPoint[11, 52]

Bundle = BundleType()

IOWrapper = IOWrapperType()
Input = InputType()
Output = OutputType()


""" SignalValue """
class SignalValueException(Exception): pass

class SignalValue:
    def __init__(self, signal_type: SignalType, literal_value):
        self.type = signal_type
        self.set_internal(literal_value)
    
    def __getattr__(self, name):
        return self.type.__getattr__(name)
    
    def __repr__(self):
        return self.validal()
    
    @property
    def literal(self):
        return self.internal_to_literal(self.internal)
    
    def set_internal(self, literal_value):
        self.internal = self.literal_to_internal(literal_value)

    """ @override """
    def literal_to_internal(self, literal_value):
        return None
    
    """ @override """
    def internal_to_literal(self, internal_value):
        return None
    
    """ @override """
    def validal(self) -> str:
        raise SignalValueException(f"{self.type.base_name} cannot be converted to a valid representation")
    
    """ @override """
    def to_bits_string(self):
        raise SignalValueException(f"{self.type.base_name} cannot be converted to a bits-string")

    """ @override """
    # def __add__(self, other): ...
    # ...


class BitsValue(SignalValue):
    def literal_to_internal(self, literal_value: Union[str, int]):
        normalize = lambda x: x % (1 << self.W)
        if isinstance(literal_value, int):
            return normalize(literal_value)
        elif isinstance(literal_value, str):
            return int(literal_value[-self.W:], base = 2)
        else:
            raise NotImplementedError
    
    def internal_to_literal(self, internal_value):
        return internal_value
    
    def validal(self) -> str:
        return "b" + self.to_bits_string() # in default
    
    def to_bits_string(self):
        return bin(self.internal)[2:].zfill(self.W)[-self.W:]


class UFixedPointValue(BitsValue):
    pass # TODO


class SFixedPointValue(BitsValue):
    def literal_to_internal(self, literal_value: Union[float, int]):
        if isinstance(literal_value, float) or isinstance(literal_value, int):
            value_int = int(literal_value * (1 << self.W_frac))
            half = 1 << (self.W - 1)
            return (value_int + half) % (1 << self.W) - half
        else:
            raise NotImplementedError
    
    def internal_to_literal(self, internal_value):
        literal_value = internal_value / (1 << self.W_frac)
        return literal_value if self.W_frac > 0 else int(literal_value) # W_frac = 0 -> Integer
    
    def validal(self) -> str:
        return str(self.literal)
    
    def to_bits_string(self):
        num_unsigned = self.internal + (1 << self.W) if self.internal < 0 else self.internal
        return bin(num_unsigned)[2:].zfill(self.W)[-self.W:]


class FloatingPointValue(BitsValue):
    pass # TODO


class BundleValue(SignalValue):
    pass # TODO


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]


if __name__ == "__main__": # test
    print(Bits)
    print(Bits[8])
    print(SFixedPoint[16, 12])
    print(SInt[8])

    print(SFixedPoint[1, 1](1.5))
    print(SFixedPoint[1, 1](2.5))

    print(" === ")

    S = Bundle[{
        "a": Input[Auto],
        "b": Output[UInt[8]],
        "c": Auto,
        "d": Output[Bundle[{
            "t": Float
        }]]
    }]

    SS = BundleType()[{
        "a": Input[Auto],
        "b": Output[UInt[8]],
        "c": Auto,
        "d": Output[Bundle[{
            "t": Float
        }]]
    }]

    T = Bundle[{
        "a": Output[Auto],
        "b": Output[Bits],
        "c": Bundle[{
            "x": Input[SInt[3]],
            "y": Output[SInt]
        }],
        "d": Input[Bundle[{
            "t": Auto
        }]]
    }]

    P = Bundle[{
        "a": Auto,
        "b": Bits,
        "c": Bundle[{
            "x": SInt[3],
            "y": SInt
        }],
        "d": Auto
    }]

    print(S.exhibital())
    print(T.exhibital())
    print(S.io_clear().exhibital())
    print(T.io_clear().exhibital())
    print(S.merge(T).exhibital())

    print(" === ")

    print(S.exhibital())
    print(P.exhibital())
    print(S.apply(P).exhibital())

    print(" === ")

    print(T.exhibital())
    print(T.io_flip().exhibital())
    print(T.io_clear().exhibital())
    
    print(UInt[8].merge(SFixedPoint[3, 4]).info)
    print(UInt[8].merge(SInt[8]).info)
    print(SFixedPoint[3, 3].merge(UFixedPoint[3, 4]).info)
    print(UFixedPoint[3, 4].merge(UInt).base_name)
    
    print(SFixedPoint[3, 3].W)
    print(SFixedPoint[3, 3].W_frac)
    print(Input[SFixedPoint[3, 3]].T)
    print(S.BT)
    
    print(S.uid)
    print(SS.uid)
    
    print(UInt64.belong(UFixedPoint[64, 0]))
    
    print(SFixedPoint[16, 12](0.999).to_bits_string())
    print(SFixedPoint[16, 12](0.9999).to_bits_string())
    print(SFixedPoint[16, 12](0.99999999999).to_bits_string())
    print(SFixedPoint[16, 12](0.999999999999).to_bits_string())

    # Q = Bundle[{
    #     "a": UInt[4],
    #     "b": Bits[8],
    #     "c": Bundle[{
    #         "x": SInt[3],
    #         "y": SInt[5],
    #         "z": Bundle[{
    #             "n": UInt[8]
    #         }]
    #     }]
    # }]

    # q = Q({
    #     "a": 20,
    #     "b": "00010010",
    #     "c": {
    #         "x": -5,
    #         "y": -2
    #     }
    # })

