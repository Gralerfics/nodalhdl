from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic.bits import *
from nodalhdl.basic.arith import *

from nodalhdl.core.hdl import emit_to_files
from nodalhdl.timing.sta import VivadoSTA
from nodalhdl.timing.pipelining import pipelining


T = SFixedPoint[16, 12] # 目前要求 W_int <= 45 且 8 <= W_frac <= 20


def ArithmeticShifter(n: int): # n > 0: move left, else right
    return CustomVHDLOperator(
        {"i": T},
        {"o": T},
        f"o <= i {"sla" if n >= 0 else "sra"} {abs(n)};"
    )


# def 


def Shader() -> Structure:
    s = Structure()
    
    iTime_ms = s.add_port("iTimeUs", Input[UInt[64]])
    fragCoord = s.add_port("fragCoord", Bundle[{"x": Input[T], "y": Input[T]}])
    fragColor_24bit = s.add_port("fragOutput", Output[Bits[24]])
    
    # iTime
    iTime_cvt = s.add_substructure("iTimeCvt", CustomVHDLOperator(
        {"i": UInt[64]},
        {"o": T},
        f"o <= '0' & i({20 + T.W_int - 2} downto {20 - T.W_frac, 0});" # TODO f"o <= '0' & i({min(20 + T.W_int - 2, 63)} downto {max(20 - T.W_frac, 0)});"
    ))
    s.connect(iTime_ms, iTime_cvt.IO.i)
    iTime_s = iTime_cvt.IO.o # 2^{-20} = 1 / 1048576 (s) ~ 1 (us)
    
    # constants
    constants = (0.1, 0.95, 1, 3.75, 5, 5.5, 384)
    consts = s.add_substructure("consts", Constants(**{f"c{str(c).replace(".", "_")}": T(c) for c in constants}))
    
    # ax
    fcx_sra_9 = s.add_substructure("fcx_sra_9", ArithmeticShifter(-9))
    fcx_sra_7 = s.add_substructure("fcx_sra_7", ArithmeticShifter(-7))
    fcx_sra_add = s.add_substructure("fcx_sra_add", Add(T, T))
    ax_const_sub = s.add_substructure("fcx_const_sub", Subtract(T, T))
    s.connect(fragCoord.x, fcx_sra_9.IO.i)
    s.connect(fragCoord.x, fcx_sra_7.IO.i)
    s.connect(fcx_sra_9.IO.o, fcx_sra_add.IO.a)
    s.connect(fcx_sra_7.IO.o, fcx_sra_add.IO.b)
    s.connect(fcx_sra_add.IO.r, ax_const_sub.IO.a)
    s.connect(consts.IO.c5, ax_const_sub.IO.b)
    ax = ax_const_sub.IO.r
    
    # ay
    fcy_sra_9 = s.add_substructure("fcy_sra_9", ArithmeticShifter(-9))
    fcy_sra_7 = s.add_substructure("fcy_sra_7", ArithmeticShifter(-7))
    fcy_sra_add = s.add_substructure("fcy_sra_add", Add(T, T))
    ay_const_sub = s.add_substructure("fcy_const_sub", Subtract(T, T))
    s.connect(fragCoord.y, fcy_sra_9.IO.i)
    s.connect(fragCoord.y, fcy_sra_7.IO.i)
    s.connect(fcy_sra_9.IO.o, fcy_sra_add.IO.a)
    s.connect(fcy_sra_7.IO.o, fcy_sra_add.IO.b)
    s.connect(fcy_sra_add.IO.r, ay_const_sub.IO.a)
    s.connect(consts.IO.c5, ay_const_sub.IO.b)
    ay = ay_const_sub.IO.r
    
    # ux, uy
    ax_sub_ay = s.add_substructure("ax_sub_ay", Subtract(T, T))
    s.connect(ax, ax_sub_ay.IO.a)
    s.connect(ay, ax_sub_ay.IO.b)
    ax_add_ay = s.add_substructure("ax_add_ay", Add(T, T))
    s.connect(ax, ax_add_ay.IO.a)
    s.connect(ay, ax_add_ay.IO.b)
    ux_const_add = s.add_substructure("ux_const_add", Add(T, T))
    s.connect(ax_sub_ay.IO.r, ux_const_add.IO.a)
    s.connect(consts.IO.C5, ux_const_add.IO.b)
    uy_const_add = s.add_substructure("uy_const_add", Add(T, T))
    s.connect(ax_add_ay.IO.r, uy_const_add.IO.a)
    s.connect(consts.IO.C5, uy_const_add.IO.b)
    ux = ux_const_add.IO.r
    uy = uy_const_add.IO.r
    
    # fx, fy
    
    # fragColor -> 24bit and output
    color_24bit_cvt = s.add_substructure("color_24bit_cvt", CustomVHDLOperator(
        {"r": T, "g": T, "b": T, "a": T},
        {"color_24": Bits[24]},
        "color_24 <= " + " & ".join([f"{attr}({T.W_frac - 1} downto {T.W_frac - 8})" for attr in "rgb"]) + ";" # TODO
    ))
    # s.connect(, color_24bit_cvt.IO.r)
    # s.connect(, color_24bit_cvt.IO.g)
    s.connect(consts.IO.c1, color_24bit_cvt.IO.b)
    s.connect(consts.IO.c1, color_24bit_cvt.IO.a)
    s.connect(color_24bit_cvt.IO.color_24, fragColor_24bit)
    
    return s


shader = Shader()

rid = RuntimeId.create()
shader.deduction(rid)
print(shader.runtime_info(rid))

# model = shader.generation(rid)

# emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

