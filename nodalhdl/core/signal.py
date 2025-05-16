from typing import Dict

import hashlib


# """ Pool """
# class SignalTypePoolException(Exception): pass

# class SignalTypePool:
#     pool: Dict[str, 'SignalType'] = {}
    
#     @staticmethod
#     def fetch(uid: str):
#         """
#             fetch the structure object by unique_name, or None when not exists.
#             sweep the invalid references (lazy tag).
#         """
#         s = ReusablePool.pool.get(unique_name, None)
#         if s is not None:
#             if s.is_reusable and s.unique_name == unique_name:
#                 # exists and still valid
#                 return s
#             else:
#                 # exists but invalid, clear
#                 del ReusablePool.pool[unique_name]
#                 return None
#         else:
#             return None
    
#     @staticmethod
#     def register(s: 'Structure'):
#         """
#             register an structure into the pool.
#             if not reusable then return False and nothing will be done.
#         """
#         if s.is_reusable:
#             fetch_s = ReusablePool.fetch(s.unique_name)
#             if fetch_s is not None and fetch_s != s: # exists and conflicts
#                 raise ReusablePoolException("unique_name should be unique")
#             else: # allowed
#                 ReusablePool.pool[s.unique_name] = s
#         else:
#             return False


class SignalTypeException(Exception): pass
class SignalTypeInstantiationException(Exception): pass

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
    
    def __repr__(self):
        return self.literal()
    
    """ @override """
    def __call__(self, *args, **kwds): # -> 'SignalValue': # type instantiation
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    """ @override """
    def derive(self, *args, **kwargs) -> 'SignalType': # derived type
        raise SignalTypeException(f"{self.__name__} has no derived types")
    
    """ @override """
    def literal(self) -> str: # valid string
        return "Signal"
    
    @property
    def base(self): # xxxType
        return self.__class__
    
    @property
    def base_name(self): # "xxxType" -> "xxx"
        return self.base.__name__[:-4]
    
    @property
    def is_determined(self): # width-determined
        return "width" in self.info.keys()
    
    def _info_check(self, *keys):
        for key in keys:
            value = self.info.get(key, None)
            if value is None:
                raise SignalTypeInstantiationException(f"missing `{key}` when instantiating {self.base_name}")
    
    def uid(self) -> str: # consistent hash of (base, info), for comparison
        raise NotImplementedError
    
    @staticmethod
    def _merge_base(base_0: type, base_1: type) -> type:
        raise NotImplementedError
    
    def merge(self, other: 'SignalType') -> 'SignalType':
        raise NotImplementedError # TODO 冲突在此判断; 返回的类型需要特化


class BitsType(SignalType):
    def __call__(self, *args, **kwds):
        self._info_check("width")
        
        raise NotImplementedError
    
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return BitsType({"width": width})
    
    def literal(self) -> str:
        width = self.info.get("width", None)
        return f"Bits_{width}" if width is not None else "Bits"


class FixedPointType(BitsType):
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def derive(self, width_integer: int, width_fraction: int = None) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return FixedPointType({"width_integer": width_integer, "width_fraction": width_fraction})
    
    def literal(self) -> str:
        width_integer = self.info.get("width_integer", None)
        width_fraction = self.info.get("width_fraction", None)
        return f"{self.base_name}_{width_integer}_{width_fraction}" if width_integer is not None and width_fraction is not None else self.base_name


class UFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._info_check("width_integer", "width_fraction")
        
        raise NotImplementedError

    def derive(self, width_integer: int, width_fraction: int = None) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return UFixedPointType({"width_integer": width_integer, "width_fraction": width_fraction, "width": width_integer + width_fraction})


class SFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._info_check("width_integer", "width_fraction")
        
        raise NotImplementedError

    def derive(self, width_integer: int, width_fraction: int = None) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return SFixedPointType({"width_integer": width_integer, "width_fraction": width_fraction, "width": 1 + width_integer + width_fraction})


class FloatingPointType(BitsType):
    def __call__(self, *args, **kwds):
        self._info_check("width_exponent", "width_mantissa")
        
        raise NotImplementedError
    
    def derive(self, width_exponent: int, width_mantissa: int = None) -> 'SignalType':
        assert isinstance(width_exponent, int) and isinstance(width_mantissa, int)
        return FixedPointType({"width_exponent": width_exponent, "width_mantissa": width_mantissa})
    
    def literal(self) -> str:
        width_exponent = self.info.get("width_exponent", None)
        width_mantissa = self.info.get("width_mantissa", None)
        return f"{self.base_name}_{width_exponent}_{width_mantissa}" if width_exponent is not None and width_mantissa is not None else self.base_name


Signal = SignalType()

Auto = SignalType()

Bits = BitsType()

UFixedPoint = UFixedPointType()

SFixedPoint = SFixedPointType()

FloatingPoint = FloatingPointType()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]


print(Bits)
print(Bits[8])
print(SFixedPoint[16, 12])


"""
    base 仅一个, 合并时为最下的、与二者都有从属关系的类型.
        (不同支类型都有的话说明就是强制转换, 取最近公共祖先; 同支的话往下走更具体)
        (信息给了就是合理的! 出现不合理就是给的问题!)
    
    类型 (type) 指 SignalType 及其子类的对象
    类型的基类型 (base) 指 SignalType 及其子类本身的引用
    但显示基类型的名字 (base_name) 时用类型基础名, 也就是基类型的名称去掉最后的 "Type"
    所以下面为了方便用而定义的一系列对象和衍生对象命名最好就是基类型的名称
"""