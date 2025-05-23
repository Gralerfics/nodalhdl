# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from ..core.signal import *
from ..core.structure import *
from ..core.reusable import *
from .bits import *


class Constants(UniquelyNamedReusable):
    @staticmethod
    def setup(**constants) -> Structure:
        """
            Constants(<constant_name_0> = constant_object_0, ...)
        """
        pairs: List[Tuple[str, SignalValue]] = list(constants.items()) # fix the order
        
        def _assign(sub_wire_name: str, c: SignalValue):
            res = []
            if isinstance(c, BundleValue):
                raise NotImplementedError # TODO
                # for k, v in c._bundle_objects.items():
                #     res.extend(_assign(sub_wire_name + "." + k, v))
            elif isinstance(c, BitsValue):
                res.append(f"{sub_wire_name} <= \"{c.to_bits_string()}\";")
            return res
        
        s = Structure()
        
        ports = [s.add_port(name, Output[value.type]) for name, value in pairs]
        
        opt = s.add_substructure("opt", CustomVHDLOperator(
            {},
            {name: value.type for name, value in pairs},
            "\n".join([line for name, value in pairs for line in _assign(name, value)]),
            _unique_name = Constants.naming(**constants) + "_Core"
        ))
        
        for port in ports:
            s.connect(opt.IO.access(port.name), port)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_sha256_16()


class FixedPointMultiply(UniquelyNamedReusable):
    @staticmethod
    def setup(t: FixedPointType):
        assert t.belong(FixedPoint) and t.is_fully_determined
        
        s = Structure()
        a = s.add_port("a", Input[t])
        b = s.add_port("b", Input[t])
        r = s.add_port("r", Output[t])
        
        if t.belong(UFixedPoint):
            bits_mul = s.add_substructure("bits_mul", BitsUnsignedMultiply(Bits[t.W], Bits[t.W]))
        else:
            bits_mul = s.add_substructure("bits_mul", BitsSignedMultiply(Bits[t.W], Bits[t.W]))
        s.connect(a, bits_mul.IO.a)
        s.connect(b, bits_mul.IO.b)
        
        tc = s.add_substructure("tc", CustomVHDLOperator(
            {"i": Bits[t.W + t.W]},
            {"o": t},
            f"o <= i({t.W_frac + t.W - 1} downto {t.W_frac});",
            _unique_name = FixedPointMultiply.naming(t) + "_Truncator"
        ))
        s.connect(bits_mul.IO.r, tc.IO.i)
        s.connect(tc.IO.o, r)

        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class FixedPointMultiplyVHDL(UniquelyNamedReusable):
    @staticmethod
    def setup(t: FixedPointType):
        assert t.belong(FixedPoint) and t.is_fully_determined
        
        s = Structure()
        a = s.add_port("a", Input[t])
        b = s.add_port("b", Input[t])
        r = s.add_port("r", Output[t])
        
        mul = s.add_substructure("tc", CustomVHDLOperator(
            {"a": t, "b": t},
            {"r": t},
            f"o <= std_logic_vector(signed(a) * signed(b));\n" +
                f"r <= o({t.W_frac + t.W - 1} downto {t.W_frac});",
            f"signal o: std_logic_vector({t.W + t.W - 1} downto 0);",
            _unique_name = FixedPointMultiply.naming(t) + "_opt"
        ))
        s.connect(a, mul.IO.a)
        s.connect(b, mul.IO.b)
        s.connect(mul.IO.r, r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class FixedPointDivide(UniquelyNamedReusable):
    @staticmethod
    def setup(t: FixedPointType):
        assert t.belong(FixedPoint) and t.is_fully_determined
        
        s = Structure()
        a = s.add_port("a", Input[t])
        b = s.add_port("b", Input[t])
        r = s.add_port("r", Output[t]) # r(esult) not r(emainder)
        
        concat = s.add_substructure("concat", CustomVHDLOperator(
            {"i": t},
            {"o": Bits[t.W + t.W_frac]},
            f"o <= i & (1 to {t.W_frac} => '0');",
            _unique_name = FixedPointDivide.naming(t) + "_Concatenator"
        ))
        s.connect(a, concat.IO.i)
        
        div = s.add_substructure("bits_div", BitsSignedDivide(Bits[t.W + t.W_frac], Bits[t.W]))
        s.connect(concat.IO.o, div.IO.a)
        s.connect(b, div.IO.b)
        
        tc = s.add_substructure("tc", CustomVHDLOperator(
            {"i": Bits[t.W + t.W_frac]},
            {"o": t},
            f"o <= i({t.W - 1} downto 0);",
            _unique_name = FixedPointDivide.naming(t) + "_Truncator"
        ))
        s.connect(div.IO.q, tc.IO.i)
        s.connect(tc.IO.o, r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class FixedPointRemainder(UniquelyNamedReusable):
    @staticmethod
    def setup(t: FixedPointType):
        assert t.belong(FixedPoint) and t.is_fully_determined
        
        s = Structure()
        a = s.add_port("a", Input[t])
        b = s.add_port("b", Input[t])
        r = s.add_port("r", Output[t])
        
        div = s.add_substructure("bits_div", BitsSignedDivide(Bits[t.W], Bits[t.W]))
        s.connect(a, div.IO.a)
        s.connect(b, div.IO.b)
        s.connect(div.IO.r, r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


# TODO Modulus 则与 b 同号, 或 mod(x, y) = x - y * floor (x / y) ? 或 rem 加一个除数?


# class FixedPointCordicSqrt(UniquelyNamedReusable):
#     @staticmethod
#     def setup(t: FixedPointType, iter_num: int):
#         assert t.belong(FixedPoint) and t.is_fully_determined
        
#         s = Structure()
#         a = s.add_port("a", Input[t])
#         r = s.add_port("r", Output[t])
        
        
        
#         return s
    
#     naming = UniqueNamingTemplates.args_kwargs_all_values()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

