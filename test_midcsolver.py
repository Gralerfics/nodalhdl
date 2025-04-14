from nodalhdl.timing.retiming_circuitry import MIDCSolver


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
    print("No solution.")
else:
    for node in V:
        print(f"x_{node} = {solution[mapping[node]]}")

