from typing import Dict

import hashlib


""" Exceptions """
class SignalTypeException(Exception): pass
class SignalTypeInstantiationException(Exception): pass
class SignalOperationException(Exception): pass


""" Metatypes """
class SignalType(type):
    """
        Reminder:
            1. Let me call the classes those are, or inherit the classes that use `metaclass = SignalType` STs (signal types).
            2. STs are classes (also objects in Python).
            3. The properties defined in SignalType will be inherited as class properties in STs.
            4. The methods defined in SignalType will be inherited as classmethods in STs, i.e. the first argument is `cls`.
    """
    _base: 'SignalType'
    
    @property
    def base(cls):
        return getattr(cls, "_base", cls)
    
    type_pool = {} # ensuring singularity
    
    def instantiate_type(cls, new_cls_name, properties = {}) -> 'SignalType': # `cls` here is the generated class, type(cls) is SignalType or its subclasses
        if not new_cls_name in cls.type_pool.keys():
            new_cls = SignalType(f"{new_cls_name}", (cls, ), {
                **properties,
                "_base": cls
            })
            cls.type_pool[new_cls_name] = new_cls
        return cls.type_pool.get(new_cls_name)
    
    """
        Class properties.
    """
    determined = False # width-determined w.r.t. signals TODO 目前定义好像不止, 例如 SFixedPoint[W] 位宽确定了但具体划分没有确定, 这种情况影响类型推导, 但确实可以生成, 要算吗?
    io_wrapper_included = False # whether IO Wrapper is included
    perfectly_io_wrapped = False # whether is perfectly IO-wrapped
    
    """
        Instantiation.
    """
    def __call__(cls, *args, **kwds):
        if not cls.determined:
            raise TypeError("Undetermined types cannot be instantiated")
        else:
            return super().__call__(*args, **kwds)
    
    """
        Representations.
    """
    def to_valid_string(cls):
        return cls.__name__
    
    def to_definition_string(cls): # eval this string can obtain the ST class
        return "Signal"
    
    def __repr__(cls): # [NOTICE] used in operator naming, should be valid string
        return cls.to_valid_string()
    
    """
        ST comparison and manipulation.
    """
    def normalize(cls: 'SignalType'):
        """
            After using dill to save and read Structure in different runs, the resulting ST is no longer the same object as the type created in .signal even though the content is the same, leading to errors in ==, is, issubclass, etc.
            So all places involving the `type_pool` and the class object itself need to be re-eval to the SignalType object in the new environment after converting the SignalType to a string definition.
        """
        return eval(cls.to_definition_string())
    
    def equals(cls: 'SignalType', other: 'SignalType'):
        """
            Judge the equivalence.
            Note that `is` is called, so the STs should be normalized.
        """
        cls, other = cls.normalize(), other.normalize()
        return cls is other
    
    def bases(cls: 'SignalType', other: 'SignalType'):
        return cls.base.equals(other)
    
    def belongs(cls: 'SignalType', other: 'SignalType'):
        """
            Whether `cls` belongs to `other`.
            This also means whether `cls` has more (or same) information that `other`.
            Note that `issubclass` is called, so the STs should be normalized.
            
            P.S. "information":
                Some STs have more information that others, e.g. UInt[8] is more useful than UInt or Auto.
                Such kind of relationship can be described by the inheritance relationship.
        """
        cls, other = cls.normalize(), other.normalize()
        return issubclass(cls, other)
    
    def merges(cls: 'SignalType', other: 'SignalType'):
        """
            Merge the information in `cls` and `other`.
            `cls` and `other` should have the same structure (ignoring IO wrappers).
            IO wrappers in both `cls` and `other` will be ignored.
        """
        t1 = cls.clear_io() if cls.io_wrapper_included else cls
        t2 = other.clear_io() if other.io_wrapper_included else other
        
        return t1.applys(t2)
    
    def applys(cls: 'SignalType', other: 'SignalType'):
        """
            Apply the information of `other` to `cls`.
            `cls` and `other` should have the same structure (ignoring IO wrappers).
            `cls` could have IO wrappers, and the IO wrappers in `other` will be ignored.
        """
        def _single_type_merges(a: 'SignalType', b: 'SignalType'):
            assert a.belongs(Bits) and b.belongs(Bits) # Single type ~ Bits (or its children)
            
            # if not a.base.belongs(b.base) and not b.base.belongs(a.base): # 基类型无继承关系, 不可合并 TODO 改了，可以合成祖宗
            #     return None
            if getattr(a, "W", None) == getattr(b, "W", None): # 有相同位宽或都没有位宽, 取基类型具体的
                # 要考虑 e.g. Bits[W]/SFixedPoint[W] 和 SFixedPoint[W_int, W_frac] 这种情况, 取后者细分的位宽信息 TODO 感觉条件写得不太好
                if a.base.belongs(b.base): # 基类型有从属取从属的
                    return a
                elif b.base.belongs(a.base): # 同上
                    return b
                else: # 没有从属关系，合成最近公共祖先，这里先用老祖宗 Bits 代着，以后来细细重构，乱七八糟的
                    return Bits[a.W] if hasattr(a, "W") else Bits
            elif (hasattr(a, "W") and not hasattr(b, "W")) or (not hasattr(a, "W") and hasattr(b, "W")): # 仅一个有位宽
                w, wo = (a, b) if hasattr(a, "W") else (b, a)
                if wo.belongs(Bits):
                    if wo.base.belongs(w.base): # and not wo.base.equals(w.base): # wo 能加位宽而且其基类型更具体, 则组合 wo 基类型和 w 的位宽信息
                        # TODO 为什么会进来 wo = SFixedPoint 和 w = SFixedPoint_16_12？
                        return wo.base[w.W]
                    else:
                        return w
                else:
                    return w # wo 没法加位宽, 则只保留 w [NOTICE] 目前没有这种情况, 只有 Bits 所谓的为 single_type (Auto 下的非 Bundle 类型), 除非后续添加
            else:
                return None
        
        if other.io_wrapper_included:
            other = other.clear_io()
        
        def _apply(d_port: SignalType, d_rtst: SignalType):
            if d_port.equals(Auto):
                return d_rtst
            elif d_rtst.equals(Auto):
                return d_port
            elif d_port.bases(Input):
                return Input[_apply(d_port.T, d_rtst)]
            elif d_port.bases(Output):
                return Output[_apply(d_port.T, d_rtst)]
            elif d_port.bases(Bundle) and d_rtst.bases(Bundle): # Bundles
                if d_port._bundle_types.keys() != d_rtst._bundle_types.keys():
                    return None
                return Bundle[{key: _apply(T1, T2) for (key, T1), (_, T2) in zip(d_port._bundle_types.items(), d_rtst._bundle_types.items())}]
            elif not d_port.bases(Bundle) and not d_rtst.bases(Bundle):
                return _single_type_merges(d_port, d_rtst)
            else:
                return None
        
        res = _apply(cls, other)
        if res is None:
            raise SignalTypeException(f"Signal types {cls.__name__} and {other.__name__} are conflicting")
        
        return res

    """
        ST methods related to IO wrappers.
        Classify STs with respect to IO wrappers they include:
            (1.) Have no IO wrapper, called non-IO-wrapped.
            (2.) All sub-signals up to the root have one and only one IO wrapper, called perfectly IO-wrapped.
            (3.) Have any sub-signal that is not wrapped, or nested wrapped, are invalid.
        This will be checked level by level as STs are built, and `io_wrapper_included` and `perfectly_io_wrapped` will be assigned automatically.
    """
    def flip_io(cls: 'SignalType'):
        """
            Recursively flip the IO wrappers under `cls`.
            `cls` should be perfectly IO-wrapped.
        """
        if not cls.perfectly_io_wrapped:
            raise SignalTypeException(f"Imperfect IO-wrapped signal type cannot be flipped")
        
        def _flip(t: SignalType):
            if t.bases(Input):
                return Output[t.T]
            elif t.bases(Output):
                return Input[t.T]
            else: # 一定是 Bundle, 如果是未被包裹的普通信号, 必然通不过 perfectly_io_wrapped 检查
                return Bundle[{key: _flip(T) for key, T in t._bundle_types.items()}]
        
        return _flip(cls)
    
    def clear_io(cls: 'SignalType'):
        """
            Recursively remove all IO wrappers.
        """
        if not cls.io_wrapper_included:
            return cls
        
        if cls.bases(Input) or cls.bases(Output):
            return cls.T
        elif cls.bases(Bundle):
            return Bundle[{key: T.clear_io() for key, T in cls._bundle_types.items()}]
        else: # ordinary
            return cls

