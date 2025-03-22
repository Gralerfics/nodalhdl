from ..core.signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle
from ..core.structure import Structure, RuntimeId, StructureGenerationException, IOProxy
from ..core.hdl import HDLFileModel
from ..core.util import static


def Addition(op1_type: SignalType, op2_type: SignalType) -> Structure:
    s = Structure()
    
    s.add_port("op1", Input[op1_type])
    s.add_port("op2", Input[op2_type])
    s.add_port("res", Output[Auto])
    
    def deduction(io: IOProxy):
        t1, t2, tr = io.op1.type, io.op2.type, io.res.type
        
        if t1.determined and t2.determined:
            io.res.update(t1.base[max(t1.W, t2.W)])
        elif tr.determined and t1.determined and t1.W < tr.W:
            io.op2.update(tr.base[tr.W])
        elif tr.determined and t2.determined and t2.W < tr.W:
            io.op1.update(tr.base[tr.W])
    
    def generation(h: HDLFileModel, io: IOProxy):
        t1, t2, tr = io.op1.type, io.op2.type, io.res.type
        
        if not (t1.belongs(UInt) and t2.belongs(UInt) or t1.belongs(SInt) and t2.belongs(SInt)):
            raise StructureGenerationException(f"Only accept UInt + UInt or SInt + SInt")

        if not tr.W == max(t1.W, t2.W):
            raise StructureGenerationException(f"Result width should be the maximum of the two operands")
        
        if tr.belongs(UInt):
            ag = "std_logic_vector(unsigned(op1) + unsigned(op2))"
        else:
            ag = "std_logic_vector(signed(op1) + signed(op2))"
        
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
    res <= {ag};
end architecture;
"""
        )
    
    s.custom_deduction = deduction
    s.custom_generation = generation
    
    rid = RuntimeId.create()
    s.deduction(rid)
    s.apply_runtime(rid)
    
    if s.is_reusable:
        s.unique_name = f"addition_{op1_type}_{op2_type}"
    
    return s

