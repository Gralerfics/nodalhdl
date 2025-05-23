# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.py.core import *
from nodalhdl.py.std import sfixed, uint, mux
from nodalhdl.py.glsl import vec2, vec3, vec4, abs, clamp

import math

T = SFixedPoint[20, 20]

def my_sin(x):
    y = (x + math.pi) % (2 * math.pi) - math.pi
    y2 = y * y
    y4 = y2 * y * y
    return y * (0.987862 - 0.155271 * y2 + 0.00559087 * y4) # 0.00564312, 0.00559312

def line(uv: vec2, speed, height, col: vec3, iTime):
    aux = abs(uv.x)
    nau = 1 - aux
    
    k0 = clamp(nau, 0, 1)
    y = uv.y + (k0 * k0 * (3 - (k0 << 1)) * my_sin(iTime * speed + uv.x * height) >> 2) # uv.y 是引用
    
    k2 = clamp((aux << 1) - 0.6, 0, 1)
    k3t1 = k2 * k2 * (0.1875 - (k2 >> 3))
    k3t1 = mux(k3t1 == 0, k3t1, 0.001)
    k3 = clamp((k3t1 + 0.004 - abs(y)) / k3t1, 0, 1)
    a = col * k3 * k3 * (3 - (k3 << 1))
    
    k4 = clamp(nau + (nau >> 1), 0, 1)
    return vec4(a.x, a.y, a.z, 1) * k4 * k4 * (3 - (k4 << 1))

def shader(iTime_us_u64: ComputeElement, fragCoord_u12: vec2) -> ComputeElement:
    iTime_us = sfixed(iTime_us_u64, T.W_int + 20, T.W_frac)
    iTime_s = sfixed(iTime_us >> 20, T.W_int, T.W_frac)
    
    fragCoord = vec2(sfixed(fragCoord_u12.x, T.W_int, T.W_frac), sfixed(fragCoord_u12.y, T.W_int, T.W_frac))
    
    uv = (fragCoord - 0.5 * vec2(1024, 768)) / 768
    o = vec4()
    for i in range(1, 6, 1):
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
levels, Phi_Gr = pipelining(s, rid, 80, model = "simple")
print("[INFO] Phi_Gr ~", Phi_Gr)
print(f"[INFO] pipelining finished: {time.time() - t} (s)")

# HDL generation
model = s.generation(rid, top_module_name = "shader")
insert_ready_valid_chain(model, levels)
emit_to_files(model.emit_vhdl(), "C:/Workspace/hdmi_ddr3_fragment_shader_proj/hdmi_ddr3_fragment_shader_proj.srcs/sources_1/new/shader")

