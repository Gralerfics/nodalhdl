# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.py.core import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


"""
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    fragColor = vec4(mod(uv.x, 0.4), mod(uv.y, 0.4), 1.0, 1.0);
}
"""

from nodalhdl.py.glsl import vec2, vec4, clamp
from nodalhdl.py.std import sfixed, uint

T = SFixedPoint[16, 12]

def test(iTime_us_u64: ComputeElement, fragCoord_u12: vec2) -> ComputeElement:
    fragCoord = vec2(sfixed(fragCoord_u12.x, T.W_int, T.W_frac), sfixed(fragCoord_u12.y, T.W_int, T.W_frac))
    uv = (fragCoord - 0.5 * vec2(1024, 768)) / 768
    fragColor = clamp(vec4(uv.x % 0.4, uv.y % 0.4, 1, 1), 0, 0.9999)
    return uint(fragColor.r << 8, 8) @ uint(fragColor.g << 8, 8) @ "11111111"


s = Structure()
iTime_us = ComputeElement(s, "itime_us", UInt[64])
fragCoord = vec2(
    x = ComputeElement(s, "frag_x", UInt[12]),
    y = ComputeElement(s, "frag_y", UInt[12]),
)
test(iTime_us, fragCoord).output("frag_color")


# expand
s.singletonize()
s.expand()
rid = RuntimeId.create()
s.deduction(rid)
print(s.runtime_info(rid))

# static timing analysis
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader_mod_pattern", vivado_executable_path = "vivado.bat")
sta.analyse(s, rid)

# pipelining
levels, Phi_Gr = pipelining(s, rid, 27, model = "simple")
print("Phi_Gr ~", Phi_Gr)

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

