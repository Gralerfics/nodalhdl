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
    "T": "wrapped_type"
}

class SignalType:
    """
        不应修改, 各操作返回新对象.
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
    
    @property
    def base(self): # xxxType
        return self.__class__
    
    @property
    def base_name(self) -> str: # "xxxType" -> "xxx"
        return self.base.__name__[:-4]
    
    @property
    def is_determined(self) -> bool: # width-determined or subtype determined
        if self.base_belong(Bits):
            return "width" in self.info.keys()
        elif self.base_belong(Bundle):
            bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", {})
            return all([t.is_determined for t in bundle_types.values()])
        elif self.base_belong(IOWrapper):
            wrapped_type: SignalType = self.info.get("wrapped_type", None)
            return wrapped_type is not None and wrapped_type.is_determined
    
    def _info_check(self, *keys):
        for key in keys:
            value = self.info.get(key, None)
            if value is None:
                raise SignalTypeInstantiationException(f"missing `{key}` when instantiating {self.base_name}")
    
    def uid(self) -> str: # consistent hash of (base, info), for comparison
        raise NotImplementedError
    
    @staticmethod
    def _base_belong(base_0: type, base_1: type):
        base_0_norm = eval(base_0.__name__)
        base_1_norm = eval(base_1.__name__)
        return issubclass(base_0_norm, base_1_norm)
    
    def base_belong(self, other: 'SignalType') -> bool:
        return SignalType._base_belong(self.base, other.base)
    
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
    
    def merge(self, other: 'SignalType') -> 'SignalType':
        raise NotImplementedError # TODO 冲突在此判断; 返回的类型需要特化


class AutoType(SignalType):
    pass


class BitsType(AutoType):
    def __call__(self, *args, **kwds):
        self._info_check("width")
        return BitsValue(self, *args, **kwds)
    
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return BitsType({"width": width})
    
    def validal(self) -> str:
        width = self.info.get("width", None)
        return f"{self.base_name}_{width}" if width is not None else "Bits"


class FixedPointType(BitsType):
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return FixedPointType({"width_integer": width_integer, "width_fraction": width_fraction})
    
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
        return UFixedPointType({"width_integer": width_integer, "width_fraction": width_fraction, "width": width_integer + width_fraction})


class SFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._info_check("width_integer", "width_fraction")
        return SFixedPointValue(self, *args, **kwds)

    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return SFixedPointType({"width_integer": width_integer, "width_fraction": width_fraction, "width": 1 + width_integer + width_fraction})


class IntegerType(FixedPointType):
    def __init__(self, info = {}):
        super().__init__(info)
        info["width_fraction"] = 0
    
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
    
    def derive(self, width_exponent: int, width_mantissa: int) -> 'SignalType':
        assert isinstance(width_exponent, int) and isinstance(width_mantissa, int)
        return FixedPointType({"width_exponent": width_exponent, "width_mantissa": width_mantissa})
    
    def validal(self) -> str:
        width_exponent = self.info.get("width_exponent", None)
        width_mantissa = self.info.get("width_mantissa", None)
        return f"{self.base_name}_{width_exponent}_{width_mantissa}" if width_exponent is not None and width_mantissa is not None else self.base_name


class BundleType(AutoType):
    def __call__(self, *args, **kwds):
        self._info_check("bundle_types")
        return BundleValue(self, *args, **kwds)
    
    def derive(self, bundle_types: Dict[str, SignalType]) -> 'SignalType':
        assert isinstance(bundle_types, SignalType)
        return BundleType({"bundle_types": bundle_types})
    
    def validal(self) -> str:
        bundle_types: Dict[str, SignalType] = self.info.get("bundle_types", {})
        return hashlib.md5(str(bundle_types).encode('utf-8')).hexdigest()


class IOWrapperType(SignalType):
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def derive(self, wrapped_type: SignalType) -> 'SignalType':
        assert isinstance(wrapped_type, SignalType)
        return IOWrapperType({"wrapped_type": wrapped_type})
    
    def validal(self) -> str:
        wrapped_type: SignalType = self.info.get("wrapped_type", None)
        return f"{self.base_name}_{wrapped_type}" if wrapped_type is not None else self.base_name


Signal = SignalType()
Auto = AutoType()
Bits = BitsType()
UFixedPoint = UFixedPointType()
SFixedPoint = SFixedPointType()
UInt = UIntType()
SInt = SIntType()
FloatingPoint = FloatingPointType()
Bundle = BundleType()
IOWrapper = IOWrapperType()


""" SignalValue """
class SignalValueException(Exception): pass

class SignalValue:
    def __init__(self, signal_type: SignalType, literal_value):
        # assert signal_type.base_name == self.__class__.__name__[:-5] # TODO 本来是保证 xType 对应 xValue, 但目前 U/SInt 直接用了 U/SFixedPoint, 先注释吧
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


print(Bits)
print(Bits[8])
print(SFixedPoint[16, 12])
print(SInt[8])

print(SFixedPoint[1, 1](1.5))
print(SFixedPoint[1, 1](2.5))

print(SInt[3](2))

print(SignalType._base_merge(SFixedPointType, SIntType))


"""
    base 仅一个, 合并时为最下的、与二者都有从属关系的类型.
        (不同支类型都有的话说明就是强制转换, 取最近公共祖先; 同支的话往下走更具体)
        (信息给了就是合理的! 出现不合理就是给的问题!)
    
    类型 (type) 指 SignalType 及其子类的对象
    类型的基类型 (base) 指 SignalType 及其子类本身的引用
    但显示基类型的名字 (base_name) 时用类型基础名, 也就是基类型的名称去掉最后的 "Type"
    所以下面为了方便用而定义的一系列对象和衍生对象命名最好就是基类型的名称
"""