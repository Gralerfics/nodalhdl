from ..core.signal import *
from ..core.structure import *
from ..core.reusable import *
from ..core.hdl import *

import textwrap


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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(unsigned(a) + unsigned(b));
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(unsigned(a) - unsigned(b));
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(-signed(a));
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= '1' when a = b else '0';
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= '1' when unsigned(a) < unsigned(b) else '0';
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= not a;
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= a and b;
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= '1' when (a = (a'range => '1')) else '0';
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= a or b;
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
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= '1' when (a /= (a'range => '0')) else '0';
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
    def setup(value_type: SignalType) -> Structure:
        s = Structure()
        
        s.add_port("i0", Input[value_type])
        s.add_port("i1", Input[value_type])
        s.add_port("sel", Input[Bit])
        s.add_port("o", Output[value_type])
        
        return s
    
    deduction = OperatorDeductionTemplates.equal_types("i0", "i1", "o")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            o <= i1 when s = '1' else i0;
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
    def setup(input_ports: dict, output_ports: dict, arch_body: str, arch_decl: str = None) -> Structure:
        s = Structure()
        
        for name, t in input_ports.items():
            s.add_port(name, Input[t])
        
        for name, t in output_ports.items():
            s.add_port(name, Output[t])
        
        # TODO 有没有办法自动加入? 存在 args 不带 key 的问题
        s.custom_params["arch_body"] = arch_body
        s.custom_params["arch_decl"] = arch_decl
        
        return s
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        arch_body: str = s.custom_params["arch_body"]
        arch_decl: str = s.custom_params["arch_decl"]
        
        h.add_arch_body("vhdl", arch_body)
        if arch_decl is not None:
            h.add_arch_declaration("vhdl", arch_decl)
    
    naming = UniqueNamingTemplates.args_kwargs_md5_16


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

