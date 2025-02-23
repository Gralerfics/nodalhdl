from nodalhdl.core.diagram import StructureNet, StructureNode


n = [StructureNode(name, None) for name in ["A", "B", "C", "D", "E"]]
m = [StructureNode(name, None) for name in ["a", "b", "c", "d", "e"]]

n[0].merge(n[1])
print({n[i].located_net for i in range(5)})
n[2].merge(n[3])
n[3].merge(n[4])
print({n[i].located_net for i in range(5)})
n[0].merge(n[4])
print({n[i].located_net for i in range(5)})
n[2].separate()
n[0].separate()
print({n[i].located_net for i in range(5)})
n[2].merge(n[0])
print({n[i].located_net for i in range(5)})

m[2].merge(m[4])
print({n[i].located_net for i in range(5)} | {m[i].located_net for i in range(5)})
n[3].merge(m[2])
print({n[i].located_net for i in range(5)} | {m[i].located_net for i in range(5)})
m[4].separate()
print({n[i].located_net for i in range(5)} | {m[i].located_net for i in range(5)})


"""
{{E}, {D}, {C}, {A, B}}
{{C, E, D}, {A, B}}
{{D, A, C, E, B}}
{{D, E, B}, {A}, {C}}
{{D, E, B}, {A, C}}
{{e, c}, {D, E, B}, {A, C}, {a}, {d}, {b}}
{{D, e, E, B, c}, {A, C}, {a}, {d}, {b}}
{{D, E, B, c}, {A, C}, {e}, {a}, {d}, {b}}
"""

