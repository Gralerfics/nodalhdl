# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from ..core.signal import *
from ..core.structure import *
from ..core.hdl import *
from .retiming import *

from typing import Union, Dict, List, Tuple


class RetimingException(Exception): pass
class PipeliningException(Exception): pass


def to_extended_circuit(s: Structure, root_runtime_id: RuntimeId):
    """
        The structure `s` should be flattened and timing-analysed.
        TODO 1. 有问题 (to be repaired); 2. 简化节点
    """
    if not s.is_flattened:
        raise RetimingException("Only flattened and timing-analysed structures can be converted")
    
    G = ExtendedCircuit()
    
    # external edges
    external_edges_map: Dict[Node, int] = {}
    external_edge_idx = 0
    for net in s.get_nets():
        if not net.has_driver:
            continue
        driver_latency = net.driver().latency
        
        # each driver -> load pair indicates an external edge
        for load in net.get_loads():
            external_edges_map[load] = external_edge_idx
            G.set_external_edge_weight(external_edge_idx, driver_latency + load.latency)
            external_edge_idx += 1

    # vertex 0 (ports-equivalent-vertex)
    e_ins_0 = [external_edges_map[po] for _, po in s.ports_inside_flipped.nodes(filter = "out", flipped = True)] # e_ins_0 are all the output ports' edges
    e_outs_0 = [external_edges_map[pi_load] for _, pi in s.ports_inside_flipped.nodes(filter = "in", flipped = True) for pi_load in pi.located_net.get_loads()] # e_outs_0 ...
    G.add_internal_edge(0, 0.0, e_ins_0, e_outs_0)

    # vertices
    vertices_map: Dict[str, int] = {}
    internal_edges_list: List[Tuple[int, float, List[int], List[int]]] = []
    for idx, (subs_inst_name, subs) in enumerate(s.substructures.items()):
        vertex_idx = idx + 1 # 1 ~ N
        vertices_map[subs_inst_name] = vertex_idx
        
        subs_ports_outside = s.get_subs_ports_outside(subs_inst_name)
        in_ports = subs_ports_outside.nodes(filter = "in")
        out_ports = subs_ports_outside.nodes(filter = "out")
        
        timing_info = subs.get_runtime(root_runtime_id.next(subs_inst_name)).timing_info
        for pi_layered_name, pi in in_ports:
            for po_layered_name, po in out_ports:
                delay = timing_info.get((pi_layered_name, po_layered_name), None)
                if delay is not None:
                    e_ins = [external_edges_map[pi]]
                    e_outs = [external_edges_map[po_load] for po_load in po.located_net.get_loads()]
                    internal_edges_list.append((vertex_idx, delay, e_ins, e_outs))
    
    G.add_internal_edges(internal_edges_list)
    
    return G, vertices_map, external_edges_map


def to_simple_circuit(s: Structure, root_runtime_id: RuntimeId, ignore_delay_lower_than: float = 1e-2):
    """
        The structure `s` should be flattened and timing-analysed.
        TODO 简化节点, 忽略延迟小于 ignore_delay_lower_than 的节点 (除了 v0), 涉及到此处 (to_simple_circuit) 建图 G, retiming() 中 apply 等过程.
    """
    if not s.is_flattened:
        raise RetimingException("Only flattened can be converted")
    
    G = SimpleCircuit()
    
    # vertices
    G.add_vertex(0.0) # vertex 0
    
    vertices_map: Dict[str, int] = {}
    for idx, (subs_inst_name, subs) in enumerate(s.substructures.items()):
        timing_info = subs.get_runtime(root_runtime_id.next(subs_inst_name)).timing_info
        delay = timing_info.get(('_simple_in', '_simple_out'), 0.0) if timing_info is not None else 0.0
        
        # if delay > ignore_delay_lower_than:
        vertex_idx = idx + 1 # 1 ~ N
        vertices_map[subs_inst_name] = vertex_idx
        G.add_vertex(delay)
        # else:
        #     pass # TODO
    
    # edges
    edges_map: Dict[Node, int] = {}
    edge_idx = 0
    edges_dict: Dict[Tuple[int, int], int] = {}
    edges_list: List[Tuple[int, int, int]] = []
    
    for net in s.get_nets():
        if not net.has_driver:
            continue
        driver = net.driver()
        
        # each driver -> load pair indicates an edge
        for load in net.get_loads():
            edges_map[load] = edge_idx
            
            u = vertices_map[driver.of_structure_inst_name] if driver.of_structure_inst_name is not None else 0
            v = vertices_map[load.of_structure_inst_name] if load.of_structure_inst_name is not None else 0
            edges_dict[(u, v)] = driver.latency + load.latency # ignore repeated edge
            
            edge_idx += 1
    
    edges_list = [(u, v, l) for (u, v), l in edges_dict.items()]
    G.add_edges(edges_list)
    
    return G, vertices_map, edges_map


