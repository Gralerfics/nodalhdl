# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.py.core import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


from nodalhdl.py.glsl import vec2


T = SFixedPoint[16, 12]

def test(iTime_us_u64: ComputeElement, fragCoord_u12: vec2) -> ComputeElement:
    return fragCoord_u12.x[7:] @ fragCoord_u12.y[7:] @ "11111111"


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
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_test", vivado_executable_path = "vivado.bat")
sta.analyse(s, rid, skip_emitting_and_script_running = False) # False

# pipelining
levels, Phi_Gr = pipelining(s, rid, 3, model = "simple")
print("Phi_Gr ~", Phi_Gr)

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")
# emit_to_files(model.emit_vhdl(), "C:/Workspace/test_project/test_project.srcs/sources_1/new")

