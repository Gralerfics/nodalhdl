import math
import heapq

from typing import List, Set, Tuple
from dataclasses import dataclass, field
from functools import total_ordering

import networkx as nx


class MIDCSolver:
    """
        Mixed-Integer Difference Constraints Solver.
            x_j - x_i <= a_ij for some x_i are reals and some are integers.
        Ref: C.E. Leiserson and James B. Saxe, A mixed-integer programming problem which is efficiently solvable, Journal of Algorithms, Vol. 9, 1988, pp. 114-128
    """
    @dataclass
    class EdgeInfo:
        next: int # next edge ID, -1 as EndOfList
        next_r: int # next real edge ID
        u: int # start vertex ID
        v: int # end vertex ID
        a: float # a_ij
        b: float = 0 # b_ij
    
    def __init__(self, n: int = 0, k: int = 0):
        self.n: int = n # number of vertices, i.e. |V|
        self.k: int = k # number of integer vertices, i.e. |V_I|
        
        self.is_int: List[bool] = [True] * k + [False] * (n - k) # is_int[v]
        self.head: List[int] = [-1] * n # head[v]
        self.head_r: List[int] = [-1] * n # head_r[v], only record real edges
        
        self.m: int = 0 # number of edges
        self.edges: List[MIDCSolver.EdgeInfo] = []
        
        self.E_R: List[int] = [] # real edge IDs (real edge: (u, v), v is real vertex, i.e. not is_int[v])
        self.E_I: List[int] = [] # integer edge IDs
    
    def add_real_variable(self):
        self.n += 1
        self.is_int.append(False)
        self.head.append(-1)
        self.head_r.append(-1)
    
    def add_int_variable(self):
        self.n += 1
        self.k += 1
        self.is_int.append(True)
        self.head.append(-1)
        self.head_r.append(-1)
    
    def add_constraint(self, x_j: int, x_i: int, a_ij: float):
        """
            x_j - x_i <= a_ij.
            i.e. an edge weighted a_ij from x_i to x_j in the constraint graph.
        """
        self.edges.append(MIDCSolver.EdgeInfo(
            next = self.head[x_i],
            next_r = self.head_r[x_i], # invalid for int edges
            u = x_i,
            v = x_j,
            a = a_ij
        ))
        self.head[x_i] = self.m
        
        if self.is_int[x_j]:
            self.E_I.append(self.m)
        else:
            self.E_R.append(self.m)
            self.head_r[x_i] = self.m
        
        self.m += 1
    
    def solve(self):
        """
            Algorithm T in Section 5.
            Return False for infeasible, or x[].
        """
        # reweighting
        r = [0] * self.n # T1
        for _ in range(self.n - self.k): # T2, Bellman-Ford
            for e_r in self.E_R: # T3
                i, j, a_ij = self.edges[e_r].u, self.edges[e_r].v, self.edges[e_r].a
                r[j] = min(r[j], r[i] + a_ij) # T4
        for e_r in self.E_R: # T5, validate
            i, j, a_ij = self.edges[e_r].u, self.edges[e_r].v, self.edges[e_r].a
            if r[j] > r[i] + a_ij:
                return False # T6
        for edge in self.edges: # T7
            i, j, a_ij = edge.u, edge.v, edge.a
            edge.b = a_ij + r[i] - r[j] # T8
        
        # framework of M algorithm
        y = [0] * self.n # T9
        for _ in range(self.k): # T10
            # relax int edges
            for e_i in self.E_I: # T12
                i, j, b_ij = self.edges[e_i].u, self.edges[e_i].v, self.edges[e_i].b
                y[j] = min(y[j], math.floor(y[i] + b_ij)) # T13
            
            # relax real edges (Dijkstra)
            Q = [(y[v], v) for v in range(self.n)]
            heapq.heapify(Q) # T14
            visited = set()
            while Q: # T15
                _, i = heapq.heappop(Q) # T17, T18
                if i in visited:
                    continue
                visited.add(i)
                
                e_r = self.head_r[i]
                while e_r != -1: # T19
                    j, b_ij = self.edges[e_r].v, self.edges[e_r].b
                    if y[j] > y[i] + b_ij:
                        y[j] = y[i] + b_ij # T20
                        heapq.heappush(Q, (y[j], j))
                    e_r = self.edges[e_r].next_r
        
        # validate (only int edges needed)
        for e_i in self.E_I: # T23
            i, j, b_ij = self.edges[e_i].u, self.edges[e_i].v, self.edges[e_i].b
            if y[j] > y[i] + b_ij:
                return False # T24
        
        # recover the results
        x = [y[v] + r[v] for v in range(self.n)]
        return x


