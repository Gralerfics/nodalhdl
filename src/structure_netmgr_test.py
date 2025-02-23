from nodalhdl.core.diagram import Structure

s1 = Structure()
n1, n2, n3, n4, n5 = [s1.netmgr.create_node(name, None) for name in ['A', 'B', 'C', 'D', 'E']]
print(s1.netmgr.nets)
n1.merge(n2)
print(s1.netmgr.nets)
n3.merge(n4)
n4.merge(n5)
print(s1.netmgr.nets)
n2.merge(n4)
print(s1.netmgr.nets)
n3.separate()
n5.separate()
print(s1.netmgr.nets)
n3.merge(n5)
print(s1.netmgr.nets)
# s1.netmgr.remove_net(n3.locates())
# print(s1.netmgr.nets)

s2 = Structure()
m1, m2, m3, m4, m5 = [s2.netmgr.create_node(name, None) for name in ['a', 'b', 'c', 'd', 'e']]
print(s2.netmgr.nets)
s1.netmgr.import_mgr(s2.netmgr)
print(s1.netmgr.nets)

"""
{{E}, {B}, {C}, {A}, {D}}
{{E}, {B, A}, {C}, {D}}
{{B, A}, {C, E, D}}
{{C, B, D, A, E}}
{{E}, {B, D, A}, {C}}
{{C, E}, {B, D, A}}
{{a}, {b}, {c}, {d}, {e}}
{{C, E}, {a}, {d}, {b}, {B, D, A}, {e}, {c}}
"""