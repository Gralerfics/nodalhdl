# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

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
    "DIR": "direction"
}

class SignalType: # should not be modified, i.e. operations return new objects.
    W: int
    W_int: int
    W_frac: int
    W_exp: int
    W_mant: int
    BT: Dict[str, 'SignalType']
    DIR: 'IOWrapper'
    
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
    
    def __eq__(self, other: 'SignalType'):
        if not isinstance(other, SignalType):
            return False
        return self.uid == other.uid # .uid does not represent everything in .info; this is not `is`, which compare the memory ids
    
    def __hash__(self): # __eq__ is overrided, __hash__ must be defined too
        return hash(self.uid)
    
    def __le__(self, other: 'SignalType'):
        return self.belong(other)
    
    def __lt__(self, other: 'SignalType'):
        return self <= other and self != other
    
    def exhibital_full(self) -> str:
        return self.exhibital() if self.DIR is None else self.DIR.validal() + "[" + self.exhibital() + "]"
    
    """ @override """
    def __call__(self, *args, **kwds) -> 'SignalValue': # type instantiation
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    """ @override """
    def derive(self, *args, **kwargs) -> 'SignalType': # derived type
        raise SignalTypeException(f"{self.__name__} has no derived types")
    
    """ @override """
    def validal(self) -> str: # valid string, and only includes the information that the base type needs, usually excludes the direction [NOTICE]
        return "Signal"
    
    """ @override """
    def exhibital(self) -> str: # display string
        return self.validal()
    
    """ @override """
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined
    
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
    def uid(self) -> str:
        return hashlib.sha256(self.validal().encode('utf-8')).hexdigest() # see .validal()
    
    @property
    def is_determined(self) -> bool: # width-determined or subtype determined
        return self.W is not None
    
    @property
    def is_io_perfect(self) -> bool:
        if self.DIR is not None:
            return True
        
        if self.belong(Bundle):
            return self.BT is not None and all([t.is_io_perfect for t in self.BT.values()])
        
        return False
    
    @property
    def is_io_existing(self) -> bool:
        if self.DIR is not None:
            return True
        
        if self.belong(Bundle):
            return self.BT is not None and any([t.is_io_existing for t in self.BT.values()])
        
        return False
    
    def _inst_info_check(self, *keys):
        for key in keys:
            value = self.info.get(key, None)
            if value is None:
                raise SignalTypeInstantiationException(f"missing `{key}` when instantiating {self.base_name}")
    
    @staticmethod
    def _base_equal(base_0: type, base_1: type) -> bool:
        return base_0.__name__ == base_1.__name__
    
    @staticmethod
    def _base_belong(base_0: type, base_1: type) -> bool:
        base_0_norm = eval(base_0.__name__)
        base_1_norm = eval(base_1.__name__)
        return issubclass(base_0_norm, base_1_norm)
    
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
    
    def base_equal(self, other: 'SignalType') -> bool:
        return SignalType._base_equal(self.base, other.base)
    
    def base_belong(self, other: 'SignalType') -> bool:
        # why not use isinstance(self, other.base)? type consistence in persistence need to be considered, see _base_belong().
        return SignalType._base_belong(self.base, other.base)
    
    def belong(self, other: 'SignalType') -> bool: # base_belong, and self has all (same) properties in other
        return self.base_belong(other) and all([self.info.get(other_key, None) == other_v for other_key, other_v in other.info.items()])
    
    # def match(self, other: 'SignalType') -> bool:
    #     raise NotImplementedError
    
    # def isomorphic(self, other: 'SignalType') -> bool:
    #     raise NotImplementedError
    
    def apply(self, other: 'SignalType') -> 'SignalType':
        assert self.belong(Bits) and other.belong(Bits)
        other = other.io_clear() # ignore other's IO-wrappers
        
        new_info = {}
        keys = set(self.info.keys()) | set(other.info.keys())
        for key in keys:
            self_value, other_value = self.info.get(key, None), other.info.get(key, None) # will not be both None in keys
            if self_value is None: # only one has the property, keep it
                new_info[key] = other_value
            elif other_value is None: # same
                new_info[key] = self_value
            elif key != "bundle_types" and self_value == other_value: # matched property, keep it (excluding bundle_types)
                new_info[key] = self_value
            elif key == "bundle_types" and self_value.keys() == other_value.keys(): # matched bundle_types should be recursively applied
                self_value: Dict[str, SignalType]
                other_value: Dict[str, SignalType]
                new_bundle_types: Dict[str, SignalType] = {k: self_t.apply(other_value.get(k)) for k, self_t in self_value.items()}
                new_info[key] = new_bundle_types
                
                if all([t.is_determined for t in new_bundle_types.values()]):
                    new_info["width"] = sum([t.W for t in new_bundle_types.values()]) # [NOTICE] here Bundle is not created by using .derive(), so width should be calculated when determined
            else: # conflicting properties
                if key == "width": # width conflicting, exception (width-conflicting bundles will be checked here too)
                    raise SignalTypeException(f"Width-conflicing types {self} and {other}")
                else: # not width, deprecate
                    pass
        
        merged_base = SignalType._base_merge(self.base, other.base)
        new_type = merged_base(new_info)
        
        return new_type
    
    def merge(self, other: 'SignalType') -> 'SignalType':
        return self.io_clear().apply(other.io_clear())
    
    def io_clear(self) -> 'SignalType':
        if self.DIR is not None: # nested IO-wrapper is impossible
            return self.base({k: v for k, v in self.info.items() if k != "direction"})
        elif self.belong(Bundle) and self.BT is not None:
            return self.base({
                "bundle_types": {k: t.io_clear() for k, t in self.BT.items()}
            })
        else:
            return self
    
    def io_flip(self) -> 'SignalType':
        if self.DIR is not None: # nested IO-wrapper is impossible
            return self.base({k: (v.flip if k == "direction" else v) for k, v in self.info.items()})
        elif self.belong(Bundle) and self.BT is not None:
            return self.base({
                "bundle_types": {k: t.io_flip() for k, t in self.BT.items()}
            })
        else:
            return self

