import math
import heapq

class MILPSolver:
    def __init__(self, V, V_I, E, a):
        self.V = V          # 顶点集合
        self.V_I = V_I      # 整数顶点集合
        self.E = E          # 边集合 (i, j)
        self.a = a          # 边权重字典 {(i, j): a_ij}
        self.E_R = [(i, j) for (i, j) in self.E if j not in self.V_I]  # 实数边
        self.E_I = [(i, j) for (i, j) in self.E if j in self.V_I]      # 整数边

    def solve_m(self):
        r = {v: 0 for v in self.V}
        for i in range(len(self.V) - len(self.V_I)):
            for (i, j) in self.E_R:
                r[j] = min(r[j], r[i] + self.a[(i, j)])
        for i in range(len(self.V_I)):
            for (i, j) in self.E_I:
                r[j] = min(r[j], math.floor(r[i] + self.a[(i, j)]))
            for i in range(len(self.V) - len(self.V_I)):
                for (i, j) in self.E_R:
                    r[j] = min(r[j], r[i] + self.a[(i, j)])
        for (i, j) in self.E:
            if r[j] > r[i] + self.a[(i, j)]:
                return "Infeasible"
        return r

    def solve(self):
        # 1. 重加权（Reweighting）
        r = {v: 0 for v in self.V}
        # Bellman-Ford松弛实数边
        for _ in range(len(self.V) - len(self.V_I)):  # |V_R|次迭代
            for (i, j) in self.E_R:
                r[j] = min(r[j], r[i] + self.a[(i, j)])
        # 检查负权环
        for (i, j) in self.E_R:
            if r[j] > r[i] + self.a[(i, j)]:
                return "Infeasible"
        # 计算新权重b_ij
        b = {(i, j): self.a[(i, j)] + r[i] - r[j] for (i, j) in self.E}
        # for i in self.V:
        #     for j in self.V:
        #         if (i, j) in self.E:
        #             print(r[j] - r[i] <= self.a[(i, j)])
        
        # 2. 处理整数边和实数边
        # y = {v: 1000000 for v in self.V}
        # y[list(y.keys())[0]] = 0
        y = {v: 0 for v in self.V}
        
        for _ in range(len(self.V_I)):
            # 松弛整数边，并对整数顶点强制取整
            for (i, j) in self.E_I:
                y[j] = min(y[j], math.floor(y[i] + b[(i, j)])) # T13
            
            # 使用Dijkstra算法松弛实数边
            # 初始化优先队列 # T14
            # Q = []
            # for v in self.V:
            #     if v not in self.V_I:
            #         heapq.heappush(Q, (y[v], v))
            Q = [(y[v], v) for v in self.V]
            heapq.heapify(Q)
            
            visited = set()
            while Q:
                y_i, i = heapq.heappop(Q)
                # if i in visited:
                #     continue
                visited.add(i)
                # 遍历所有以i为起点的实数边
                for (i_, j) in self.E_R:
                    if i_ == i:
                        if y[j] > y[i] + b[(i, j)]:
                            y[j] = y[i] + b[(i, j)]
                            heapq.heappush(Q, (y[j], j))
        
        # 3. 验证并转换结果
        for (i, j) in self.E_I:
            if y[j] > y[i] + b[(i, j)]:
                print(y[j], y[i], b[(i, j)])
                return "Infeasible"
        # 转换为原始变量x
        x = {v: y[v] + r[v] for v in self.V}
        return x


# 定义测试案例（用户提供的示例）
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



import pulp

# 定义问题
prob = pulp.LpProblem("MILP_Example", pulp.LpMinimize)

# 定义变量
r = {vi: pulp.LpVariable(vi, lowBound = 0, cat = "Integer") for vi in V_I}
R = {vc: pulp.LpVariable(vc) for vc in V_C}
V = {**r, **R}  # 合并变量字典

# 目标函数
prob += 0 # sum(r.values()) # , "Objective"

# 约束条件
for i in range(1):
    for (xi, xj), aij in a.items():
        Xi = V[xi]
        Xj = V[xj]
        prob += Xj - Xi <= aij + i # , f"Constraint_{xi}_{xj}"
    
# prob += 2*x + y >= 10, "Constraint1"
# prob += x + 2*y >= 12, "Constraint2"

# 求解
prob.solve()

# 输出结果
print(f"Status: {pulp.LpStatus[prob.status]}")
print([rv.value() for rv in r.values()])
print(
    round((V['R0'].value() - V['r0'].value()) * c),
    round((V['R1'].value() - V['r1'].value()) * c),
    round((V['R2'].value() - V['r1'].value()) * c),
    round((V['R3'].value() - V['r2'].value()) * c),
    round((V['R4'].value() - V['r2'].value()) * c)
)



# 创建求解器实例
solver = MILPSolver(V, V_I, E, a)
solution = solver.solve()
# solution = solver.solve_m()

# 打印结果
if solution == "Infeasible":
    print("问题无解")
else:
    print("找到可行解：")
    for node in V:
        print(f"x_{node} = {solution[node]}")
    
    # 验证所有约束
    valid = True
    for (i, j) in E:
        if solution[j] - solution[i] > a[(i, j)]:
            print(f"违反约束: x_{j} - x_{i} = {solution[j] - solution[i]} > {a[(i, j)]}")
            valid = False
    for node in V_I:
        if not isinstance(solution[node], int):
            print(f"违反整数约束: x_{node} = {solution[node]} 不是整数")
            valid = False
    if valid:
        print("所有约束均满足！")

