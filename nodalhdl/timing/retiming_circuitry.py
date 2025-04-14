import uuid
import weakref
import math
import heapq
from dataclasses import dataclass
from typing import List

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
                
                # e = self.head[i]
                # while e != -1: # T19
                #     j, b_ij = self.edges[e].v, self.edges[e].b
                #     if not self.is_int[j]: # j in V_R
                #         if y[j] > y[i] + b_ij:
                #             y[j] = y[i] + b_ij # T20
                #             heapq.heappush(Q, (y[j], j))
                #     e = self.edges[e].next

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


# Test
Nv = 3
Ne = 5 + 1
c = 5

# 16.1      r(v) - R(e) <= -d(f) / c            (R(e), r(v)): -d(f) / c
a_1 = {
    ('R0', 'r0'): -0 / c,
    # ('R0', 'r0'): -0 / c,
    ('R1', 'r1'): -2 / c,
    ('R2', 'r1'): -3 / c,
    ('R3', 'r2'): -2 / c,
    ('R4', 'r2'): -1 / c,
    ('R4', 'r2'): -4 / c,
    
    ('R5', 'r0'): -5 / c,
    # ('R5', 'r0'): -5 / c
}

# 16.2      R(e) - r(v) <= 1                    (r(v), R(e)): 1
a_2 = {key: 1 for key in set([(xj, xi) for xi, xj in a_1.keys()])}

# 16.3      r(u) - r(v) <= w(e)                 (r(v), r(u)): w(e)
a_3 = {
    ('r1', 'r0'): 2,
    ('r2', 'r1'): 0,
    # ('r2', 'r1'): 0,
    ('r0', 'r2'): 0,
    # ('r0', 'r2'): 0,
    
    # ('r1', 'r0'): 2
}

# 16.4      R(ea) - R(eb) <= w(ea) - d(f) / c   (R(eb), R(ea)): w(ea) - d(f) / c
a_4 = {
    ('R1', 'R0'): 2 - 2 / c,
    ('R2', 'R0'): 2 - 3 / c,
    ('R3', 'R1'): 0 - 2 / c,
    ('R4', 'R1'): 0 - 1 / c,
    ('R4', 'R2'): 0 - 4 / c,
    ('R0', 'R3'): 0 - 0 / c,
    ('R0', 'R4'): 0 - 0 / c,
    
    ('R2', 'R5'): 2 - 5 / c
}

V = [
    *[f'r{i}' for i in range(Nv)],
    *[f'R{i}' for i in range(Ne)]
]
V_I = [v for v in V if v.startswith('r')]
V_C = [v for v in V if v.startswith('R')]
a = {**a_1, **a_2, **a_3, **a_4}
E = a.keys()


solver = MIDCSolver(Nv + Ne, Nv)

mapping = {
    **{f'r{i}': i for i in range(Nv)},
    **{f'R{i}': Nv + i for i in range(Ne)}
}
for (i, j), v in a.items():
    # print(f"{j} ({mapping[j]}) - {i} ({mapping[i]}) <= {v}")
    solver.add_constraint(mapping[j], mapping[i], v)

solution = solver.solve()

if not solution:
    print("无解")
else:
    print("找到可行解：")
    for node in V:
        print(f"x_{node} = {solution[mapping[node]]}")




# 扩展模型


# 求解，运行 WD 得到 D，在 D 上二分查找，使用 MIDCSolver 求解得到 r