class BitsType(SignalType):
    def __call__(self, *args, **kwds):
        self._inst_info_check("width")
        return BitsValue(self, *args, **kwds)
    
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return self.base({"width": width})
    
    def validal(self) -> str:
        return f"{self.base_name}_{self.W}" if self.W is not None else self.base_name

class FixedPointType(BitsType):
    def __init__(self, info = {}):
        super().__init__(info)
        
        if self.W is not None and self.W_int is not None and self.W_frac is not None and self.W != self.W_int + self.W_frac: # deprecate wrong info
            del self.info["width_integer"]
            del self.info["width_fraction"]
        
        if self.W is None and self.W_int is not None and self.W_frac is not None: # generate new info if possible
            self.info["width"] = self.W_int + self.W_frac
    
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined and self.W_int is not None and self.W_frac is not None

    def derive(self, width_integer: int, width_fraction: int) -> 'SignalType':
        assert isinstance(width_integer, int) and isinstance(width_fraction, int)
        return self.base({"width_integer": width_integer, "width_fraction": width_fraction, "width": width_integer + width_fraction})
    
    def validal(self) -> str:
        return f"{self.base_name}_{self.W_int}_{self.W_frac}" if self.W_int is not None and self.W_frac is not None else self.base_name

class UFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._inst_info_check("width_integer", "width_fraction")
        return UFixedPointValue(self, *args, **kwds)

class SFixedPointType(FixedPointType):
    def __call__(self, *args, **kwds):
        self._inst_info_check("width_integer", "width_fraction")
        return SFixedPointValue(self, *args, **kwds)

