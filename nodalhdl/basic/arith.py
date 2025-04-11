from ..core.signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle
from ..core.structure import Structure, RuntimeId, StructureGenerationException, IOProxy
from ..core.hdl import HDLFileModel

from typing import Dict


class ArgsOperatorMeta(type):
    def __getitem__(cls, args):
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
    pool: Dict[str, Structure] = {}
    
    @staticmethod
    def setup(*args) -> Structure: return Structure()
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy): pass
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy): pass
    
    @classmethod
    def naming(cls, *args): return f"{cls.__name__}_{'_'.join(map(str, args))}" # [NOTICE] use valid string


class Add(ArgsOperator):
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


class Subtract(Add):
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


class GetAttribute(ArgsOperator):
    @staticmethod
    def setup(*args) -> Structure:
        ti, to = args[0], args[0]
        for key in args[1]:
            to = to._bundle_types[key]
        
        s = Structure()
        
        s.add_port("i", Input[ti])
        s.add_port("o", Output[to])
        
        s.custom_params["path"] = args[1]
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        ti, to = io.i.type, io.o.type
        
        f = lambda t: t.__name__ if t.belongs(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
        i: in {f(ti)};
        o: out {f(to)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    o <= i.{'.'.join(s.custom_params["path"])};
end architecture;
"""
        )
    
    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{args[0].__name__[7:15]}_{'_'.join(map(str, args[1]))}"

