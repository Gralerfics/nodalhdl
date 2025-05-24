# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.py.core import *
from nodalhdl.py.std import mux, sfixed, uint
from nodalhdl.py.glsl import vec2, vec3, vec4, clamp, dot, min, max, abs

import math

T = SFixedPoint[12, 16]

def my_sin(x):
    y = (x + math.pi) % (2 * math.pi) - math.pi
    y2 = y * y
    y4 = y2 * y * y
    return y * (0.987862 - 0.155271 * y2 + 0.00559087 * y4) # 0.00564312, 0.00559312

def shader(iTime_us_u64: ComputeElement, fragCoord_u12: vec2) -> ComputeElement:
    iTime_us = sfixed(iTime_us_u64, T.W_int + 20, T.W_frac)
    iTime_s = sfixed(iTime_us >> 20, T.W_int, T.W_frac)
    
    iResolution = vec3(1024, 768, 1)
    fragCoord = vec2(sfixed(fragCoord_u12.x, T.W_int, T.W_frac), iResolution.y - sfixed(fragCoord_u12.y, T.W_int, T.W_frac))
    
    u = ((fragCoord << 1) - iResolution.xy) / iResolution.x
    s = my_sin(iTime_s)
    fac = 2.5 + (s >> 1)
    tp = fac / iResolution.xy
    p = vec3(tp.x, tp.y, fac)
    a = vec3()
    
    o = vec4()
    for i in range(21):
        o = 2 + vec4(p.x, -p.x, a.x, a.y)
        a = abs(p)
        l = p + 0.5
        l_sqr = dot(l, l)
        p = p + vec3(u.x, u.y, -1) * min(1 - max(a.xy, max(a.y, -p.z)).x, l_sqr - 0.25)
    
    t = max((a.xz << 2) - p.y, 0)
    t_sqr = dot(t, t)
    o = 0.01 / t_sqr + 0.8 / o + 30 * min(3 - o, 0.01)
    o = o / (dot(p, p) + 0.4 / dot(p + 0.5, p + 0.8))
    
    fragColor = clamp(o, 0, 0.9999)
    return uint(fragColor.r << 8, 8) @ uint(fragColor.g << 8, 8) @ uint(fragColor.b << 8, 8)


from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *

import time
import sys

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

# static timing analysis
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader_cornell267", vivado_executable_path = "vivado.bat")
sta.analyse(s, rid)

# pipelining
print(f"[INFO] start pipelining")
t = time.time()
levels, Phi_Gr = pipelining(s, rid, 100, model = "simple")
print("[INFO] Phi_Gr ~", Phi_Gr)
print(f"[INFO] pipelining finished: {time.time() - t} (s)")

# levels = 100
# res = pipelining(s, rid, levels, 12.000, model = "simple")
# if res:
#     print(f"[INFO] pipelining finished: {time.time() - t} (s)")
# else:
#     print(f"[ERROR] retiming failed")
#     sys.exit(-1)

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