class BitsType(SignalType): # every type whose width can be defined by base[W] should inherit Bits(Type)
    W: int # not assigned, not exist, only for type-hinting
    
    def __getitem__(cls, item) -> 'BitsType':
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
    W_int: int
    W_frac: int
    signed: bool
    
    def __getitem__(cls, item) -> 'FixedPointType':
        if isinstance(item, int): # only width
            width = item
            is_signed = cls.equals(SFixedPoint)
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{width}",
                {
                    "W": width,
                    "W_int": None,
                    "W_frac": None,
                    "signed": is_signed
                }
            )
            new_cls.determined = False
            
            return new_cls
        elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int): # int width and frac width
            integer_width, fraction_width = item
            is_signed = cls.equals(SFixedPoint)
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{integer_width}_{fraction_width}",
                {
                    "W": integer_width + fraction_width + int(is_signed),
                    "W_int": integer_width,
                    "W_frac": fraction_width,
                    "signed": is_signed
                }
            )
            new_cls.determined = True
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<integer_width (int)>, <fraction_width (int)>]")

class FloatingPointType(BitsType):
    W_exp: int
    W_frac: int
    
    def __getitem__(cls, item) -> 'FloatingPointType':
        if isinstance(item, int): # only width
            width = item
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{width}",
                {
                    "W": width,
                    "W_exp": None,
                    "W_frac": None
                }
            )
            new_cls.determined = False
            
            return new_cls
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
    T: SignalType
    
    def __getitem__(cls, item) -> 'IOWrapperType':
        if isinstance(item, SignalType):
            T = item
            
            if T.io_wrapper_included:
                raise SignalTypeException(f"Nesting is not allowed for IO Wrappers")
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{T.__name__}",
                {
                    "T": T
                }
            )
            new_cls.determined = item.determined # the determinacy of the wrapper is decided by the wrapped ST
            new_cls.io_wrapper_included = True # now wrapped
            new_cls.perfectly_io_wrapped = True # wrap on the root, so perfectly wrapped
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<signal_type (SignalType)>]")