@total_ordering
class OrderedPair:
    def __init__(self, a, b):
        self.a = a
        self.b = b
    
    def __add__(self, other):
        if isinstance(other, OrderedPair):
            return OrderedPair(self.a + other.a, self.b + other.b)
        elif isinstance(other, (int, float)):
            return OrderedPair(self.a + other, self.b + other)
        return NotImplemented
    
    def __sub__(self, other):
        if isinstance(other, OrderedPair):
            return OrderedPair(self.a - other.a, self.b - other.b)
        elif isinstance(other, (int, float)):
            return OrderedPair(self.a - other, self.b - other)
        return NotImplemented
    
    __radd__ = __add__
    __rsub__ = __sub__
    
    def __eq__(self, other):
        if isinstance(other, OrderedPair):
            return (self.a, self.b) == (other.a, other.b)
        elif isinstance(other, (int, float)):
            return self.a == other
        return False
    
    def __lt__(self, other):
        if isinstance(other, OrderedPair):
            return (self.a, self.b) < (other.a, other.b)
        elif isinstance(other, (int, float)):
            return self.a < other
        return NotImplemented
    
    def __repr__(self):
        return f"({self.a}, {self.b})"

class ExtendedCircuit:
    """
        Extended circuit model allowing nonuniform functional element delays.
        Record (u, v, w) for edges and (v, d, e_ins[], e_outs[]) for internal edges, that is enough to build constraints and build H<E, F, wd>;
        Record (fs[]) for vertices, for WD computation.
        Support:
            1. Solve retiming r for a given clock period c by solving an MILP problem.
            2. Apply retiming r on G to obtain G_r.
            3. Run (Extended) WD algorithm to obtain D(u, v).
            4. TODO Run (Extended) CP algorithm to obtain Phi(G).
            5. Combine (3.), binary search and (1.) to solve clock-period-minimization problem.
    """
    EPSILON = 1e-5
    
    @dataclass
    class FunctionalElement:
        fs: Set[int] = field(default_factory = set)
    
    @dataclass
    class ExternalEdge:
        u: int = -1
        v: int = -1
        w: int = 0
        f_as: Set[int] = field(default_factory = set)
        f_bs: Set[int] = field(default_factory = set)
    
    @dataclass
    class InternalEdge:
        v: int
        d: float
        e_ins: Set[int] = field(default_factory = set)
        e_outs: Set[int] = field(default_factory = set)
    
    def __init__(self):
        self.V: List[ExtendedCircuit.FunctionalElement] = []
        self.E: List[ExtendedCircuit.ExternalEdge] = []
        self.F: List[ExtendedCircuit.InternalEdge] = []
    
    """ Getters """
    def get_vertex(self, v: int):
        if v > len(self.V) - 1:
            self.V.extend([ExtendedCircuit.FunctionalElement() for _ in range(v + 1 - len(self.V))])
        return self.V[v]
    
    def get_external_edge(self, e: int):
        if e > len(self.E) - 1:
            self.E.extend([ExtendedCircuit.ExternalEdge() for _ in range(e + 1 - len(self.E))])
        return self.E[e]
    
    def get_internal_edge(self, f: int):
        return self.F[f]
    
    def get_vertex_e_outs(self, v: int):
        return set([e_out for f in self.get_vertex(v).fs for e_out in self.get_internal_edge(f).e_outs])
    
    """ Constructing """
    def set_external_edge_weight(self, e: int, w: int):
        self.get_external_edge(e).w = w
    
    def add_internal_edge(self, v: int, d: float, e_ins_init: List[int] = [], e_outs_init: List[int] = []):
        f = len(self.F)
        self.F.append(ExtendedCircuit.InternalEdge(v = v, d = d))
        self.update_internal_edge(f, e_ins_update = e_ins_init, e_outs_update = e_outs_init)
        self.get_vertex(v).fs.add(f)
        return f
    
    def add_internal_edges(self, info: List[Tuple]):
        for entry in info:
            self.add_internal_edge(*entry)
    
    def update_internal_edge(self, f: int, e_ins_update: List[int] = [], e_outs_update: List[int] = []):
        f_obj = self.get_internal_edge(f)
        
        for e_in in e_ins_update:
            e_in_obj = self.get_external_edge(e_in)
            e_in_obj.v = f_obj.v
            e_in_obj.f_bs.add(f)
        f_obj.e_ins.update(e_ins_update)
        
        for e_out in e_outs_update:
            e_out_obj = self.get_external_edge(e_out)
            e_out_obj.u = f_obj.v
            e_out_obj.f_as.add(f)
        f_obj.e_outs.update(e_outs_update)
    
    """ Tasks """
    def solve_retiming(self, c: float, external_port_vertices: List[int] = [0]): # (1.)
        """
            Compute the retiming r on given clock period c.
            Return a legal r if feasible, or return False.
            
            Construct mixed-integer difference constraints and solve using MIDCSolver.
            Variable 0 ~ |V| - 1 are integer variables (i.e. r(v)); Variable |V| ~ |V| + |E| - 1 are real variables (i.e. R(e)).
        """
        c += ExtendedCircuit.EPSILON # ?
        
        solver = MIDCSolver(n = len(self.V) + len(self.E), k = len(self.V))
        
        r = lambda v: v
        R = lambda e: len(self.V) + e
        
        # 16.1  r(u) - R(e) <= -d(f) / c, for f --e-> ?, f in F_u
        for f_obj in self.F:
            for e in f_obj.e_outs:
                e_obj = self.get_external_edge(e)
                solver.add_constraint(r(e_obj.u), R(e), -f_obj.d / c)
                # print(f"r{e_obj.u} - R{e} <= {-f_obj.d / c}")
        
        # 16.2  R(e) - r(u) <= 1, for u --e-> ?
        for e, e_obj in enumerate(self.E):
            solver.add_constraint(R(e), r(e_obj.u), 1)
            # print(f"R{e} - r{e_obj.u} <= 1")
        
        # 16.3  r(u) - r(v) <= w(e), for u --e-> v
        uv_w_min = {}
        for e_obj in self.E:
            key = (e_obj.u, e_obj.v)
            value = uv_w_min.get(key)
            uv_w_min[key] = min(e_obj.w, value) if value is not None else e_obj.w # pick minimum w(e) between u and v
        for (u, v), w_e in uv_w_min.items():
            solver.add_constraint(r(u), r(v), w_e)
            # print(f"r{u} - r{v} <= {w_e}")
        
        # 16.4  R(e_a) - R(e_b) <= w(e_a) - d(f) / c, for e_a --f-> e_b
        for f_obj in self.F:
            for (e_a, e_b) in [(x, y) for x in f_obj.e_ins for y in f_obj.e_outs]:
                e_a_obj = self.get_external_edge(e_a)
                
                # [NOTICE] if e_a is a output edge of an external port vertex, this constraint should be deserted. It considers the delay from tail to head in cycle.
                if e_a_obj.u in external_port_vertices:
                    continue
                
                w_e_a = e_a_obj.w
                solver.add_constraint(R(e_a), R(e_b), w_e_a - f_obj.d / c)
                # print(f"R{e_a} - R{e_b} <= {w_e_a - f_obj.d / c}")
        
        solution = solver.solve()
        return False if not solution else solution[:len(self.V)]
    
    def apply_retiming(self, r: List[int]): # (2.)
        """
            Apply the retiming r on the graph.
            Equation (2): w_r(e) = w(e) + r(v) - r(u).
        """
        for e_obj in self.E:
            e_obj.w = e_obj.w + r[e_obj.v] - r[e_obj.u]
    
    def build_H(self, external_port_vertices: List[int] = [0]):
        """
            Build an auxiliary graph H<E, F, wd> for WD and CP.
            In H, vertices are from E (external edges), edges are from F (internal edges);
            The weight for H edge `e --f-> ?` wd(f) = (w(e), -d(f)).
        """
        H = nx.DiGraph()
        H_edges = [
            (e_a, e_b, OrderedPair(self.get_external_edge(e_a).w, -f_obj.d))
            for f_obj in self.F
            for e_a in f_obj.e_ins
            for e_b in f_obj.e_outs
            if f_obj.v not in external_port_vertices
        ] # all edges e_a --f-> e_b, [NOTICE] w/o f in external_port_vertices
        H.add_weighted_edges_from(H_edges)
        return H
    
    def compute_Ds(self, external_port_vertices: List[int] = [0]): # (3.)
        """
            Run (Extended) WD algorithm to obtain D(u, v).
            Return sorted and de-duplicated D-value list.
            TODO improve performance?
        """
        H = self.build_H(external_port_vertices = external_port_vertices) # [NOTICE] ignore f in v0?
        try:
            dists = dict(nx.all_pairs_dijkstra_path_length(H)) # [NOTICE] seems all nonnegative. need Johnson?
        except Exception:
            raise Exception("There is something wrong with the circuit structure")
        
        D_min = max([f_obj.d for f_obj in self.F]) # Phi(G) >= max{D(v, v) | v in V}, D(v, v) = max{d(f), f in F_v}
        Ds: Set[int] = set([D_min])
        
        for u in range(len(self.V)):
            for v in range(len(self.V)):
                if u == v:
                    continue
                
                W_uv, D_uv = None, None
                for e_a in self.get_vertex_e_outs(u):
                    for e_b in self.get_vertex_e_outs(v):
                        if e_a == e_b or dists.get(e_a) is None or dists[e_a].get(e_b) is None:
                            continue
                        
                        dist: OrderedPair = dists[e_a][e_b]
                        W = dist.a
                        D = max([self.get_internal_edge(f_a).d for f_a in self.get_external_edge(e_a).f_as]) - dist.b
                        if D <= D_min:
                            continue
                        
                        if W_uv is None or W < W_uv or (W == W_uv and D > D_uv):
                            W_uv = W
                            D_uv = D
                
                if D_uv is not None:
                    Ds.add(D_uv)
        
        return sorted(list(Ds))
    
    def minimize_clock_period(self, external_port_vertices: List[int] = [0]): # (5.)
        """
            Perform binary search on sorted Ds, check answer by solving retiming.
            Return Phi(G_r) and the retiming r.
        """
        Ds = self.compute_Ds(external_port_vertices = external_port_vertices)
        
        left, right = 0, len(Ds) - 1
        res = None
        while left <= right:
            mid = (left + right) // 2
            c = Ds[mid]
            
            solution = self.solve_retiming(c, external_port_vertices = external_port_vertices)
            if solution is not False:
                res = (c, solution)
                right = mid - 1
            else:
                left = mid + 1
        
        return res