class IntegerType(FixedPointType):
    def __init__(self, info = {}):
        super().__init__(info)
        
        if self.W_int is not None: # deprecate old info
            del self.info["width_integer"]
        
        if self.W is not None: # generate new info if possible
            self.info["width_integer"] = self.W
        self.info["width_fraction"] = 0
    
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    def derive(self, width: int) -> 'SignalType':
        assert isinstance(width, int)
        return self.base({"width": width, "width_integer": width}) # , "width_fraction": 0})
    
    def validal(self):
        return f"{self.base_name}_{self.W}" if self.W is not None else self.base_name

class UIntType(IntegerType, UFixedPointType):
    def __call__(self, *args, **kwds):
        self._inst_info_check("width")
        return UFixedPointValue(self, *args, **kwds)

class SIntType(IntegerType, SFixedPointType):
    def __call__(self, *args, **kwds):
        self._inst_info_check("width")
        return SFixedPointValue(self, *args, **kwds)

class FloatingPointType(BitsType):
    def __init__(self, info = {}):
        super().__init__(info)
        
        if self.W is not None and self.W_exp is not None and self.W_mant is not None and self.W != 1 + self.W_exp + self.W_mant: # deprecate wrong info
            del self.info["width_exponent"]
            del self.info["width_mantissa"]
        
        if self.W is None and self.W_exp is not None and self.W_mant is not None: # generate new info if possible
            self.info["width"] = 1 + self.W_exp + self.W_mant
    
    def __call__(self, *args, **kwds):
        self._inst_info_check("width_exponent", "width_mantissa")
        return FloatingPointValue(self, *args, **kwds)
    
    @property
    def is_fully_determined(self) -> bool:
        return self.is_determined and self.W_exp is not None and self.W_mant is not None
    
    def derive(self, width_exponent: int, width_mantissa: int) -> 'SignalType':
        assert isinstance(width_exponent, int) and isinstance(width_mantissa, int)
        return self.base({"width_exponent": width_exponent, "width_mantissa": width_mantissa})
    
    def validal(self) -> str:
        return f"{self.base_name}_{self.W_exp}_{self.W_mant}" if self.W_exp is not None and self.W_mant is not None else self.base_name

class BundleType(BitsType):
    def __init__(self, info = {}):
        super().__init__(info)
        
        # deprecate wrong info TODO
        
        if self.BT is not None and all([t.is_determined for t in self.BT.values()]): # generate new info if possible
            width = sum([t.W for t in self.BT.values()])
            self.info["width"] = width
    
    def __call__(self, *args, **kwds):
        self._inst_info_check("bundle_types")
        return BundleValue(self, *args, **kwds)
    
    def derive(self, bundle_types: Dict[str, SignalType]) -> 'SignalType':
        assert isinstance(bundle_types, dict)
        return self.base({"bundle_types": bundle_types})
    
    def validal(self) -> str:
        if self.BT is not None:
            return self.base_name + "_" + hashlib.sha256(str(self.BT).encode('utf-8')).hexdigest() # used in core.hdl
        else:
            return self.base_name
    
    def exhibital(self) -> str:
        if self.BT is not None:
            return self.base_name + "{" + ", ".join([f"{k}: {t.exhibital()}" for k, t in self.BT.items()]) + "}"
        else:
            return self.base_name
    
    def exhibital_full(self) -> str:
        if self.BT is not None:
            res = self.base_name + "{" + ", ".join([f"{k}: {t.exhibital_full()}" for k, t in self.BT.items()]) + "}"
        else:
            res = self.base_name
        return res if self.DIR is None else self.DIR.validal() + "[" + res + "]"

class IOWrapper(SignalType): # `Wrapper` is different from `Type`, they only derive to other types
    def __init__(self, info = {}):
        super().__init__(info)
        self.info["direction"] = self
    
    def __call__(self, *args, **kwds):
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be instantiated")
    
    @property
    def base_name(self) -> str: # "xxxWrapper" -> "xxx"
        return self.base.__name__[:-7]
    
    @property
    def flip(self) -> 'IOWrapper':
        raise SignalTypeInstantiationException(f"{self.base_name} cannot be flipped")
    
    def validal(self) -> str:
        return self.base_name

