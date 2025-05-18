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
    
    naming = UniqueNamingTemplates.args_kwargs_md5_16()


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


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

