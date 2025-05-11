from .signal import *
from .structure import Structure, RuntimeId, IOProxy
from .hdl import HDLFileModel

from typing import Dict


operators_pool: Dict[str, Structure] = {} # all operators should be defined in methods in .core.operator (here)


class OperatorUtils:
    @staticmethod
    def type_decl(t: SignalType, hdl: str = "vhdl"):
        if hdl == "vhdl":
            return t.__name__ if t.bases(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"
        elif hdl == "verilog":
            return t.__name__ if t.bases(Bundle) else f"[{t.W - 1}:0]"
        else:
            raise NotImplementedError


class OperatorDeductionTemplates:
    @staticmethod
    def binary_wider_as_output(input_path_1: str, input_path_2: str, output_path: str):
        def _deduction(s: Structure, io: IOProxy):
            i1, i2, o = io.access(input_path_1), io.access(input_path_2), io.access(output_path)
            
            merged_base = i1.type.base.merges(i2.type.base).merges(o.type.base)
            o.update(merged_base[max(i1.type.W, i2.type.W)] if hasattr(i1.type, "W") and hasattr(i2.type, "W") else merged_base)
            i1.update(merged_base[o.type.W] if hasattr(i2.type, "W") and hasattr(o.type, "W") and i2.type.W < o.type.W else merged_base)
            i2.update(merged_base[o.type.W] if hasattr(i1.type, "W") and hasattr(o.type, "W") and i1.type.W < o.type.W else merged_base)
        
        return _deduction


class ArgsOperatorMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        
        s: Structure = cls.setup(*args)
        
        s.custom_deduction = cls.deduction
        s.custom_generation = cls.generation
        s.custom_params["_setup_args"] = args
        
        rid = RuntimeId.create()
        s.deduction(rid)
        if s.is_runtime_applicable:
            s.apply_runtime(rid)
        
        if s.is_reusable:
            unique_name = cls.naming(*args) # should be a valid string and unique across all operators
            if unique_name in operators_pool:
                return operators_pool[unique_name]
            else:
                s.unique_name = unique_name
                operators_pool[unique_name] = s
        
        return s


class ArgsOperator(metaclass = ArgsOperatorMeta):
    @staticmethod
    def setup(*args) -> Structure:
        return Structure()
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy): ...
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy): ...
    
    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{'_'.join(map(str, args))}" # [NOTICE] use valid string