class BundleType(SignalType):
    _bundle_types: Dict[str, SignalType]
    
    def __getitem__(cls, item) -> 'BundleType':
        if isinstance(item, dict) and all([isinstance(x, SignalType) for x in item.values()]):
            bundle_types: dict = item
            
            new_cls = cls.instantiate_type(
                f"{cls.__name__}_{hashlib.md5(str(bundle_types).encode('utf-8')).hexdigest()}",
                {
                    "_bundle_types": bundle_types, # signal name -> signal type
                    **bundle_types # for convenience
                }
            )
            new_cls.determined = all([x.determined for x in bundle_types.values()]) # determined when all sub-signals are determined
            new_cls.io_wrapper_included = any([x.io_wrapper_included for x in bundle_types.values()]) # IO wrapped when any sub-signal is IO-wrapped
            new_cls.perfectly_io_wrapped = all([x.perfectly_io_wrapped for x in bundle_types.values()]) # perfectly wrapped when all sub-signals are perfectly wrapped
            
            return new_cls
        else:
            raise SignalTypeException(f"Invalid parameter(s) \'{item}\' for type {cls.__name__}[<members (dict[str, SignalType])>]")


""" Types """
class Signal(metaclass = SignalType): pass

class Auto(Signal):
    @classmethod
    def to_definition_string(cls):
        return "Auto"
    
    def to_bits_string(self):
        return None

