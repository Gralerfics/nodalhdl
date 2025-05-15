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
    def __init__(self, info: dict = {}, base: str = None): # do not call by yourself
        self.info = info
        self.info["bases"] = self.info.get("bases", []) + [base] # add base information
    
    """ @override """
    def __getitem__(self, item) -> 'SignalType': # derived type (by pass arguments into "[]")
        raise SignalTypeException(f"{self.__name__} has no derived types")
    
    """ @override """
    def __call__(self, *args, **kwds): # -> 'SignalValue': # 类型实例化
        pass
    
    def __repr__(self):
        return self.literal()
    
    """ @override """
    def literal(self) -> str: # valid string
        return "Signal"
    
    @property
    def is_determined(self):
        return "width" in self.info.keys()
    
    def uid(self) -> str:
        """
            calculate a unique and consistent id for the signal type,
            according to the info.
        """
        pass # TODO
    
    def best_match(self) -> 'SignalType':
        """
            匹配 info 中信息的最优的纯类型 (len(bases) == 1)
        """
        pass # TODO
    
    def merge(self, other: 'SignalType'):
        pass # TODO merge, merge_by? 返回新的还是允许修改?


class BitsType(SignalType):
    def __getitem__(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return BitsType(info = {"width": width}, base = "Bits")
    
    def __call__(self, *args, **kwds):
        pass # TODO
    
    def literal(self) -> str: # valid string
        width = self.info.get("width", None)
        return f"Bits_{width}" if width is not None else "Bits"


Signal = SignalType(base = "Signal")

Auto = SignalType(base = "Auto")

Bits = BitsType(base = "Bits")


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]


print(Bits)
print(Bits[8])

