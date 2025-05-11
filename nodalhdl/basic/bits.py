from ..core.signal import *
from ..core.structure import Structure, IOProxy
from ..core.operators import ArgsOperator, OperatorUtils, OperatorSetupTemplates, OperatorDeductionTemplates
from ..core.hdl import HDLFileModel

import hashlib
import textwrap

from typing import Dict, List


"""
    check the `NotImplementedError`s.
"""


class BitsAdd(ArgsOperator):
    """
        2's complement addition.
        
        BitsAddition[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsSubtract(ArgsOperator):
    """
        2's complement subtraction.
        
        BitsSubtract[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsInverse(ArgsOperator):
    """
        2's complement inverse. (r = ~a + 1)
        
        BitsInverse[<a_type (SignalType)>]
        
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


class BitsEqualTo(ArgsOperator):
    """
        Same width EQU.
    
        BitsEqualTo[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsLessThan(ArgsOperator):
    """
        Same width LE. (P.S. unsigned)

        BitsLessThan[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsNot(ArgsOperator):
    """
        Bitwise NOT.

        BitsNot[<a_type (SignalType)>]
        
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


class BitsAnd(ArgsOperator):
    """
        Bitwise AND.

        BitsAnd[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsReductionAnd(ArgsOperator):
    """
        Bitwise reduction AND.

        BitsReduceAnd[<a_type (SignalType)>]
        
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


class BitsOr(ArgsOperator):
    """
        Bitwise OR.

        BitsOr[<a_type (SignalType)>, <b_type (SignalType)>]
        
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


class BitsReductionOr(ArgsOperator):
    """
        Bitwise reduction OR.

        BitsReductionOr[<a_type (SignalType)>]
        
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
        type_declaration = OperatorUtils.type_decl(value_type)
        
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
        
        port_str = ";\n".join([f"        c{idx}: out {OperatorUtils.type_decl(type(c))}" for idx, c in enumerate(constants)])
        
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
            port_str = "\n".join([f"        i{idx}: in {OperatorUtils.type_decl(t)};" for idx, t in enumerate(input_types)])
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
        o: out {OperatorUtils.type_decl(output_type)}
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


class BitsVHDLOperator(ArgsOperator):
    """
        Customized bitwise operations in VHDL.

        BitsVHDLOperator[(input_type_0, input_type_1, ...), (output_type_0, output_type_1, ...), arch_body (str), arch_decl (str)]
        
        Input(s): i0 (input_type_0), i1 (input_type_1), ...
        Output(s): o0 (output_type_0), o1 (output_type_1), ...
    """
    @staticmethod
    def setup(*args) -> Structure:
        assert \
            len(args) >= 3 and \
            (isinstance(args[0], tuple) or isinstance(args[0], list) or isinstance(args[0], SignalType)) and \
            (isinstance(args[1], tuple) or isinstance(args[1], list) or isinstance(args[1], SignalType)) and \
            isinstance(args[2], str) and \
            (len(args) == 3 or isinstance(args[3], str))
        
        input_types = [args[0]] if isinstance(args[0], SignalType) else args[0]
        output_types = [args[1]] if isinstance(args[1], SignalType) else args[1]
        
        s = Structure()
        
        for idx, t in enumerate(input_types):
            s.add_port(f"i{idx}", Input[t])
        
        for idx, t in enumerate(output_types):
            s.add_port(f"o{idx}", Output[t])
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        args = s.custom_params["_setup_args"]
        inputs_num = 1 if isinstance(args[0], SignalType) else len(args[0])
        outputs_num = 1 if isinstance(args[1], SignalType) else len(args[1])
        arch_body: str = args[2]
        arch_decl: str = args[3] if len(args) > 3 else None
        
        port_body = ";\n                    ".join(
            [f"i{idx}: in {OperatorUtils.type_decl(io.access(f"i{idx}").type)}" for idx in range(inputs_num)] +
            [f"o{idx}: out {OperatorUtils.type_decl(io.access(f"o{idx}").type)}" for idx in range(outputs_num)]
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

    @classmethod
    def naming(cls, *args):
        return f"{cls.__name__}_{hashlib.md5(str(args).encode('utf-8')).hexdigest()[:16]}"


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