class Bits(Auto, metaclass = BitsType):
    @classmethod
    def to_definition_string(cls):
        return f"Bits[{cls.W}]" if hasattr(cls, 'W') else "Bits"
    
    def __init__(self, value = 0):
        if isinstance(value, int):
            self.set_value(value)
        elif isinstance(value, str):
            self.set_value(int(value[-self.W:], base = 2))
        else:
            raise SignalTypeInstantiationException
    
    def __repr__(self):
        return "b" + self.to_bits_string()
    
    def set_value(self, value: int):
        self.value = value % (1 << self.W)
    
    def to_bits_string(self):
        return bin(self.value)[2:].zfill(self.W)[-self.W:]

Bit = Bits[1]
Byte = Bits[8]

class UInt(Bits):
    @classmethod
    def to_definition_string(cls):
        return f"UInt[{cls.W}]" if hasattr(cls, 'W') else "UInt"
    
    def __repr__(self):
        return f"{self.value}.U({self.W}.W)"
    
    def __add__(self, other):
        if isinstance(other, UInt):
            return UInt[max(self.W, other.W)](self.value + other.value)
        else:
            raise SignalOperationException
    
    def __sub__(self, other):
        if isinstance(other, UInt):
            return UInt[max(self.W, other.W)](self.value - other.value)
        else:
            raise SignalOperationException
    
    __radd__ = __add__
    __rsub__ = __sub__

UInt8 = UInt[8]
UInt16 = UInt[16]
UInt32 = UInt[32]
UInt64 = UInt[64]

class SInt(Bits):
    @classmethod
    def to_definition_string(cls):
        return f"SInt[{cls.W}]" if hasattr(cls, 'W') else "SInt"
    
    def __init__(self, value: int = 0):
        self.set_value(value)
    
    def __repr__(self):
        return f"{self.value}.S({self.W}.W)"
    
    def __add__(self, other):
        if isinstance(other, SInt):
            return SInt[max(self.W, other.W)](self.value + other.value)
        else:
            raise SignalOperationException
    
    def __sub__(self, other):
        if isinstance(other, SInt):
            return SInt[max(self.W, other.W)](self.value - other.value)
        else:
            raise SignalOperationException
    
    __radd__ = __add__
    __rsub__ = __sub__
    
    def set_value(self, value: int):
        half = 1 << self.W - 1
        self.value = (value + half) % (1 << self.W) - half
    
    def to_bits_string(self):
        num = self.value
        if num < 0:
            num = (1 << self.W) + num
        return bin(num)[2:].zfill(self.W)[-self.W:]

Int8 = SInt[8]
Int16 = SInt[16]
Int32 = SInt[32]
Int64 = SInt[64]

class UFixedPoint(UInt, metaclass = FixedPointType):
    @classmethod
    def to_definition_string(cls):
        if getattr(cls, "W_int", None) is not None and getattr(cls, "W_frac", None) is not None:
            return f"UFixedPoint[{cls.W_int}, {cls.W_frac}]"
        elif getattr(cls, "W", None) is not None:
            return f"UFixedPoint[{cls.W}]"
        else:
            return "UFixedPoint"
        
    def __init__(self, value = 0.0):
        if isinstance(value, float):
            self.set_value(value)
        elif isinstance(value, str):
            self.set_value(int(value[-self.W:], base = 2))
        else:
            raise SignalTypeInstantiationException
    
    def __repr__(self):
        return f"Q{self.W_int}.{self.W_frac}({self.to_float})"
    
    def __add__(self, other):
        if isinstance(other, UFixedPoint) and self.W_int == other.W_int and self.W_frac == other.W_frac:
            return UFixedPoint[self.W_int, self.W_frac](self.to_float + other.to_float) # TODO 这样不一定符合实际结果
        else:
            raise SignalOperationException
    
    def __sub__(self, other):
        if isinstance(other, UFixedPoint) and self.W_int == other.W_int and self.W_frac == other.W_frac:
            return UFixedPoint[self.W_int, self.W_frac](self.to_float - other.to_float) # TODO 同上
        else:
            raise SignalOperationException
    
    __radd__ = __add__
    __rsub__ = __sub__
    
    def set_value(self, value: float):
        value_int = int(value * (1 << self.W_frac))
        self.value = value_int % (1 << self.W) # TODO 整数截断这样截吗？

    @property
    def to_float(self):
        return self.value / (1 << self.W_frac)

