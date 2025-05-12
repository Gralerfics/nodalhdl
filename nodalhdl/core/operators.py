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


class OperatorSetupTemplates:
    @staticmethod
    def input_type_args_2i1o(input_name_1: str, input_name_2: str, output_name: str, output_type: SignalType = Auto):
        def _setup(*args):
            assert 1 <= len(args) <= 2 and all([isinstance(item, SignalType) for item in args])
            input_type_1 = args[0]
            input_type_2 = args[1] if len(args) == 2 else input_type_1
            
            s = Structure()
            
            s.add_port(input_name_1, Input[input_type_1])
            s.add_port(input_name_2, Input[input_type_2])
            s.add_port(output_name, Output[output_type])
            
            return s
        
        return _setup
    
    @staticmethod
    def input_type_args_1i1o(input_name: str = "a", output_name: str = "r", output_type: SignalType = Auto):
        def _setup(*args):
            assert len(args) == 1 and isinstance(args[0], SignalType)
            input_type = args[0]
            
            s = Structure()
            
            s.add_port(input_name, Input[input_type])
            s.add_port(output_name, Output[output_type])
            
            return s
        
        return _setup


class OperatorDeductionTemplates:
    @staticmethod
    def wider_as_output_2i1o(input_path_1: str, input_path_2: str, output_path: str):
        def _deduction(s: Structure, io: IOProxy):
            i1, i2, o = io.access(input_path_1), io.access(input_path_2), io.access(output_path)
            
            merged_base = i1.type.base.merges(i2.type.base).merges(o.type.base)
            o.update(merged_base[max(i1.type.W, i2.type.W)] if hasattr(i1.type, "W") and hasattr(i2.type, "W") else merged_base)
            i1.update(merged_base[o.type.W] if hasattr(i2.type, "W") and hasattr(o.type, "W") and i2.type.W < o.type.W else merged_base)
            i2.update(merged_base[o.type.W] if hasattr(i1.type, "W") and hasattr(o.type, "W") and i1.type.W < o.type.W else merged_base)
        
        return _deduction
    
    @staticmethod
    def equal_types(*port_paths):
        def _deduction(s: Structure, io: IOProxy):
            P = [io.access(path) for path in port_paths]
            
            full_type = Auto
            for p in P:
                full_type = full_type.merges(p.type)
            for p in P:
                p.update(full_type)
        
        return _deduction


class ArgsOperatorMeta(type):
    def __getitem__(cls, args):
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        
        unique_name = cls.naming(*args) # should be a valid string and unique across all operators
        if unique_name in operators_pool: # return existed reusable structure (will not be in the pool if not reusable)
            return operators_pool[unique_name]
        
        s: Structure = cls.setup(*args)
        
        s.custom_deduction = cls.deduction
        s.custom_generation = cls.generation
        s.custom_params["_setup_args"] = args
        
        rid = RuntimeId.create()
        s.deduction(rid)
        if s.is_runtime_applicable:
            s.apply_runtime(rid)
        
        if s.is_reusable: # only save reusable structures
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

