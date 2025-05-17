from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.py.core import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


from nodalhdl.py.std import sfixed
from nodalhdl.py.glsl import vec2, fract, min


T = SFixedPoint[16, 12]

def shader(iTime_us: ComputeElement, fragCoord: vec2) -> ComputeElement:
    iTime_us = sfixed(iTime_us, T.W_int + 20, T.W_frac)
    iTime_s = iTime_us >> 20 # i.e. 1 / 1048576 (s) ~ 1 (us)
    
    a = vec2((fragCoord.x >> 9) + (fragCoord.x >> 7) - 5, (fragCoord.y >> 9) + (fragCoord.y >> 7) - 3.75)
    
    u = (a.x - a.y + 5, a.x + a.y + 5)
    
    # f = fract(u)
    # f = min(f, 1 - f)
    
    return u.x


s = Structure()
iTime_us = ComputeElement(s, "itime_us", UInt[64])
fragCoord = vec2(
    x = ComputeElement(s, "frag_x", UInt[12]),
    y = ComputeElement(s, "frag_y", UInt[12]),
)
shader(iTime_us, fragCoord).output("frag_color")


# expand
s.singletonize()
s.expand()
rid = RuntimeId.create()
s.deduction(rid)
print(s.runtime_info(rid))

# # static timing analysis
# sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader", vivado_executable_path = "vivado.bat")
# sta.analyse(s, rid, skip_emitting_and_script_running = False)

# # pipelining
# levels, Phi_Gr = pipelining(s, rid, 24, model = "simple")
# print("Phi_Gr ~ ", Phi_Gr)

# # HDL generation
# model = s.generation(rid, top_module_name = "shader")
# insert_ready_valid_chain(model, levels)
# emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

