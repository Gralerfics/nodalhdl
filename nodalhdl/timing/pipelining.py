from ..core.structure import Structure, Node
from .retiming import ExtendedCircuit

from typing import Union, Dict, List, Tuple


class RetimingException(Exception): pass
class PipeliningException(Exception): pass


def to_extended_circuit(s: Structure):
    """
        The structure `s` should be flattened and timing-analysed.
    """
    if not s.is_flattened or not s.is_flatly_timed:
        raise RetimingException("Only flattened and timing-analysed structures can be converted")
    
    G = ExtendedCircuit()
    
    # external edges
    external_edges_map: Dict[Node, int] = {}
    external_edge_idx = 0
    for net in s.get_nets():
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
        
        for pi_full_name, pi in in_ports:
            for po_full_name, po in out_ports:
                delay = subs.timing_info.get((pi_full_name, po_full_name))
                if delay is not None:
                    e_ins = [external_edges_map[pi]]
                    e_outs = [external_edges_map[po_load] for po_load in po.located_net.get_loads()]
                    internal_edges_list.append((vertex_idx, delay, e_ins, e_outs))
    
    G.add_internal_edges(internal_edges_list)
    
    return G, vertices_map, external_edges_map

def apply_retiming_to_structure(s: Structure, r: List[int], vertices_map: Dict[str, int]):
    pass

def retiming(s: Structure, period: Union[float, str] = "min"):
    """
        Retiming.
        The structure `s` should be flattened and timing-analysed.
        `period`: target clock period (ns), use "min" to perform clock-period-minimization.
    """
    G, V_map, E_map = to_extended_circuit(s)
    
    if period == "min":
        Phi_Gr, r = G.minimize_clock_period(external_port_vertices = [0])
    else: # number
        r = G.solve_retiming(period, external_port_vertices = [0])
        if not r:
            return False
    
    apply_retiming_to_structure(s, G, V_map)

def pipelining(s: Structure): # , TODO
    """
        Pipelining.
        TODO
    """
    if s.is_sequential:
        raise PipeliningException("Only combinational structures can be pipelined")
    
    pass


"""
    TODO
    要有个 retiming, 针对运行过 sta 的

    拿着分析好的 structure 和 timing 信息去生成 ExtendedCircuit, 然后就可以跑 retiming 了 (pipeline 则先插点寄存器, 见下).
        每个模块对应一个 node, 从 1 开始, 保留 0 作为 ports 等效 vertex.
        每一个 driver -> load 都是一个 external edge (每个对应一个 load), 这个不是手动添加而是直接写标号, 所以一开始要走一轮赋好编号.
            或许直接写到 load 节点的属性里, 虽然有点脏, 但方便, 要么就存一个 mapping.
            driver 上 (或者 net 里, 或者不存, 每次遍历) 则存一下所有 load 对应的 edge 号.
            跑之前把所有 driver 上的寄存器放到 load 去 (Net().transform_driver_latency_to_loads), w(e) 就是 load 的 latency.
        每个模块的每个 i&o 对都是一个 internal edge.
            在目前暂不实现细致的时序模型而是以 port 为最小单位的情况下, 每个 internal edge 只会有一个输入.
                等下, 不分内部边的简化模式并不是如此. 而且加边时也可以省略很多东西. 看来这个得分开考虑了. 设置放哪里呢?
            每组 i&o i 的 port (注意要用 ports_outside, 不过因为 flattened, 也就一个? 不对, operators 可复用. 没事! 遍历的应该是所有模块的 ports_outside (注意还要去掉被其他模块引用的))
                (如果前面 duplicate 的话好像 operators 也 deepcopy 了, 保险起见按上面的)
            这个 I port 就连 load 的 e, O port 连所在 net 所有 load 的 e in E_outs.
    然后 retiming 后会得到 r, 前面要存一下模块和 r 的对应关系, 我们 retime 直接在 structure 上做.
        不过如果是以 port 为最小单位的情况, e 就对应实际的连线, 可以 apply retiming 时直接对应修改 w(e) -> load latency.
            不过要考虑简化模式. 还是在 structure 上做.
        怎么做? 每个模块 I ports 和 O ports 按 r 改一下就好了, 如果 O ports 去改的是 driver, 那改完再 transform 一下.
            加个方法, transform 到 driver 以节约 reg, 可以最后的最后跑一下.
    
    pipelining 的话 structure 必须是 not is_sequential 的,
        也就是前面的单纯 retiming 可以允许 sequential, 所以运行 sta 前不能直接去原来的上面改 latency.
        话说论文里提到个什么来着, 忘了, 晚点看下.
    每个输入端口要插入相同数量的寄存器,
        这个数量除了用户设定, 怎么自动计算?
            比如时序报告中同时跑一个顶层模块输入到输出的最大路径 (要得到这个又不能插寄存器, 或者在跑下面那行的过程中通过模块的延迟累加起来), 除以预期时钟周期, 再去掉一些寄存器延迟;
            或者同时还要考虑上限, 即最多模块数的路径上有几个模块, 最多插 n - 1 个, 再多没意义.
        
"""