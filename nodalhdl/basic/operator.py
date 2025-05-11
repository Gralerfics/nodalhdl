from ..core.signal import *
from ..core.structure import Structure, RuntimeId, IOProxy
from ..core.hdl import HDLFileModel

import hashlib

from typing import Dict, List


"""
    TODO check the `NotImplementedError`s.
"""


declaration_from_type = lambda t: t.__name__ if t.bases(Bundle) else f"std_logic_vector({t.W - 1} downto 0)"


class ArgsOperatorMeta(type):
    pool: Dict[str, Structure] = {}
    
    def __getitem__(cls, args):
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = [args]
        
        s = cls.setup(*args)
        
        s.custom_deduction = cls.deduction
        s.custom_generation = cls.generation
        s.custom_params["_setup_args"] = args
        
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


class WiderOutputBinaryOperator(ArgsOperator):
    @staticmethod
    def setup(*args) -> Structure:
        op1_type, op2_type = args[0], args[1]
        
        s = Structure()
        
        s.add_port("op1", Input[op1_type])
        s.add_port("op2", Input[op2_type])
        s.add_port("res", Output[Auto])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if op1_type.determined and op2_type.determined:
            io.res.update(op1_type.base[max(op1_type.W, op2_type.W)])
        elif res_type.determined and op1_type.determined and op1_type.W < res_type.W:
            io.op2.update(res_type.base[res_type.W])
        elif res_type.determined and op2_type.determined and op2_type.W < res_type.W:
            io.op1.update(res_type.base[res_type.W])


class EqualBinaryOperator(ArgsOperator):
    @staticmethod
    def setup(*args) -> Structure:
        op1_type, op2_type = args[0], args[1]
        
        s = Structure()
        
        s.add_port("op1", Input[op1_type])
        s.add_port("op2", Input[op2_type])
        s.add_port("res", Output[Auto])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        io.res.update(io.op1.type)
        io.res.update(io.op2.type)
        io.op1.update(io.res.type)
        io.op2.update(io.res.type)


class Adder(WiderOutputBinaryOperator):
    """
        Adder[<op1_type (SignalType)>, <op2_type (SignalType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (the wider one)
    """
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if op1_type.bases(UInt) and op2_type.bases(UInt):
            ts = "unsigned"
        elif op1_type.bases(SInt) and op2_type.bases(SInt):
            ts = "signed"
        elif op1_type.bases(UFixedPoint) and op2_type.bases(UFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            ts = "unsigned"
        elif op1_type.bases(SFixedPoint) and op2_type.bases(SFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            ts = "signed"
        else:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: out {declaration_from_type(res_type)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector({ts}(op1) + {ts}(op2));
end architecture;
"""
        )


class Subtracter(WiderOutputBinaryOperator):
    """
        Subtracter[<op1_type (SignalType)>, <op2_type (SignalType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (the wider one)
    """
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if op1_type.bases(UInt) and op2_type.bases(UInt):
            ts = "unsigned"
        elif op1_type.bases(SInt) and op2_type.bases(SInt):
            ts = "signed"
        elif op1_type.bases(UFixedPoint) and op2_type.bases(UFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            ts = "unsigned"
        elif op1_type.bases(SFixedPoint) and op2_type.bases(SFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            ts = "signed"
        else:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: {declaration_from_type(res_type)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector({ts}(op1) - {ts}(op2));
end architecture;
"""
        )


class Inverse(ArgsOperator):
    """
        Inverse[<op_type (SignalType)>]
        
        Input(s): op (input_type)
        Output(s): res (input_type)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op_type = args[0]
        
        s = Structure()
        
        s.add_port("op", Input[op_type])
        s.add_port("res", Output[op_type])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        io.res.update(io.op.type)
        io.op.update(io.res.type)
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op_type = io.op.type
        type_declaration = declaration_from_type(op_type)
        
        if not op_type.bases(SInt) or not op_type.bases(SFixedPoint):
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op: in {type_declaration};
        res: out {type_declaration}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= std_logic_vector(-signed(op));
end architecture;
"""
        )


class EqualTo(ArgsOperator):
    """
        EqualTo[<op1_type (SignalType)>, <op2_type (SignalType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (Bit)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op1_type, op2_type = args[0], args[1]
        
        s = Structure()
        
        s.add_port("op1", Input[op1_type])
        s.add_port("op2", Input[op2_type])
        s.add_port("res", Output[Bit])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type = io.op1.type, io.op2.type
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: out std_logic
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= '1' when op1 = op2 else '0';
end architecture;
"""
        )


class LessThan(ArgsOperator):
    """
        LessThan[<op1_type (SignalType)>, <op2_type (SignalType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (Bit)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op1_type, op2_type = args[0], args[1]
        
        s = Structure()
        
        s.add_port("op1", Input[op1_type])
        s.add_port("op2", Input[op2_type])
        s.add_port("res", Output[Bit])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type = io.op1.type, io.op2.type
        
        if op1_type.bases(UInt) and op2_type.bases(UInt):
            cond_str = "unsigned(op1) < unsigned(op2)"
        elif op1_type.bases(SInt) and op2_type.bases(SInt):
            cond_str = "signed(op1) < signed(op2)"
        elif op1_type.bases(UFixedPoint) and op2_type.bases(UFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            cond_str = "unsigned(op1) < unsigned(op2)"
        elif op1_type.bases(SFixedPoint) and op2_type.bases(SFixedPoint) and op1_type.W_int == op2_type.W_int and op1_type.W_frac == op2_type.W_frac:
            cond_str = "signed(op1) < signed(op2)"
        else:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: out std_logic
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= '1' when {cond_str} else '0';
end architecture;
"""
        )


class Not(ArgsOperator):
    """
        Not[<op_type (BitsType)>]
        
        Input(s): op (op_type)
        Output(s): res (op_type)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op_type = args[0]
        
        s = Structure()
        
        s.add_port("op", Input[op_type])
        s.add_port("res", Output[op_type])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        io.res.update(io.op.type)
        io.op.update(io.res.type)
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op_type = io.op.type
        type_declaration = declaration_from_type(op_type)
        
        if op_type.base != Bits:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op: in {type_declaration};
        res: out {type_declaration}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= not op;
end architecture;
"""
        )


