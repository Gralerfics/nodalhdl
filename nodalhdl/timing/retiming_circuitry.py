import uuid
import weakref
from typing import List
from dataclasses import dataclass, field

import math
import heapq

import numpy

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


class ExtendedCircuit:
    """
        Extended circuit model allowing nonuniform functional element delays.
        Only record (u, v, w) for edges and (v, d, e_ins, e_outs) for internal edges, that is enough to build constraints and build H<E, F, wd>.
        Support:
            1. Solve retiming r for a given clock period c by solving an MILP problem.
            2. Apply retiming r on G to obtain G_r.
            3. TODO Run (Extended) WD algorithm to obtain D(u, v).
            4. TODO Run (Extended) CP algorithm to obtain Phi(G).
            5. TODO Combine (3.), binary search and (1.) to solve clock-period-minimization problem.
        
        TODO 允许转为 H Model (用 networkx?), 运行 WD 得到 D, 即 Phi(G_r) 可能范围.
                H Model 需要所有 e_a --f-> e_b, 也就是条件 16.4 的遍历过程.
                WD 要运行全源最短路, 使用 Johnson. 但是似乎没有负边, H 的边都是内部边延迟, 所以似乎普通的 |V| 遍 Dijkstra 就行了?
                    nx 里还有 all_pairs_all_shortest_paths(G, weight='weight', method='dijkstra').
                    注: weight 应该是 wd(f) = (w(e), -d(f)) for e --f-> ?.
    """
    EPSILON = 1e-5
    
    @dataclass
    class ExternalEdge:
        u: int = -1
        v: int = -1
        w: int = 0
    
    @dataclass
    class InternalEdge:
        v: int
        d: float
        e_ins: List[int] = field(default_factory = list)
        e_outs: List[int] = field(default_factory = list)
    
    def __init__(self, n_v: int):
        self.n_v: int = n_v # number of functional elements
        self.E: List[ExtendedCircuit.ExternalEdge] = []
        self.F: List[ExtendedCircuit.InternalEdge] = []
    
    def get_external_edge(self, e: int):
        if e > len(self.E) - 1:
            self.E.extend([ExtendedCircuit.ExternalEdge() for _ in range(e + 1 - len(self.E))])
        return self.E[e]
    
    def set_external_edge_weight(self, e: int, w: int):
        self.get_external_edge(e).w = w
    
    def add_internal_edge(self, v: int, d: float, e_ins_init: List[int] = [], e_outs_init: List[int] = []):
        f = len(self.F)
        self.F.append(ExtendedCircuit.InternalEdge(v = v, d = d))
        self.update_internal_edge(f, e_ins_update = e_ins_init, e_outs_update = e_outs_init)
        return f
    
    def update_internal_edge(self, f: int, e_ins_update: List[int] = [], e_outs_update: List[int] = []):
        f_obj = self.F[f]
        
        for e_in in e_ins_update:
            self.get_external_edge(e_in).v = f_obj.v
        f_obj.e_ins.extend(e_ins_update)
        
        for e_out in e_outs_update:
            self.get_external_edge(e_out).u = f_obj.v
        f_obj.e_outs.extend(e_outs_update)
    
    def solve_retiming(self, c: float): # (1.)
        """
            Compute the retiming r on given clock period c.
            Return a legal r if feasible, or return False.
            
            Construct mixed-integer difference constraints and solve using MIDCSolver.
            Variable 0 ~ n_v - 1 are integer variables (i.e. r(v)); variable n_v ~ n_v + n_e - 1 are real variables (i.e. R(e)).
        """
        c += ExtendedCircuit.EPSILON # ?
        
        solver = MIDCSolver(n = self.n_v + len(self.E), k = self.n_v)
        
        r = lambda v: v
        R = lambda e: self.n_v + e
        
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
                w_e_a = self.get_external_edge(e_a).w
                solver.add_constraint(R(e_a), R(e_b), w_e_a - f_obj.d / c)
                # print(f"R{e_a} - R{e_b} <= {w_e_a - f_obj.d / c}")
        
        solution = solver.solve()
        return False if not solution else solution[:self.n_v]
    
    def apply_retiming(self, r: List[int]): # (2.)
        """
            Apply the retiming r on the graph.
            Equation (2): w_r(e) = w(e) + r(v) - r(u).
        """
        for e_obj in self.E:
            e_obj.w = e_obj.w + r[e_obj.v] - r[e_obj.u]
    
    def build_H(self):
        pass # TODO
    
    def WD(self):
        pass # TODO


# Test
G = ExtendedCircuit(n_v = 3)

G.add_internal_edge(0, 0, [3, 4], [0, 5])
G.add_internal_edge(1, 2, [0], [1])
G.add_internal_edge(1, 3, [0], [2])
G.add_internal_edge(1, 5, [5], [2])
G.add_internal_edge(2, 2, [1], [3])
G.add_internal_edge(2, 1, [1], [4])
G.add_internal_edge(2, 4, [2], [4])

G.set_external_edge_weight(0, 2)
G.set_external_edge_weight(5, 2)

import time
t = time.time()
r = G.solve_retiming(8)
print(time.time() - t)
if r:
    print("r:", r)
    G.apply_retiming(r)
    [print(f"e_{idx}.w_r = {e_obj.w}") for idx, e_obj in enumerate(G.E)]
else:
    print("No solution.")