# Test
if __name__ == '__main__':
    G = ExtendedCircuit()

    # G.add_internal_edge(0, 0, [3, 4], [0, 5])
    # G.add_internal_edge(1, 2, [0], [1])
    # G.add_internal_edge(1, 3, [0], [2])
    # G.add_internal_edge(1, 5, [5], [2])
    # G.add_internal_edge(2, 2, [1], [3])
    # G.add_internal_edge(2, 1, [1], [4])
    # G.add_internal_edge(2, 4, [2], [4])
    # G.set_external_edge_weight(0, 2)
    # G.set_external_edge_weight(5, 2)

    G.add_internal_edges([
        (0, 0, [12, 13, 14, 15], [0, 1, 2, 3]),
        (1, 2, [0], [4]),
        (1, 1, [0], [5]),
        (1, 3, [1], [5]),
        (2, 4, [2], [6, 7]),
        (2, 2, [3], [6, 7]),
        (2, 5, [3], [8]),
        (3, 1, [4], [9]),
        (3, 4, [4], [14]),
        (3, 2, [5], [9]),
        (3, 3, [5], [14]),
        (3, 7, [6], [14]),
        (3, 2, [6], [10]),
        (3, 4, [7], [10]),
        (3, 2, [8], [11]),
        (4, 3, [9], [12]),
        (4, 4, [9], [13]),
        (5, 3, [10], [15]),
        (5, 5, [11], [15])
    ])
    G.set_external_edge_weight(0, 1)
    G.set_external_edge_weight(1, 1)
    G.set_external_edge_weight(6, 1)
    G.set_external_edge_weight(7, 1)
    G.set_external_edge_weight(8, 1)

    print(G.minimize_clock_period([0]))

    # import time
    # t = time.time()
    # r = G.solve_retiming(5)
    # print(time.time() - t)
    # if r:
    #     print("r:", r)
    #     G.apply_retiming(r)
    #     [print(f"e_{idx}.w_r = {e_obj.w}") for idx, e_obj in enumerate(G.E)]
    # else:
    #     print("No solution.")