def retiming(s: Structure, root_runtime_id: RuntimeId, period: Union[float, str] = "min", model = "simple"):
    """
        Retiming.
        The structure `s` should be flattened and timing-analysed.
        `period`: target clock period (ns), use "min" to perform clock-period-minimization.
    """
    if model == "extended":
        G, V_map, E_map = to_extended_circuit(s, root_runtime_id)
        
        if period == "min":
            Phi_Gr, r = G.minimize_clock_period(external_port_vertices = [0])
        else: # number
            r = G.solve_retiming(period, external_port_vertices = [0])
            if not r:
                return False
    elif model == "simple":
        G, V_map, E_map = to_simple_circuit(s, root_runtime_id)

        print(f"[INFO] |V| = {len(G.V)}, |E| = {len(G.E)}") # TODO

        if period == "min":
            Phi_Gr, r = G.minimize_clock_period()
        else: # number
            r = G.solve_retiming(period)
            if not r:
                return False
    else:
        raise RetimingException(f"Unsupported circuit model type \'{model}\'")
    
    # apply the retiming to the structure
    for load in E_map.keys():
        driver = load.located_net.driver() # [NOTICE] 理论上 E_map 中 load 都有对应的 driver
        u = V_map[driver.of_structure_inst_name] if driver.of_structure_inst_name is not None else 0
        v = V_map[load.of_structure_inst_name] if load.of_structure_inst_name is not None else 0
        load.incr_latency(r[v] - r[u])
    
    for net in s.get_nets():
        net.transform_to_best_distribution()
    
    return Phi_Gr if period == "min" else period


def pipelining(s: Structure, root_runtime_id: RuntimeId, levels: int = None, period: float = None, model = "simple"):
    """
        Pipelining.
    """
    if s.is_sequential:
        raise PipeliningException("Only combinational structures can be pipelined")
    
    if levels is not None and period is not None:
        # add registers on all the input ports
        for _, pi in s.ports_inside_flipped.nodes(filter = "in", flipped = True):
            pi.set_latency(levels)
        
        if retiming(s, root_runtime_id, period = period, model = model): # success
            return levels, period
        else: # failed
            for _, pi in s.ports_inside_flipped.nodes(filter = "in", flipped = True):
                pi.set_latency(0)
            return False
    
    elif levels is not None:
        # add registers on all the input ports
        for _, pi in s.ports_inside_flipped.nodes(filter = "in", flipped = True):
            pi.set_latency(levels)
        
        # retiming
        Phi_Gr = retiming(s, root_runtime_id, period = "min", model = model)
    
    elif period is not None:
        # estimate? binary search?
        pass # TODO
        
        # levels = ...
        
        # retiming
        # Phi_Gr = retiming(s, root_runtime_id, period = TODO, model = model)
    
    else:
        raise Exception("At least one of `levels` and `period` should be provided")
    
    return levels, Phi_Gr

def insert_ready_valid_chain(model: HDLFileModel, levels: int, prev_ready_name = "in_ready", prev_valid_name = "in_valid", post_ready_name = "out_ready", post_valid_name = "out_valid", valid_regs_name = "valid_chain"):
    # if in_valid_name is not None and out_valid_name is not None: ... # TODO 四个信号名可以为 None, 为 None 时不构建相关功能
    
    model.add_port(prev_ready_name, "out", Bit)
    model.add_port(prev_valid_name, "in", Bit)
    model.add_port(post_ready_name, "in", Bit)
    model.add_port(post_valid_name, "out", Bit)
    
    # valid chain
    reg_valid_next_name, reg_valid_name = model.add_register(valid_regs_name, Bit, latency = levels)
    model.add_assignment(reg_valid_next_name, prev_valid_name)
    model.add_assignment(post_valid_name, reg_valid_name)
    
    # prev_ready
    prev_ready_buffer_name = f"{prev_ready_name}_buffer"
    model.add_signal(prev_ready_buffer_name, Bit)
    model.add_assignment(prev_ready_buffer_name, f"(not {reg_valid_name}) or {post_ready_name}")
    model.add_assignment(prev_ready_name, prev_ready_buffer_name)

    # enable
    enable_signal_name = f"{prev_ready_name}_and_{prev_valid_name}"
    model.set_register_enable_signal_name(enable_signal_name)
    model.add_assignment(enable_signal_name, f"{prev_ready_buffer_name} and {prev_valid_name}")


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

