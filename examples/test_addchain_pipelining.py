# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from nodalhdl.core.signal import *
from nodalhdl.core.structure import *
from nodalhdl.basic_arch.arith import *
from nodalhdl.basic_arch.bits import *
from nodalhdl.timing.sta import *
from nodalhdl.timing.pipelining import *

from typing import List

import time


def AddChain(n: int, t: SignalType) -> Structure:
    s = Structure()
    
    i = [s.add_port(f"i{idx}", Input[t]) for idx in range(n)]
    o = s.add_port("o", Output[Auto])
    
    adder: list[StructureProxy] = []
    for idx in range(n - 1):
        adder.append(s.add_substructure(f"adder{idx}", BitsAdd(t, t)))

        s.connect(adder[-2].IO.r if idx > 0 else i[0], adder[-1].IO.a)
        s.connect(i[idx + 1], adder[-1].IO.b)
    
    s.connect(adder[-1].IO.r, o)

    return s


ns = [10, 100, 200, 500, 1000]
# skips = [False, False, False, False, False]
skips = [True, True, True, True, True]
level = 10
op_type = UInt[4]

ss: List[Structure] = []
rids: List[RuntimeId] = []
stas: List[VivadoSTA] = []

for idx, n in enumerate(ns):
    t = time.time()
    ss.append(AddChain(n, op_type))
    rids.append(RuntimeId.create())
    ss[idx].deduction(rids[idx])
    print(f"Build n = {n}: ", time.time() - t)

for idx, n in enumerate(ns):
    stas.append(VivadoSTA(part_name = "xc7a200tfbg484-1", temporary_workspace_path = f".vivado_sta_s{n}", vivado_executable_path = "vivado.bat"))
    stas[idx].analyse(ss[idx], rids[idx], skip_emitting_and_script_running = skips[idx])

for idx, n in enumerate(ns):
    for _, pi in ss[idx].ports_inside_flipped.nodes(filter = "in", flipped = True):
        pi.set_latency(level)
    
    t = time.time()
    print(f"Phi_Gr (s{n}, simple): ", retiming(ss[idx], rids[idx], period = "min", model = "simple"))
    print(f"Time (s{n}, simple): ", time.time() - t)
    
    t = time.time()
    print(f"Phi_Gr (s{n}, extended): ", retiming(ss[idx], rids[idx], period = "min", model = "extended"))
    print(f"Time (s{n}, extended): ", time.time() - t)

