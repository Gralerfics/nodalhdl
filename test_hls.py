from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.py.core import ComputeElement
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *


from nodalhdl.py.proposed import us_to_s
from types import SimpleNamespace


T = SFixedPoint[16, 12]

def shader(iTime_us, fragCoord) -> ComputeElement:
    iTime_s = us_to_s(iTime_us, T)
    
    pass


s = Structure()
iTime_us = ComputeElement(s, "itime_us", UInt[64])
fragCoord = SimpleNamespace(
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

# static timing analysis
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader", vivado_executable_path = "vivado.bat")
sta.analyse(s, rid, skip_emitting_and_script_running = False)

# pipelining
levels, Phi_Gr = pipelining(s, rid, 24, model = "simple")
print("Phi_Gr ~ ", Phi_Gr)

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

