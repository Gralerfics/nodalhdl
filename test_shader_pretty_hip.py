from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.basic.arith import *

from nodalhdl.core.hdl import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


T = SFixedPoint[16, 12] # 目前要求 W_int <= 45 且 8 <= W_frac <= 20


def Shader() -> Structure:
    s = Structure()

    def TArithmeticShifter(i: Node, n: int): # n > 0: move left, else right
        u = s.add_substructure(f"arith_shifter", CustomVHDLOperator(
            {"i": T},
            {"o": T},
            f"o <= std_logic_vector({"shift_left" if n >= 0 else "shift_right"}(signed(i), {abs(n)}));",
            _unique_name = f"ArithShifter_{str(n).replace("-", "NEG")}_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def TFract(i: Node):
        u = s.add_substructure(f"fract", CustomVHDLOperator(
            {"i": T},
            {"o": T},
            f"o <= (o'high downto {T.W_frac} => '0') & i({T.W_frac - 1} downto 0);",
            _unique_name = f"Fract_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o

    def TAddition(a: Node, b: Node):
        u = s.add_substructure(f"addition", Add(T, T))
        s.connect(a, u.IO.a)
        s.connect(b, u.IO.b)
        return u.IO.r
    
    def TSubtraction(a: Node, b: Node):
        u = s.add_substructure(f"subtraction", Subtract(T, T))
        s.connect(a, u.IO.a)
        s.connect(b, u.IO.b)
        return u.IO.r
    
    def TMultiplication(a: Node, b: Node):
        u = s.add_substructure(f"multiplication", Multiply(T, T))
        s.connect(a, u.IO.a)
        s.connect(b, u.IO.b)
        return u.IO.r
    
    def TMin(a: Node, b: Node):
        u = s.add_substructure(f"min", CustomVHDLOperator(
            {"a": T, "b": T},
            {"o": T},
            f"o <= a when signed(a) < signed(b) else b;",
            _unique_name = f"Min_{T}_{T}"
        ))
        s.connect(a, u.IO.a)
        s.connect(b, u.IO.b)
        return u.IO.o

    def TMinPositiveXAndOneMinusX(i: Node):
        u = s.add_substructure(f"minx1mx", CustomVHDLOperator(
            {"i": T},
            {"o": T},
            f"o <= i when unsigned(i) < to_unsigned({1 << (T.W_frac - 1)}, {T.W}) else std_logic_vector(to_unsigned({1 << T.W_frac}, {T.W}) - unsigned(i));",
            _unique_name = f"MinPositiveXandOneMinusX_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def TCeil(i: Node):
        u = s.add_substructure(f"ceil", CustomVHDLOperator(
            {"i": T},
            {"o": T},
            f"o({T.W_frac - 1} downto 0) <= (others => '0');\n" +
                f"plus_one <= std_logic_vector(unsigned(i) + to_unsigned({1 << T.W_frac}, {T.W}));" +
                f"o(o'high downto {T.W_frac}) <= i(i'high downto {T.W_frac}) when i({T.W_frac - 1} downto 0) = ({T.W_frac - 1} downto 0 => '0') else plus_one(o'high downto {T.W_frac});",
            f"signal plus_one: std_logic_vector({T.W} - 1 downto 0);",
            _unique_name = f"Ceil_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def TClampZeroToOne(i: Node): # 注意是 [0.0, 1.0), 以确保转八位时没有问题
        u = s.add_substructure(f"clamp01", CustomVHDLOperator(
            {"i": T},
            {"o": T},
            f"o <= (others => '0') when i(i'high) = '1' else\n" +
            f"     (i'high downto {T.W_frac} => '0', others => '1') when i(i'high downto {T.W_frac}) /= (i'high downto {T.W_frac} => '0') else\n" +
            f"     (i'high downto {T.W_frac} => '0') & i({T.W_frac - 1} downto 0);",
            _unique_name = f"Clamp0To1_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def fragCoordValueConvertor(i: Node):
        u = s.add_substructure(f"fragcoord_value_convertor", CustomVHDLOperator(
            {"i": UInt[12]},
            {"o": T},
            f"o({T.W_frac + 11} downto {T.W_frac}) <= i;\n" +
                f"o({T.W - 1} downto {T.W_frac + 12}) <= (others => '0');\n" +
                f"o({T.W_frac - 1} downto 0) <= (others => '0');",
            _unique_name = f"FragCoordValueConvertor_UInt_12_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def iTimeConvertor(i: Node):
        u = s.add_substructure(f"itime_convertor", CustomVHDLOperator(
            {"i": UInt[64]},
            {"o": T},
            f"o <= '0' & i({20 + T.W_int - 1} downto {20 - T.W_frac});",
            _unique_name = f"ITimeConvertor_UInt_64_{T}"
        ))
        s.connect(i, u.IO.i)
        return u.IO.o
    
    def Tto8bitConvertor(i: Node):
        u = s.add_substructure(f"to8bit_cvt", CustomVHDLOperator(
            {"i_clamped": T},
            {"o": Bits[8]},
            f"o <= i_clamped({T.W_frac - 1} downto {T.W_frac - 8});",
            _unique_name = f"To8bitConvertor_{T}"
        ))
        s.connect(TClampZeroToOne(i), u.IO.i_clamped)
        return u.IO.o
    
    def Concatenate888(r: Node, g: Node, b: Node):
        u = s.add_substructure("color_24bit_cvt", CustomVHDLOperator(
            {"r": Bits[8], "g": Bits[8], "b": Bits[8]},
            {"o": Bits[24]},
            "o <= r & g & b;",
            _unique_name = f"Concatenate_Bits_8_Bits_8_Bits_8"
        ))
        s.connect(r, u.IO.r)
        s.connect(g, u.IO.g)
        s.connect(b, u.IO.b)
        return u.IO.o
    
    # ============================================================================================================== #
    
    # ports
    iTime_us = s.add_port("itime_us", Input[UInt[64]])
    fragCoord_12bit = s.add_port("frag", Bundle[{"x": Input[UInt[12]], "y": Input[UInt[12]]}])
    fragColor_24bit = s.add_port("frag_color", Output[Bits[24]])
    
    # iTime
    iTime_s = iTimeConvertor(iTime_us) # 2^{-20} = 1 / 1048576 (s) ~ 1 (us)
    
    # fragCoord
    fragCoord = StructuralNodes({
        "x": fragCoordValueConvertor(fragCoord_12bit.x),
        "y": fragCoordValueConvertor(fragCoord_12bit.y)
    })
    
    # constants
    constants = (0.1, 0.95, 1, 3.75, 5, 5.5, 384)
    consts = s.add_substructure("consts", Constants(**{f"c{str(c).replace(".", "_")}": T(c) for c in constants}))
    C = lambda c: consts.IO.access(f"c{str(c).replace(".", "_")}")
    
    # ax, ay
    ax = TSubtraction(
        TAddition(
            TArithmeticShifter(fragCoord.x, -9),
            TArithmeticShifter(fragCoord.x, -7)
        ),
        C(5)
    )
    ay = TSubtraction(
        TAddition(
            TArithmeticShifter(fragCoord.y, -9),
            TArithmeticShifter(fragCoord.y, -7)
        ),
        C(3.75)
    )
    
    # ux, uy
    ux = TAddition(TSubtraction(ax, ay), C(5))
    uy = TAddition(TAddition(ax, ay), C(5))
    
    # fx, fy
    fx = TMinPositiveXAndOneMinusX(TFract(ux))
    fy = TMinPositiveXAndOneMinusX(TFract(uy))
    
    # vx, vy
    vx = TSubtraction(TCeil(ux), C(5.5))
    vy = TSubtraction(TCeil(uy), C(5.5))
    
    # vsqr, s, e, v
    vsqr = TAddition(TMultiplication(vx, vx), TMultiplication(vy, vy))
    vs = TAddition(C(1), TArithmeticShifter(vsqr, -3))
    ee = TSubtraction(TArithmeticShifter(TFract(TArithmeticShifter(TSubtraction(iTime_s, TArithmeticShifter(vs, -1)), -2)), 1), C(1))
    vv = TFract(TArithmeticShifter(TMin(fx, fy), 2))
    
    # mux, rampFactor, clampValue, mixFactor
    mux_calc = s.add_substructure("mux_calc", CustomVHDLOperator(
        {"ee": T, "vv": T},
        {"o": T},
        f"o <= vv when ee(ee'high) = '1' else std_logic_vector(to_unsigned({1 << T.W_frac}, {T.W}) - unsigned(vv));"
    ))
    s.connect(ee, mux_calc.IO.ee)
    s.connect(vv, mux_calc.IO.vv)
    mux = mux_calc.IO.o
    rampFactor = TSubtraction(TMultiplication(C(0.95), mux), TMultiplication(ee, ee))
    clampValue = TAddition(
        TAddition(
            TArithmeticShifter(rampFactor, 4),
            TArithmeticShifter(rampFactor, 2)
        ),
        C(1)
    )
    mixFactor = TAddition(TClampZeroToOne(clampValue), TMultiplication(vs, C(0.1)))
    
    # r, g, b, a
    r = Tto8bitConvertor(TSubtraction(C(1), TArithmeticShifter(mixFactor, -1)))
    g = Tto8bitConvertor(TSubtraction(C(1), TArithmeticShifter(mixFactor, -2)))
    b = Tto8bitConvertor(consts.IO.c1)
    a = b
    
    # 24bit frag_color output
    s.connect(Concatenate888(r, g, b), fragColor_24bit)
    
    return s


# construct
shader = Shader()
# rid = RuntimeId.create()
# shader.deduction(rid)
# print(shader.runtime_info(rid))


# expand
shader.singletonize()
shader.expand()
rid = RuntimeId.create()
shader.deduction(rid)
print(shader.runtime_info(rid))


# STA
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader_old", vivado_executable_path = "vivado.bat")
sta.analyse(shader, rid, skip_emitting_and_script_running = True)


# pipelining, 慢可以手动指定 c 只跑 FEAS
levels, Phi_Gr = pipelining(shader, rid, 24, model = "simple") # , model = "extended")
print("Phi_Gr", Phi_Gr)


# generation
model = shader.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)


# emit
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")
# emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