class And(EqualBinaryOperator):
    """
        And[<op1_type (BitsType)>, <op2_type (BitsType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (the wider one)
    """
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if op1_type.base != Bits or op2_type.base != Bits:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: out {declaration_from_type(res_type)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= op1 and op2;
end architecture;
"""
        )


class ReduceAnd(ArgsOperator):
    """
        ReduceAnd[<op_type (BitsType)>]
        
        Input(s): op (op_type)
        Output(s): res (Bit)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op_type = args[0]
        
        s = Structure()
        
        s.add_port("op", Input[op_type])
        s.add_port("res", Output[Bit])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op_type = io.op.type
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op: in {declaration_from_type(op_type)};
        res: out std_logic
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= '1' when (op = (op'range => '1')) else '0';
end architecture;
"""
        )


class Or(EqualBinaryOperator):
    """
        Or[<op1_type (BitsType)>, <op2_type (BitsType)>]
        
        Input(s): op1 (op1_type), op2 (op2_type)
        Output(s): res (the wider one)
    """
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op1_type, op2_type, res_type = io.op1.type, io.op2.type, io.res.type
        
        if op1_type.base != Bits or op2_type.base != Bits:
            raise NotImplementedError
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op1: in {declaration_from_type(op1_type)};
        op2: in {declaration_from_type(op2_type)};
        res: out {declaration_from_type(res_type)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= op1 or op2;
end architecture;
"""
        )


class ReduceOr(ArgsOperator):
    """
        ReduceOr[<op_type (BitsType)>]
        
        Input(s): op (op_type)
        Output(s): res (Bit)
    """
    @staticmethod
    def setup(*args) -> Structure:
        op_type = args[0]
        
        s = Structure()
        
        s.add_port("op", Input[op_type])
        s.add_port("res", Output[Bit])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        op_type = io.op.type
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        op: in {declaration_from_type(op_type)};
        res: out std_logic
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    res <= '1' when (op /= (op'range => '0')) else '0';
end architecture;
"""
        )


class Multiplexer(ArgsOperator):
    """
        Multiplexer[<value_type (SignalType)>]: two-way MUX
        
        Input(s): i0 (value_type), i1 (value_type), s (Bit)
        Output(s): o
    """
    @staticmethod
    def setup(*args) -> Structure:
        value_type = args[0]
        
        s = Structure()
        
        s.add_port("i0", Input[value_type])
        s.add_port("i1", Input[value_type])
        s.add_port("s", Input[Bit])
        s.add_port("o", Output[value_type])
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        io.o.update(io.i0.type)
        io.o.update(io.i1.type)
        io.i0.update(io.o.type)
        io.i1.update(io.o.type)
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        value_type = io.i0.type
        type_declaration = declaration_from_type(value_type)
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;

entity {h.entity_name} is
    port (
        i0: in {type_declaration};
        i1: in {type_declaration};
        s: in std_logic;
        o: out {type_declaration}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    o <= i1 when s = '1' else i0;
end architecture;
"""
        )


class Decomposition(ArgsOperator):
    """
        Decomposition[<input_type (BundleType)>]: all shallow members
        Decomposition[<input_type (BundleType)>, <path_0 (str)>, <path_1 (str)>, ...]

        Input(s): i (BundleType)
        Output(s): o (structural)
    """
    @staticmethod
    def setup(*args) -> Structure:
        assert len(args) - 1 >= 0
        
        # arguments
        input_type: BundleType = args[0].clear_io()
        path_strings = args[1:] if len(args) > 1 else list(input_type._bundle_types.keys())
        
        # add Output wrappers
        output_type = input_type
        
        def _add_output(t: SignalType, path: List[str]):
            if len(path) == 0:
                return Output[t]
            elif t.bases(Bundle):
                return Bundle[{k: (v if k != path[0] else _add_output(v, path[1:])) for k, v in t._bundle_types.items()}]
            else:
                raise Exception("Invalid path")
        
        for path_str in path_strings:
            output_type = _add_output(output_type, path_str.strip(".").split("."))
        
        # remove imperfect componets
        def _remove_non_wrapped(t: SignalType):
            return Bundle[{k: (v if v.perfectly_io_wrapped else _remove_non_wrapped(v)) for k, v in t._bundle_types.items() if v.io_wrapper_included}]
        
        output_type = _remove_non_wrapped(output_type)
        
        # build structure
        s = Structure()
        
        s.add_port("i", Input[input_type])
        s.add_port(f"o", output_type)
        
        s.custom_params["path_strings"] = path_strings
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        input_type = io.i.type
        
        path_to_valid_name = lambda path_str: path_str.strip(".").replace(".", "_")
        
        port_str = ";\n".join([f"        o_{path_to_valid_name(path_str)}: out {declaration_from_type(eval(f"io.o.{path_str.strip(".")}.type"))}" for path_str in s.custom_params["path_strings"]]) # [NOTICE] dont use eval
        assign_str = "\n".join([f"    o_{path_to_valid_name(path_str)} <= i.{path_str.strip(".")};" for path_str in s.custom_params["path_strings"]])
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
        i: in {declaration_from_type(input_type)};
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
        if len(args) == 1:
            return f"{cls.__name__}_{args[0].__name__[7:15]}"
        else:
            return f"{cls.__name__}_{args[0].__name__[7:15]}_{"_".join([path_str.strip(".").replace(".", "_") for path_str in args[1:]])}"


class Composition(ArgsOperator):
    """
        Composition[<output_type (BundleType)>, <path_0 (str)>, ...]
        
        Input(s): i (structural)
        Output(s): o (BundleType)
    """
    @staticmethod
    def setup(*args) -> Structure:
        assert len(args) - 1 >= 0
        
        # arguments
        output_type: BundleType = args[0].clear_io()
        path_strings = args[1:] if len(args) > 1 else list(input_type._bundle_types.keys())
        
        # add Input wrappers
        input_type = output_type
        
        def _add_input(t: SignalType, path: List[str]):
            if len(path) == 0:
                return Input[t]
            elif t.bases(Bundle):
                return Bundle[{k: (v if k != path[0] else _add_input(v, path[1:])) for k, v in t._bundle_types.items()}]
            else:
                raise Exception("Invalid path")
        
        for path_str in path_strings:
            input_type = _add_input(input_type, path_str.strip(".").split("."))
        
        selectively_wrapped_input_type = input_type
        
        # remove imperfect componets
        def _remove_non_wrapped(t: SignalType):
            return Bundle[{k: (v if v.perfectly_io_wrapped else _remove_non_wrapped(v)) for k, v in t._bundle_types.items() if v.io_wrapper_included}]
        
        input_type = _remove_non_wrapped(input_type)
        
        # build structure
        s = Structure()
        
        s.add_port("i", input_type)
        s.add_port("o", Output[output_type])
        
        s.custom_params["path_strings"] = path_strings
        s.custom_params["selectively_wrapped_input_type"] = selectively_wrapped_input_type
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        output_type = io.o.type
        selectively_wrapped_input_type = s.custom_params["selectively_wrapped_input_type"]
        
        path_to_valid_name = lambda path_str: path_str.strip(".").replace(".", "_")
        
        port_str = ";\n".join([f"        i_{path_to_valid_name(path_str)}: in {declaration_from_type(eval(f"io.i.{path_str.strip(".")}.type"))}" for path_str in s.custom_params["path_strings"]]) # [NOTICE] dont use eval
        assign_str = "\n".join([f"    o.{path_str.strip(".")} <= i_{path_to_valid_name(path_str)};" for path_str in s.custom_params["path_strings"]])
        
        def _assign_zeros(t: SignalType, path: List[str] = []):
            res = ""
            if not t.perfectly_io_wrapped:
                if t.bases(Bundle):
                    res += "".join([_assign_zeros(v, path + [k]) for k, v in t._bundle_types.items()])
                else:
                    res += f"\n    o.{".".join(path)} <= (others => \'0\');"
            return res
        
        assign_str += _assign_zeros(selectively_wrapped_input_type)
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use work.types.all;

entity {h.entity_name} is
    port (
        o: out {declaration_from_type(output_type)};
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
        if len(args) == 1:
            return f"{cls.__name__}_{args[0].__name__[7:15]}"
        else:
            return f"{cls.__name__}_{args[0].__name__[7:15]}_{"_".join([path_str.strip(".").replace(".", "_") for path_str in args[1:]])}"


class Constant(ArgsOperator):
    """
        Constant[constant_0 (Signal), constant_1 (Signal), ...]
        
        Output(s): c0 (type(constant_0)), c1 (type(constant_1)), ...
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
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        constants = s.custom_params["constants"]
        
        port_str = ";\n".join([f"        c{idx}: out {declaration_from_type(type(c))}" for idx, c in enumerate(constants)])
        
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


class Concatenater(ArgsOperator):
    """
        Concatenater[N (int)]: N-inputs, Auto type
        Concatenater[type_0 (SignalType), type_1 (SignalType), ...]: TODO
        
        Input(s): i0, i1, ...
        Output(s): o (Bits[...])
    """
    @staticmethod
    def setup(*args) -> Structure:
        s = Structure()
        
        if isinstance(args[0], int):
            for idx in range(args[0]):
                s.add_port(f"i{idx}", Input[Auto])
            s.add_port("o", Output[Auto])
            
            s.custom_params["N"] = args[0]
        else:
            raise NotImplementedError
        
        return s
    
    @staticmethod
    def deduction(s: Structure, io: IOProxy):
        N = s.custom_params["N"]
        input_types = [io._proxy[f"i{idx}"].type for idx in range(N)]
        
        if all([t.determined for t in input_types]):
            io.o.update(Bits[sum([t.W for t in input_types])])
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        N = s.custom_params["N"]
        input_types = [io._proxy[f"i{idx}"].type for idx in range(N)]
        output_type = io.o.type
        
        if N is not None:
            port_str = "\n".join([f"        i{idx}: in {declaration_from_type(t)};" for idx, t in enumerate(input_types)])
            assign_str = "    o <= " + " & ".join([f"i{idx}" for idx in range(N)]) + ";"
        else:
            raise NotImplementedError

        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
{port_str}
        o: out {declaration_from_type(output_type)}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
{assign_str}
end architecture;
"""
        )

    # @classmethod
    # def naming(cls, *args): # TODO 只给出 N 的情况非定态


class BitsOperator(ArgsOperator):
    """
        Concatenater[(Wi0, Wi1, ...), (Wo0, Wo1, ...), "VHDL", content (str)]
        
        Input(s): i0, i1, ...
        Output(s): o0, o1, ...
    """
    @staticmethod
    def setup(*args) -> Structure:
        i_widths = args[0]
        o_widths = args[1]
        hdl_type = args[2]
        hdl_content = args[3]
        
        s = Structure()
        
        for idx, w in enumerate(i_widths):
            s.add_port(f"i{idx}", Input[Bits[w]])
        
        for idx, w in enumerate(o_widths):
            s.add_port(f"o{idx}", Output[Bits[w]])
        
        s.custom_params["i_widths"] = i_widths
        s.custom_params["o_widths"] = o_widths
        s.custom_params["hdl_type"] = hdl_type
        s.custom_params["hdl_content"] = hdl_content
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        i_widths = s.custom_params["i_widths"]
        o_widths = s.custom_params["o_widths"]
        hdl_type = s.custom_params["hdl_type"]
        hdl_content: str = s.custom_params["hdl_content"]
        
        port_str = "\n".join(
            [f"        i{idx}: in {declaration_from_type(Bits[w])};" for idx, w in enumerate(i_widths)] +
            [f"        o{idx}: out {declaration_from_type(Bits[w])};" for idx, w in enumerate(o_widths)]
        )
        
        if hdl_type == "VHDL":
            h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
{port_str[:-1]}
    );
end entity;

architecture Behavioral of {h.entity_name} is
begin
    {hdl_content.replace("\n", "\n    ")}
end architecture;
"""
            )
        else:
            raise NotImplementedError

    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{'_'.join([hashlib.md5(str(arg).encode('utf-8')).hexdigest()[:8] for arg in args])}" # [NOTICE] use valid string


# class Slicer(ArgsOperator):
#     """
#         Slicer[input_type (SignalType), wire_1 (SignalType), ...]
        
#         Output(s): c0 (type(constant_0)), c1 (type(constant_1)), ...
#     """
#     pass


# class Shifter(ArgsOperator):
#     """
#         TODO 暂时只考虑 UInt, SInt 和 Bits
#     """
#     pass

