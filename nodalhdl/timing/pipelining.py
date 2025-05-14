from ..core.structure import RuntimeId, Structure, Node
from .retiming import ExtendedCircuit, SimpleCircuit

from typing import Union, Dict, List, Tuple


class RetimingException(Exception): pass
class PipeliningException(Exception): pass


# TODO 只有线网、只有一端（常数）等情况，不需要转到电路模型.


def to_extended_circuit(s: Structure, root_runtime_id: RuntimeId):
    """
        The structure `s` should be flattened and timing-analysed.
    """
    if not s.is_flattened: # or not s.is_flatly_timed: TODO
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
        out_ports = subs_ports_outside.nodes(filter = "out") # TODO 加个功能让一次能两个一起返回了吧
        
        timing_info = subs.get_runtime(root_runtime_id.next(subs_inst_name)).timing_info
        for pi_layered_name, pi in in_ports:
            for po_layered_name, po in out_ports:
                delay = timing_info.get((pi_layered_name, po_layered_name))
                if delay is not None:
                    e_ins = [external_edges_map[pi]]
                    e_outs = [external_edges_map[po_load] for po_load in po.located_net.get_loads()]
                    internal_edges_list.append((vertex_idx, delay, e_ins, e_outs))
    
    G.add_internal_edges(internal_edges_list)
    
    return G, vertices_map, external_edges_map


def to_simple_circuit(s: Structure, root_runtime_id: RuntimeId):
    """
        The structure `s` should be flattened and timing-analysed.
    """
    if not s.is_flattened: # or not s.is_flatly_timed: TODO
        raise RetimingException("Only flattened and timing-analysed structures can be converted")
    
    G = SimpleCircuit()
    
    # vertices
    G.add_vertex(0.0) # vertex 0
    
    vertices_map: Dict[str, int] = {}
    for idx, (subs_inst_name, subs) in enumerate(s.substructures.items()):
        vertex_idx = idx + 1 # 1 ~ N
        vertices_map[subs_inst_name] = vertex_idx
        
        timing_info = subs.get_runtime(root_runtime_id.next(subs_inst_name)).timing_info
        G.add_vertex(timing_info.get(('_simple_in', '_simple_out'), 0.0) if timing_info is not None else 0.0)
    
    # edges
    edges_map: Dict[Node, int] = {}
    edge_idx = 0
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
            edges_list.append((u, v, driver.latency + load.latency))
            
            edge_idx += 1
    
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
    
    return Phi_Gr


def pipelining(s: Structure, root_runtime_id: RuntimeId, levels: int = None, period: float = None, model = "simple"):
    """
        Pipelining.
    """
    if s.is_sequential:
        raise PipeliningException("Only combinational structures can be pipelined")
    
    if (levels is not None and period is not None) or (levels is None and period is None):
        raise PipeliningException("One and only one of `levels` and `period` should be provided")
    
    if levels is not None:
        # add registers on all the input ports
        for _, pi in s.ports_inside_flipped.nodes(filter = "in", flipped = True):
            pi.set_latency(levels)
        
        # retiming
        return retiming(s, root_runtime_id, period = "min", model = model)
    else: # period is not None
        # estimate? binary search?
        pass # TODO
        
        # retiming
        # return retiming(s, root_runtime_id, period = TODO, model = model)

"""
    pipelining 的话 structure 必须是 not is_sequential 的,
        也就是前面的单纯 retiming 可以允许 sequential, 所以运行 sta 前不能直接去原来的上面改 latency.
        话说论文里提到个什么来着 (关于 pipelining), 忘了, 晚点看下.
    每个输入端口要插入相同数量的寄存器,
        这个数量除了用户设定, 怎么自动计算?
            比如时序报告中同时跑一个顶层模块输入到输出的最大路径 (要得到这个又不能插寄存器, 或者在跑下面那行的过程中通过模块的延迟累加起来), 除以预期时钟周期, 再去掉一些寄存器延迟;
            或者同时还要考虑上限, 即最多模块数的路径上有几个模块, 最多插 n - 1 个, 再多没意义.
"""