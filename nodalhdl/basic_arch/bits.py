# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

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
    deduction = OperatorDeductionTemplates.equi_bases_wider_output_2i1o("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(unsigned(a) + unsigned(b));
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSubtract(UniquelyNamedReusable):
    """
        2's complement subtraction.
        
        BitsSubtract(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (wider width)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.equi_bases_wider_output_2i1o("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(unsigned(a) - unsigned(b));
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsUnsignedMultiply(UniquelyNamedReusable):
    @staticmethod
    def setup(t1: SignalType, t2: SignalType):
        assert t1.belong(Bits) and t2.belong(Bits) and t1.is_determined and t2.is_determined
        
        s = Structure()
        a = s.add_port("a", Input[t1])
        b = s.add_port("b", Input[t2])
        r = s.add_port("r", Output[Bits[t1.W + t2.W]])
        
        lW, sW = max(t1.W, t2.W), min(t1.W, t2.W)
        lP, sP = (a, b) if t1.W > t2.W else (b, a)
        
        gen = s.add_substructure("gen_addends", CustomVHDLOperator(
            {"long": Bits[lW], "short": Bits[sW]},
            {f"addend_{idx}": Bits[lW + idx + 1] for idx in range(sW)}, # plus 1 to avoid overflow
            f"long_shifted <= '0' & long & (1 to {sW - 1} => '0');\n" +
                "\n".join([f"addend_{idx} <= long_shifted({lW + sW - 1} downto {sW - idx - 1}) when short({idx}) = '1' else (others => '0');" for idx in range(sW)]),
            f"signal long_shifted: std_logic_vector({lW + sW - 1} downto 0);",
            _unique_name = BitsUnsignedMultiply.naming(t1, t2) + "_AddendsGenerator"
        ))
        s.connect(lP, gen.IO.long)
        s.connect(sP, gen.IO.short)
        
        adder_idx = 0
        last_P = []
        P = [gen.IO.access(f"addend_{idx}") for idx in range(sW)]
        while len(P) > 1:
            last_P, P = P, []
            
            for i in range(1, len(last_P), 2): # add adjacent ports
                new_adder = s.add_substructure(
                    f"adder_{adder_idx}",
                    BitsAdd(last_P[i - 1].origin_signal_type.io_clear(), last_P[i].origin_signal_type.io_clear())
                )
                s.connect(last_P[i - 1], new_adder.IO.a)
                s.connect(last_P[i], new_adder.IO.b)
                P.append(new_adder.IO.r)
                
                adder_idx += 1
            
            if len(last_P) % 2 == 1: # fallout port
                P.append(last_P[-1])
        s.connect(P[0], r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSignedMultiply(UniquelyNamedReusable):
    @staticmethod
    def setup(t1: SignalType, t2: SignalType):
        assert t1.belong(Bits) and t2.belong(Bits) and t1.is_determined and t2.is_determined
        
        s = Structure()
        a = s.add_port("a", Input[t1])
        b = s.add_port("b", Input[t2])
        r = s.add_port("r", Output[Bits[t1.W + t2.W]])
        
        lW, sW = max(t1.W, t2.W), min(t1.W, t2.W)
        lP, sP = (a, b) if t1.W > t2.W else (b, a)
        
        gen = s.add_substructure("gen_addends", CustomVHDLOperator(
            {"long": Bits[lW], "short": Bits[sW]},
            {
                **{f"addend_{idx}": SInt[lW + sW] for idx in range(sW - 1)},
                "subend": SInt[lW + sW]
            },
            f"long_shifted <= long & (1 to {sW - 1} => '0');\n" +
                f"long_sign <= long(long'high);\n" +
                "\n".join([
                    (f"addend_{idx}" if idx < sW - 1 else "subend") + 
                    f" <= (1 to {sW - idx} => long_sign) & long_shifted({lW + sW - 2} downto {sW - idx - 1}) when short({idx}) = '1' else (others => '0');"
                for idx in range(sW)]),
            f"signal long_shifted: std_logic_vector({lW + sW - 2} downto 0);\n" +
                f"signal long_sign: std_logic;",
            _unique_name = BitsUnsignedMultiply.naming(t1, t2) + "_AddendsGenerator"
        ))
        s.connect(lP, gen.IO.long)
        s.connect(sP, gen.IO.short)
        
        adder_idx = 0
        last_P = []
        P = [gen.IO.access(f"addend_{idx}") for idx in range(sW - 1)]
        while len(P) > 1:
            last_P, P = P, []
            
            for i in range(1, len(last_P), 2): # add adjacent ports
                new_adder = s.add_substructure(
                    f"adder_{adder_idx}",
                    BitsAdd(last_P[i - 1].origin_signal_type.io_clear(), last_P[i].origin_signal_type.io_clear())
                )
                s.connect(last_P[i - 1], new_adder.IO.a)
                s.connect(last_P[i], new_adder.IO.b)
                P.append(new_adder.IO.r)
                
                adder_idx += 1
            
            if len(last_P) % 2 == 1: # fallout port
                P.append(last_P[-1])
        
        subtractor = s.add_substructure(
            f"subtractor",
            BitsSubtract(last_P[i - 1].origin_signal_type.io_clear(), last_P[i].origin_signal_type.io_clear())
        )
        s.connect(P[0], subtractor.IO.a)
        s.connect(gen.IO.access("subend"), subtractor.IO.b)
        s.connect(subtractor.IO.r, r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSignedDivide(UniquelyNamedReusable):
    @staticmethod
    def setup(t1: SignalType, t2: SignalType):
        assert t1.belong(Bits) and t2.belong(Bits) and t1.is_determined and t2.is_determined
        
        s = Structure()
        a = s.add_port("a", Input[t1])
        b = s.add_port("b", Input[t2])
        q = s.add_port("q", Output[t1])
        r = s.add_port("r", Output[t2]) # sign(rem) = sign(a), 0 <= |rem| < |b|
        
        t_ea = Bits[t2.W + 1] # ea means E & A, storing the (partial) remainder
        
        gen = s.add_substructure("gen_wires", CustomVHDLOperator(
            {"a": t1, "b": t2},
            {
                **{f"a_{idx}": Bit for idx in range(t1.W)},
                "ea_init": t_ea,
                "b_ext": t_ea
                # "b_sign": Bit
            },
            "\n".join([f"a_{idx}(0) <= a({idx});" for idx in range(t1.W)]) + "\n" +
                "ea_init <= (others => a(a'high));\n" +
                "b_ext <= b(b'high) & b;\n",
                # "b_sign <= b(b'high);",
            _unique_name = BitsSignedDivide.naming(t1, t2) + "_WiresGenerator"
        ))
        
        DivisionCell = CustomVHDLOperator(
            {"ea": t_ea, "a_i": Bit, "b_ext": t_ea},
            {"ea_new": t_ea, "q_i": Bit},
            textwrap.dedent("""
                ea_shift <= ea(ea'high - 1 downto 0) & a_i;
                
                process (ea_shift, b_ext)
                begin
                    if (ea_shift(ea_shift'high) xor b_ext(b_ext'high)) = '1' then
                        q_i <= "0";
                        ea_new <= std_logic_vector(signed(ea_shift) + signed(b_ext));
                    else
                        q_i <= "1";
                        ea_new <= std_logic_vector(signed(ea_shift) - signed(b_ext));
                    end if;
                end process;
            """),
            f"signal ea_shift: std_logic_vector({t2.W} downto 0);",
            _unique_name = BitsSignedDivide.naming(t1, t2) + "_DivisionCell"
        )
        cells: List[StructureProxy] = []
        for idx in range(t1.W):
            cells.append(s.add_substructure(f"div_cell_{idx}", DivisionCell))

        corr = s.add_substructure("corrector", CustomVHDLOperator(
            {
                "ea": t_ea,
                **{f"q_{idx}": Bit for idx in range(t1.W)},
                "a_sign": Bit,
                "b_ext": t_ea
            },
            {"q": t1, "r": t2},
            textwrap.dedent(f"""
                q_concat <= not {" & ".join([f"q_{idx}" for idx in range(t1.W - 1, -1, -1)])} & '1';
                
                process (ea, q_concat, a_sign, b_ext)
                begin
                    if ((ea(ea'high) xor a_sign(0)) = '1' and unsigned(ea) /= to_unsigned(0, {t_ea.W})) or (signed(ea) = signed(b_ext)) or (signed(ea) = -signed(b_ext)) then
                        if ea(ea'high) = b_ext(b_ext'high) then
                            q_corrected <= std_logic_vector(signed(q_concat) + to_signed(1, {t1.W + 1}));
                            ea_corrected <= std_logic_vector(signed(ea) - signed(b_ext));
                        else
                            q_corrected <= std_logic_vector(signed(q_concat) - to_signed(1, {t1.W + 1}));
                            ea_corrected <= std_logic_vector(signed(ea) + signed(b_ext));
                        end if;
                    else
                        q_corrected <= q_concat;
                        ea_corrected <= ea;
                    end if;
                end process;
                
                q <= q_corrected(q_corrected'high - 1 downto 0);
                r <= ea_corrected(ea_corrected'high - 1 downto 0);
            """),
            f"signal q_concat, q_corrected: std_logic_vector({t1.W} downto 0);\n" +
                f"signal ea_corrected: std_logic_vector({t2.W} downto 0);",
            _unique_name = BitsSignedDivide.naming(t1, t2) + "_Corrector"
        ))
        
        # a, b
        s.connect(a, gen.IO.a)
        s.connect(b, gen.IO.b)
        
        # a_i, a_sign
        for idx in range(t1.W):
            s.connect(gen.IO.access(f"a_{idx}"), cells[idx].IO.a_i)
        s.connect(gen.IO.access(f"a_{t1.W - 1}"), corr.IO.a_sign)
        
        # ea
        s.connect(gen.IO.ea_init, cells[t1.W - 1].IO.ea)
        for idx in range(t1.W - 1):
            s.connect(cells[idx + 1].IO.ea_new, cells[idx].IO.ea)
        s.connect(cells[0].IO.ea_new, corr.IO.ea)
        
        # b_ext
        for idx in range(t1.W):
            s.connect(gen.IO.b_ext, cells[idx].IO.b_ext)
        s.connect(gen.IO.b_ext, corr.IO.b_ext)
        
        # q_i
        for idx in range(t1.W):
            s.connect(cells[idx].IO.q_i, corr.IO.access(f"q_{idx}"))
        
        # q, r
        s.connect(corr.IO.q, q)
        s.connect(corr.IO.r, r)
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSignedInverse(UniquelyNamedReusable):
    """
        2's complement inverse. (r = ~a + 1)
        
        BitsSignedInverse(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r")
    deduction = OperatorDeductionTemplates.equi_types("a", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(-signed(a));
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSignedAbsolute(UniquelyNamedReusable):
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r")
    deduction = OperatorDeductionTemplates.equi_types("a", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= std_logic_vector(abs(signed(a)));
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsEqualTo(UniquelyNamedReusable):
    """
        Same width EQU.
    
        BitsEqualTo(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r", output_type = Bit)
    deduction = OperatorDeductionTemplates.equi_types("a", "b")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= "1" when a = b else "0";
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsUnsignedLessThan(UniquelyNamedReusable):
    """
        Same width LE. (unsigned)

        BitsUnsignedLessThan(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r", output_type = Bit)
    deduction = OperatorDeductionTemplates.equi_types("a", "b")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= "1" when unsigned(a) < unsigned(b) else "0";
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsSignedLessThan(UniquelyNamedReusable):
    """
        Same width LE. (signed)

        BitsSignedLessThan(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (Bit)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r", output_type = Bit)
    deduction = OperatorDeductionTemplates.equi_types("a", "b")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= "1" when signed(a) < signed(b) else "0";
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsNot(UniquelyNamedReusable):
    """
        Bitwise NOT.

        BitsNot(<a_type (SignalType)>)
        
        Input(s): a (a_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_1i1o("a", "r")
    deduction = OperatorDeductionTemplates.equi_types("a", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= not a;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsAnd(UniquelyNamedReusable):
    """
        Bitwise AND.

        BitsAnd(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.equi_types("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= a and b;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


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
            r <= "1" when (a = (a'range => '1')) else "0";
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsOr(UniquelyNamedReusable):
    """
        Bitwise OR.

        BitsOr(<a_type (SignalType)>, <b_type (SignalType)>)
        
        Input(s): a (a_type), b (b_type)
        Output(s): r (same type)
    """
    setup = OperatorSetupTemplates.input_type_args_2i1o("a", "b", "r")
    deduction = OperatorDeductionTemplates.equi_types("a", "b", "r")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            r <= a or b;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


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
            r <= "1" when (a /= (a'range => '0')) else "0";
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


class BitsLeadingOneDetect(UniquelyNamedReusable):
    @staticmethod
    def setup(layer_num: int):
        s = Structure()
        
        # TODO
        
        return s
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


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
    
    deduction = OperatorDeductionTemplates.equi_types("i0", "i1", "o")
    
    @staticmethod
    def generation(s: Structure, h: HDLFileModel, io: IOProxy):
        h.add_arch_body("vhdl", textwrap.dedent(f"""\
            o <= i1 when sel = "1" else i0;
        """))
    
    naming = UniqueNamingTemplates.args_kwargs_all_values()


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
    
    naming = UniqueNamingTemplates.args_kwargs_sha256_16()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

