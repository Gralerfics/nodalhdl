from ..core.signal import SignalType, BundleType, Signal, Bits, UInt, SInt, Input, Output, Auto, Bundle
from ..core.structure import Structure, RuntimeId, StructureGenerationException, IOProxy
from ..core.hdl import HDLFileModel

import hashlib

from typing import Dict


class ArgsOperatorMeta(type):
    pool: Dict[str, Structure] = {}
    
    def __getitem__(cls, args):
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        
        s = cls.setup(*args)
        
        s.custom_deduction = cls.deduction
        s.custom_generation = cls.generation
        
        rid = RuntimeId.create()
        s.deduction(rid)
        
        if s.is_runtime_applicable:
            s.apply_runtime(rid)
        
        if s.is_reusable:
            unique_name = cls.naming(*args) # should be a valid string and unique across all operators
            if unique_name in cls.pool:
                return cls.pool[unique_name]
            else:
                s.unique_name = unique_name
                cls.pool[unique_name] = s
        
        return s


class ArgsOperator(metaclass = ArgsOperatorMeta):
    @staticmethod
    def setup(*args) -> Structure: return Structure()
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy): pass
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy): pass
    
    @classmethod
    def naming(cls, *args): return f"{cls.__name__}_{'_'.join(map(str, args))}" # [NOTICE] use valid string


class IntAdd(ArgsOperator):
    @staticmethod
    def setup(*args) -> Structure:
        s = Structure()
        
        s.add_port("op1", Input[args[0]])
        s.add_port("op2", Input[args[1]])
        s.add_port("res", Output[Auto])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        t1, t2, tr = io.op1.type, io.op2.type, io.res.type
        
        if t1.determined and t2.determined:
            io.res.update(t1.base[max(t1.W, t2.W)])
        elif tr.determined and t1.determined and t1.W < tr.W:
            io.op2.update(tr.base[tr.W])
        elif tr.determined and t2.determined and t2.W < tr.W:
            io.op1.update(tr.base[tr.W])
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        t1, t2, tr = io.op1.type, io.op2.type, io.res.type
        
        if not (t1.belongs(UInt) and t2.belongs(UInt) or t1.belongs(SInt) and t2.belongs(SInt)):
            raise StructureGenerationException(f"Only accept UInt + UInt or SInt + SInt")

        if not tr.W == max(t1.W, t2.W):
            raise StructureGenerationException(f"Result width should be the maximum of the two operands")
        
        ts = "unsigned" if t1.belongs(UInt) else "signed"
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in std_logic_vector({t1.W - 1} downto 0);
        op2: in std_logic_vector({t2.W - 1} downto 0);
        res: out std_logic_vector({tr.W - 1} downto 0)
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector({ts}(op1) + {ts}(op2));
end architecture;
"""
        )


class IntSubtract(IntAdd):
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        t1, t2, tr = io.op1.type, io.op2.type, io.res.type
        
        if not (t1.belongs(UInt) and t2.belongs(UInt) or t1.belongs(SInt) and t2.belongs(SInt)):
            raise StructureGenerationException(f"Only accept UInt - UInt or SInt - SInt")

        if not tr.W == max(t1.W, t2.W):
            raise StructureGenerationException(f"Result width should be the maximum of the two operands")
        
        ts = "unsigned" if t1.belongs(UInt) else "signed"
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in std_logic_vector({t1.W - 1} downto 0);
        op2: in std_logic_vector({t2.W - 1} downto 0);
        res: out std_logic_vector({tr.W - 1} downto 0)
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector({ts}(op1) - {ts}(op2));
end architecture;
"""
        )


class Decomposition(ArgsOperator):
    """
        Decomposition[type]: all shallow members TODO to be tested
        Decomposition[type, [<keys_0>], ...]: selected members
    """
    @staticmethod
    def setup(*args) -> Structure:
        out_nums = len(args) - 1
        assert out_nums >= 0
        
        ti: BundleType = args[0]
        to = []
        paths = args[1:]
        
        if out_nums == 0:
            keys = ti._bundle_types.keys()
            out_nums = len(keys)
            paths = [[key] for key in keys]
        
        for path in paths:
            if isinstance(path, list) or isinstance(path, tuple):
                t = ti
                for key in path:
                    t = t._bundle_types[key]
                to.append(t)
            else: # str
                to.append(ti._bundle_types[path])
        
        s = Structure()
        
        s.add_port("i", Input[ti])
        for idx, t in enumerate(to):
            s.add_port(f"o{idx}", Output[t])
        
        s.custom_params["paths"] = paths
        s.custom_params["to"] = to
        
        return s
    
    # TODO deduction
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        ti, to = io.i.type, s.custom_params["to"]
        
        f = lambda t: t.__name__ if t.belongs(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"
        
        port_str = ";\n".join([f"        o{idx}: out {f(t)}" for idx, t in enumerate(to)])
        assign_str = "\n".join([f"    o{idx} <= i.{'.'.join(s.custom_params["paths"][idx])};" for idx in range(len(to))])
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
        i: in {f(ti)};
{port_str}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
{assign_str}
end architecture;
"""
        )
    
    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{args[0].__name__[7:15]}_{"_".join(["_".join(map(str, path)) for path in args[1:]])}"


class Composition(ArgsOperator):
    """
        Composition[type]: all shallow members
        Composition[type, [<keys_0>], ...]: selected members
    """
    pass # TODO


class Constant(ArgsOperator):
    """
        Constant[signal_0, ...]
        TODO to be tested
    """
    @staticmethod
    def setup(*args) -> Structure:
        assert all([isinstance(arg, Signal) for arg in args])
        
        s = Structure()
        
        for idx, signal in enumerate(args):
            s.add_port(f"c{idx}", Output[type(signal)])
        
        s.custom_params["constants"] = args
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        for idx, c in enumerate(s.custom_params["constants"]):
            port = io.__getattr__(f"c{idx}")
            port.update(type(c))
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        constants = s.custom_params["constants"]
        
        f = lambda t: t.__name__ if t.belongs(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"
        
        port_str = ";\n".join([f"        c{idx}: out {f(type(c))}" for idx, c in enumerate(constants)])
        
        def _assign(sub_wire_name: str, c: Signal):
            res = ""
            if isinstance(c, Bundle):
                for k, v in c._bundle_objects.items():
                    res += _assign(sub_wire_name + "." + k, v)
            elif isinstance(c, Bits):
                res += f"    {sub_wire_name} <= \"{c.to_bits_string()}\";\n"
            return res
        
        assign_str = ""
        for idx, c in enumerate(constants):
            assign_str += _assign(f"c{idx}", c)
        assign_str = assign_str[:-1]

        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
{port_str}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
{assign_str}
end architecture;
"""
        )
    
    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{'_'.join([hashlib.md5(str(arg).encode('utf-8')).hexdigest()[:8] for arg in args])}" # [NOTICE] use valid string

