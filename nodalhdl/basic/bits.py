from ..core.signal import *
from ..core.structure import Structure, IOProxy
from ..core.pool import UniquelyNamedReusable, OperatorUtils, OperatorSetupTemplates, OperatorDeductionTemplates, UniqueNamingTemplates
from ..core.hdl import HDLFileModel

import hashlib
import textwrap

from typing import List


class BitsAdd(UniquelyNamedReusable):
    """
        2's complement addition.
        
        BitsAdd(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (wider width)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.wider_as_output_2i1o("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= std_logic_vector(unsigned(a) + unsigned(b));
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsSubtract(UniquelyNamedReusable):
    """
        2's complement subtraction.
        
        BitsSubtract(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (wider width)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.wider_as_output_2i1o("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= std_logic_vector(unsigned(a) - unsigned(b));
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsInverse(UniquelyNamedReusable):
    """
        2's complement inverse. (r = ~a + 1)
        
        BitsInverse(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r")
    deduction = OperatorDeductionTemplates.equal_types("a", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= std_logic_vector(-signed(a));
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsEqualTo(UniquelyNamedReusable):
    """
        Same width EQU.
    
        BitsEqualTo(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r", output_type = Bit)
    deduction = OperatorDeductionTemplates.equal_types("a", "b")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out std_logic
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= '1' when a = b else '0';
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsLessThan(UniquelyNamedReusable):
    """
        Same width LE. (P.S. unsigned)

        BitsLessThan(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r", output_type = Bit)
    deduction = OperatorDeductionTemplates.equal_types("a", "b")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out std_logic
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= '1' when unsigned(a) < unsigned(b) else '0';
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsNot(UniquelyNamedReusable):
    """
        Bitwise NOT.

        BitsNot(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r")
    deduction = OperatorDeductionTemplates.equal_types("a", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= not a;
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsAnd(UniquelyNamedReusable):
    """
        Bitwise AND.

        BitsAnd(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.equal_types("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= a and b;
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsReductionAnd(UniquelyNamedReusable):
    """
        Bitwise reduction AND.

        BitsReduceAnd(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r", output_type = Bit)
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    r: out std_logic
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= '1' when (a = (a'range => '1')) else '0';
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsOr(UniquelyNamedReusable):
    """
        Bitwise OR.

        BitsOr(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.equal_types("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    b: in {OperatorUtils.type_decl(io.b.type)};
                    r: out {OperatorUtils.type_decl(io.r.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= a or b;
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BitsReductionOr(UniquelyNamedReusable):
    """
        Bitwise reduction OR.

        BitsReductionOr(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r", output_type = Bit)
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;

            entity {h.entity_name} is
                port (
                    a: in {OperatorUtils.type_decl(io.a.type)};
                    r: out std_logic
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                r <= '1' when (a /= (a'range => '0')) else '0';
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class BinaryMultiplexer(UniquelyNamedReusable):
    """
        Two-way MUX.
    
        BinaryMultiplexer(<value_type (SignalType)>)
        
        Input(s): i0 (value_type), i1 (value_type), sel (Bit)
        Output(s): o
    """
    @staticmethod
    def setup(*args) -> Structure:
        assert len(args) == 1 and isinstance(args[0], SignalType)
        
        value_type = args[0]
        
        s = Structure()
        
        s.add_port("i0", Input[value_type])
        s.add_port("i1", Input[value_type])
        s.add_port("sel", Input[Bit])
        s.add_port("o", Output[value_type])
        
        return s
    
    deduction = OperatorDeductionTemplates.equal_types("i0", "i1", "o")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;

            entity {h.entity_name} is
                port (
                    i0: in {OperatorUtils.type_decl(io.i0.type)};
                    i1: in {OperatorUtils.type_decl(io.i1.type)};
                    s: in std_logic;
                    o: out {OperatorUtils.type_decl(io.o.type)}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
            begin
                o <= i1 when s = '1' else i0;
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values


class CustomVHDLOperator(UniquelyNamedReusable):
    """
        Customized bitwise operations in VHDL.

        CustomVHDLOperator(
            {input_name_0: input_type_0, ...}
            {output_name_0: output_type_0, ...},
            arch_body (str),
            arch_decl (str)
        )
        
        TODO 结构化端口, 直接放个带 IOWrapper 的完善 Bundle 进来, 合适吗? 为保兼容性应保留原方式.
        
        Input(s): <input_name_0> (input_type_0), ...
        Output(s): <output_name_0> (output_type_0), ...
    """
    @staticmethod
    def setup(*args, **kwargs) -> Structure:
        assert \
            len(args) >= 3 and \
            isinstance(args[0], dict) and \
            isinstance(args[1], dict) and \
            isinstance(args[2], str) and \
            (len(args) == 3 or isinstance(args[3], str))
        
        s = Structure()
        
        for name, t in args[0].items():
            s.add_port(name, Input[t])
        
        for name, t in args[1].items():
            s.add_port(name, Output[t])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        args = s.custom_params["_setup_args"]
        input_ports: dict = args[0]
        output_ports: dict = args[1]
        arch_body: str = args[2]
        arch_decl: str = args[3] if len(args) > 3 else None
        
        port_body = ";\n                    ".join(
            [f"{name}: in {OperatorUtils.type_decl(io.access(name).type)}" for name in input_ports.keys()] +
            [f"{name}: out {OperatorUtils.type_decl(io.access(name).type)}" for name in output_ports.keys()]
        )
        
        h.set_raw(".vhd", textwrap.dedent(f"""\
            library IEEE;
            use IEEE.std_logic_1164.all;
            use IEEE.numeric_std.all;
            use work.types.all;

            entity {h.entity_name} is
                port (
                    {port_body}
                );
            end entity;

            architecture Behavioral of {h.entity_name} is
                {textwrap.dedent(arch_decl).strip().replace("\n", "\n                ") if arch_decl else "-- no declarations"}
            begin
                {textwrap.dedent(arch_body).strip().replace("\n", "\n                ")}
            end architecture;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_md5_16


# TODO 重构
class Decomposition(UniquelyNamedReusable):
    """
        Decomposition(<input_type (BundleType)>): all shallow members
        Decomposition(<input_type (BundleType)>, <path_0 (str)>, <path_1 (str)>, ...)

        Input(s): i (BundleType)
        Output(s): o (structural)
    """
    @staticmethod
    def setup(*args, **kwargs) -> Structure:
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
        
        port_str = ";\n".join([f"        o_{path_to_valid_name(path_str)}: out {OperatorUtils.type_decl(eval(f"io.o.{path_str.strip(".")}.type"))}" for path_str in s.custom_params["path_strings"]]) # [NOTICE] dont use eval
        assign_str = "\n".join([f"    o_{path_to_valid_name(path_str)} <= i.{path_str.strip(".")};" for path_str in s.custom_params["path_strings"]])
        
        h.set_raw(".vhd",
f"""\
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use work.types.all;

entity {h.entity_name} is
    port (
        i: in {OperatorUtils.type_decl(input_type)};
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

# TODO 重构
class Composition(UniquelyNamedReusable):
    """
        Composition(<output_type (BundleType)>, <path_0 (str)>, ...)
        
        Input(s): i (structural)
        Output(s): o (BundleType)
    """
    @staticmethod
    def setup(*args, **kwargs) -> Structure:
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
        
        port_str = ";\n".join([f"        i_{path_to_valid_name(path_str)}: in {OperatorUtils.type_decl(eval(f"io.i.{path_str.strip(".")}.type"))}" for path_str in s.custom_params["path_strings"]]) # [NOTICE] dont use eval
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
        o: out {OperatorUtils.type_decl(output_type)};
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


# TODO Slicer、Concatenater、Shifter 以及其他复杂位操作可以直接用 CustomVHDLOperator 实现（大多这样的操作都是拼接性质，放在一个基本算子里会导致无法拆分的大延迟）