class InputWrapper(IOWrapper):
    @property
    def flip(self):
        return Output
    
    def derive(self, wrapped_type: SignalType) -> 'SignalType':
        assert isinstance(wrapped_type, SignalType) and not wrapped_type.is_io_existing
        return wrapped_type.base({"direction": Input, **wrapped_type.info})

class OutputWrapper(IOWrapper):
    @property
    def flip(self):
        return Input

    def derive(self, wrapped_type: SignalType) -> 'SignalType':
        assert isinstance(wrapped_type, SignalType) and not wrapped_type.is_io_existing
        return wrapped_type.base({"direction": Output, **wrapped_type.info})


Bits = BitsType()
Bit = Bits[1]
Byte = Bits[8]

Auto = Bits

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

Input = InputWrapper()
Output = OutputWrapper()


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
    print(Bits, "->", "Bits")
    print(Bits[8], "->", "Bits_8")
    print(SFixedPoint[16, 12], "->", "SFixedPoint_16_12")
    print(SInt[8], "->", "SInt_8")

    print(SFixedPoint[1, 1](1.5), "->", "-0.5")
    print(SFixedPoint[1, 1](2.5), "->", "0.5")
    
    print(Output[Bits].DIR == Output, "->", "True")

    print(" === ")

    S = Bundle[{
        "a": Input[Auto],
        "b": Output[UInt[8]],
        "c": Input[Auto],
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

    print(S.exhibital_full())
    print(T.exhibital_full())
    print(S.io_clear().exhibital_full())
    print(T.io_clear().exhibital_full())
    print(S.merge(T).exhibital_full())

    print(" === ")

    print(S.exhibital_full())
    print(P.exhibital_full())
    print(S.apply(P).exhibital_full())

    print(" === ")

    print(T.exhibital_full())
    print(T.io_flip().exhibital_full())
    print(T.io_clear().exhibital_full())

    print(" === ")
    
    print(UInt[8].info)
    print(SFixedPoint[4, 4].info)
    print(UInt[8].merge(SFixedPoint[4, 4]))
    print(UInt[8].merge(SFixedPoint[4, 4]).info)

    print(" === ")
    
    print(UInt[8].merge(SInt[8]).info)
    print(SFixedPoint[3, 4].merge(UFixedPoint[3, 4]).info)

    print(" !== ")
    
    print(UFixedPoint[3, 4].merge(UInt))
    print(UFixedPoint[3, 4].info)
    print(UInt.info)
    print(UFixedPoint[3, 4].merge(UInt).info) # [NOTICE]

    print(" === ")
    
    print(SFixedPoint[3, 3].W)
    print(SFixedPoint[3, 3].W_frac)
    print(Input[SFixedPoint[3, 3]].DIR)
    print(S.BT)

    print(" === ")
    
    print(S.uid)
    print(SS.uid)

    print(" === ")
    
    print(UInt64.belong(UFixedPoint[64, 0]))
    print(UInt64 <= UFixedPoint[64, 0])

    print(" === ")

    print(Bundle[{"a": UInt[8], "b": SFixedPoint[3, 2]}].merge(UInt[13]))

    print(" === ")
    
    print(SFixedPoint[16, 12](0.999).to_bits_string())
    print(SFixedPoint[16, 12](0.9999).to_bits_string())
    print(SFixedPoint[16, 12](0.99999999999).to_bits_string())
    print(SFixedPoint[16, 12](0.999999999999).to_bits_string())

    print(" === ")

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


"""
    TODO 为了可读性（好像并不太可读）, 暂时不把 Bundle 转 record 改成全用 std_logic_vector 表示了 (要修改的话主要涉及 hdl 的 type_decl, 常数以及寄存器的初始化).
"""