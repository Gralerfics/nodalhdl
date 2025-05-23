# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

# TODO 有点问题, 中间黑了; 会是因为 % 吗?

from nodalhdl.core.signal import *
from nodalhdl.py.core import *
from nodalhdl.py.std import sfixed, uint
from nodalhdl.py.glsl import vec2, vec3, vec4, abs, smoothstep, clamp

import math

T = SFixedPoint[12, 12]

def my_sin(x):
    x = (x + math.pi) % (2 * math.pi) - math.pi
    x3 = x * x * x
    x5 = x3 * x * x
    return 0.987862 * x - 0.155271 * x3 + 0.00564312 * x5

def line(uv: vec2, speed, height, col: vec3, iTime):
    uv.y = uv.y + smoothstep(1, 0, abs(uv.x)) * my_sin(iTime * speed + uv.x * height) * 0.2
    a = col * smoothstep(0.06 * smoothstep(0.2, 0.9, abs(uv.x)), 0, abs(uv.y) - 0.004) # * col # TODO
    return vec4(a.x, a.y, a.z, 1) * smoothstep(1, 0.3, abs(uv.x))

def shader(iTime_us_u64: ComputeElement, fragCoord_u12: vec2) -> ComputeElement:
    iTime_us = sfixed(iTime_us_u64, T.W_int + 20, T.W_frac)
    iTime_s = sfixed(iTime_us >> 20, T.W_int, T.W_frac)
    
    fragCoord = vec2(sfixed(fragCoord_u12.x, T.W_int, T.W_frac), sfixed(fragCoord_u12.y, T.W_int, T.W_frac))
    
    uv = (fragCoord - 0.5 * vec2(1024, 768)) / 768
    o = vec4()
    for i in range(2, 7, 2):
        t = i / 5
        o = o + line(uv, 1 + t, 4 + t, vec3(0.2 + t * 0.7, 0.2 + t * 0.4, 0.3), iTime_s)
    
    fragColor = clamp(o, 0, 0.9999)
    return uint(fragColor.r << 8, 8) @ uint(fragColor.g << 8, 8) @ uint(fragColor.b << 8, 8)


from nodalhdl.core.structure import *
from nodalhdl.core.hdl import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *

import time

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
sta = VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = ".vivado_sta_shader_dt", vivado_executable_path = "vivado.bat", pool_size = 12, syn_max_threads = 8)
sta.analyse(s, rid)

# pipelining
print(f"[INFO] start pipelining")
t = time.time()
levels, Phi_Gr = pipelining(s, rid, 60, model = "simple")
print("Phi_Gr ~", Phi_Gr)
print(f"[INFO] pipelining finished: {time.time() - t} s")

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