class SFixedPoint(SInt, metaclass = FixedPointType): # W = W_int + W_frac + 1 (sign bit, not in W_int)
    @classmethod
    def to_definition_string(cls):
        if getattr(cls, "W_int", None) is not None and getattr(cls, "W_frac", None) is not None:
            return f"SFixedPoint[{cls.W_int}, {cls.W_frac}]"
        elif getattr(cls, "W", None) is not None:
            return f"SFixedPoint[{cls.W}]"
        else:
            return "SFixedPoint"
    
    def __init__(self, value = 0.0):
        if isinstance(value, float) or isinstance(value, int):
            self.set_value(value)
        elif isinstance(value, str):
            self.set_value(int(value[-self.W:], base = 2))
        else:
            raise SignalTypeInstantiationException
    
    def __repr__(self):
        return f"sQ{self.W_int}.{self.W_frac}({self.to_float})"
    
    def __add__(self, other):
        if isinstance(other, SFixedPoint) and self.W_int == other.W_int and self.W_frac == other.W_frac:
            return SFixedPoint[self.W_int, self.W_frac](self.to_float + other.to_float) # TODO 同上
        else:
            raise SignalOperationException
    
    def __sub__(self, other):
        if isinstance(other, SFixedPoint) and self.W_int == other.W_int and self.W_frac == other.W_frac:
            return SFixedPoint[self.W_int, self.W_frac](self.to_float - other.to_float) # TODO 同上
        else:
            raise SignalOperationException
    
    __radd__ = __add__
    __rsub__ = __sub__

    @property
    def to_float(self):
        return self.value / (1 << self.W_frac)
    
    def set_value(self, value: float):
        value_int = int(value * (1 << self.W_frac))
        half = 1 << self.W - 1
        self.value = (value_int + half) % (1 << self.W) - half # TODO 整数截断这样截吗？符号位考虑了吗？
    
    # def to_bits_string(self): # TODO 需要检查
    #     num = self.value
    #     if num < 0:
    #         num = (1 << self.W) + num
    #     return bin(num)[2:].zfill(self.W)[-self.W:]

class FloatingPoint(Bits, metaclass = FloatingPointType):
    @classmethod
    def to_definition_string(cls):
        if getattr(cls, "W_exp", None) is not None and getattr(cls, "W_frac", None) is not None:
            return f"FloatingPoint[{cls.W_exp}, {cls.W_frac}]"
        elif getattr(cls, "W", None) is not None:
            return f"FloatingPoint[{cls.W}]"
        else:
            return "FloatingPoint"
    
    def to_bits_string(self):
        return NotImplementedError

Float = FloatingPoint[8, 23]
Double = FloatingPoint[11, 52]

class IOWrapper(Signal, metaclass = IOWrapperType):
    @classmethod
    def to_definition_string(cls):
        return f"IOWrapper[{cls.T.to_definition_string()}]" if hasattr(cls, 'T') else "IOWrapper"
    
    def __init__(self):
        raise SignalTypeInstantiationException("IO wrappers can not be instantiated")

class Input(IOWrapper):
    @classmethod
    def to_definition_string(cls):
        return f"Input[{cls.T.to_definition_string()}]" if hasattr(cls, 'T') else "Input"

class Output(IOWrapper):
    @classmethod
    def to_definition_string(cls):
        return f"Output[{cls.T.to_definition_string()}]" if hasattr(cls, 'T') else "Output"

class Bundle(Auto, metaclass = BundleType):
    @classmethod
    def to_definition_string(cls):
        return "Bundle[{" + ", ".join([f"\"{k}\": {v.to_definition_string()}" for k, v in cls._bundle_types.items()]) + "}]" if hasattr(cls, '_bundle_types') else "Bundle"
    
    def __init__(self, value: dict = {}):
        self._bundle_objects: Dict[str, Signal] = {}
        for k, v in self._bundle_types.items():
            default_value = value.get(k)
            self._bundle_objects[k] = v(default_value) if default_value is not None else v()
            setattr(self, k, self._bundle_objects[k])
    
    def __repr__(self):
        return "{" + ", ".join([f"\"{k}\": {str(v)}" for k, v in self._bundle_objects.items()]) + "}"

