"""
    不严谨测试, 单在简单合并问题上并查集较 Python 12 下的 set 操作快 30% 左右;
    但五十万点下花费时间也就在一秒上下, 影响似乎不大;
    同时考虑并查集删除和全局情况查询实现上存在的麻烦;
    先用 set 操作实现, 后续可以考虑杂糅到一起.
"""

# import time

# N = 500000

# class SetManager:
#     def __init__(self):
#         self.sets = {}
#         self.set_id_counter = 0
    
#     def create_set(self):
#         set_id = self.set_id_counter
#         self.sets[set_id] = set()
#         self.set_id_counter += 1
#         return set_id
    
#     def add_node(self, node, set_id):
#         self.sets[set_id].add(node)
#         node.set_id = set_id
    
#     def remove_node(self, node):
#         set_id = node.set_id
#         self.sets[set_id].remove(node)
        
#         if not self.sets[set_id]:
#             del self.sets[set_id]
        
#         new_set_id = self.create_set()
#         self.add_node(node, new_set_id)
    
#     def merge_sets(self, set_id1, set_id2):
#         if set_id1 == set_id2:
#             return
        
#         for node in self.sets[set_id2]:
#             self.add_node(node, set_id1)
        
#         del self.sets[set_id2]
    
#     def are_in_same_set(self, node1, node2):
#         return node1.set_id == node2.set_id
    
#     def get_all_sets(self):
#         return {set_id: list(nodes) for set_id, nodes in self.sets.items()}


# class Node:
#     def __init__(self, name):
#         self.name = name
#         self.set_id = None
    
#     def __repr__(self):
#         return f"Node({self.name})"


# manager = SetManager()

# t = time.time()

# sets = [manager.create_set() for i in range(N)]

# nodes = [Node(str(i)) for i in range(N)]

# [manager.add_node(nodes[i], sets[i]) for i in range(N)]

# for i in range(N - 1):
#     manager.merge_sets(sets[0], sets[i + 1])

# for i in range(N - 1):
#     manager.remove_node(nodes[i + 1])
    
# # print(manager.get_all_sets())

# print("SetManager: ", time.time() - t)


""" ==================================================================================================== """


# class UnionFind:
#     def __init__(self):
#         self.parent = {}
#         self.rank = {}
#         self.node_sets = {}
    
#     def add_node(self, node):
#         if node not in self.parent:
#             self.parent[node] = node
#             self.rank[node] = 0
#             self.node_sets[node] = {node}
    
#     def find(self, node):
#         if self.parent[node] != node:
#             self.parent[node] = self.find(self.parent[node])
#         return self.parent[node]
    
#     def union(self, node1, node2):
#         root1 = self.find(node1)
#         root2 = self.find(node2)
        
#         if root1 != root2:
#             if self.rank[root1] > self.rank[root2]:
#                 self.parent[root2] = root1
#                 self.node_sets[root1].update(self.node_sets[root2])
#                 del self.node_sets[root2]
#             elif self.rank[root1] < self.rank[root2]:
#                 self.parent[root1] = root2
#                 self.node_sets[root2].update(self.node_sets[root1])
#                 del self.node_sets[root1]
#             else:
#                 self.parent[root2] = root1
#                 self.rank[root1] += 1
#                 self.node_sets[root1].update(self.node_sets[root2])
#                 del self.node_sets[root2]
    
#     def are_in_same_set(self, node1, node2):
#         return self.find(node1) == self.find(node2)
    
#     def remove_node(self, node):
#         root = self.find(node)
#         if node in self.node_sets[root]:
#             new_root = node
#             self.parent[new_root] = new_root
#             self.rank[new_root] = 0
#             self.node_sets[new_root] = {node}
#             self.node_sets[root].remove(node)
#             if not self.node_sets[root]:
#                 del self.node_sets[root]
    
#     def get_all_sets(self):
#         return {root: nodes for root, nodes in self.node_sets.items()}


# uf = UnionFind()

# t = time.time()

# # 创建集合 (无需)

# [uf.add_node(str(i)) for i in range(N)]

# # 加入集合 (无需)

# for i in range(N - 1):
#     uf.union("0", str(i + 1))

# for i in range(N - 1):
#     uf.remove_node(str(i + 1))
    
# # print(uf.get_all_sets())

# print("UnionFind: ", time.time() - t)


""" ==================================================================================================== """


# def use_dsu_node(uid: str = ""):
#     class DSUException(Exception): pass
    
#     def decorator(cls):
#         def __init__(self, *args, **kwargs):
#             self._dsu_father = self # 父节点初始化为自己
#             self._dsu_rank = 0  # 初始化秩为 0
#             self._dsu_uid = uid  # uid 不同的节点属不同空间, 不应被合并

#             if hasattr(cls, '__original_init__'): # 如有则调用原有 __init__
#                 cls.__original_init__(self, *args, **kwargs)

#         def root(self):
#             if self._dsu_father != self: # 路径压缩
#                 self._dsu_father = self._dsu_father.root()
#             return self._dsu_father

#         def merge(self, other):
#             if not hasattr(other, "_dsu_uid"):
#                 raise DSUException(f"Target node is not a DSU node")
#             if self._dsu_uid != other._dsu_uid:
#                 raise DSUException(f"Nodes with different uids should not be merged")
            
#             root_self = self.root()
#             root_other = other.root()

#             if root_self != root_other: # 不在同一个集合, 按秩合并
#                 if root_self._dsu_rank > root_other._dsu_rank:
#                     root_other._dsu_father = root_self
#                 elif root_self._dsu_rank < root_other._dsu_rank:
#                     root_self._dsu_father = root_other
#                 else:
#                     root_other._dsu_father = root_self
#                     root_self._dsu_rank += 1

#         if hasattr(cls, '__init__'): # 若原本定义了 __init__ 则保存起来
#             cls.__original_init__ = cls.__init__
        
#         cls.__init__ = __init__
#         cls.root = root
#         cls.merge = merge
        
#         return cls
    
#     return decorator


# @use_dsu_node("")
# class NodeDSU:
#     def __init__(self, name):
#         self.name = name


# t = time.time()

# # 创建集合 (无需)

# nodes = [NodeDSU(str(i)) for i in range(N)]

# # 加入集合 (无需)

# for i in range(N - 1):
#     nodes[i + 1].merge(nodes[0])

# # 移除
    
# # 打印集合情况

# print("DSU: ", time.time() - t)


""" ==================================================================================================== """


# def use_dsu_plus_node(uid: str = ""):
#     class DSUPlusException(Exception): pass
    
    
    
#     def decorator(cls):
#         def __init__(self, *args, **kwargs):
#             self._dsu_father = self # 父节点初始化为自己
#             self._dsu_rank = 0  # 初始化秩为 0
#             self._dsu_uid = uid  # uid 不同的节点属不同空间, 不应被合并

#             if hasattr(cls, '__original_init__'): # 如有则调用原有 __init__
#                 cls.__original_init__(self, *args, **kwargs)

#         def root(self):
#             if self._dsu_father != self: # 路径压缩
#                 self._dsu_father = self._dsu_father.root()
#             return self._dsu_father

#         def merge(self, other):
#             if not hasattr(other, "_dsu_uid"):
#                 raise DSUException(f"Target node is not a DSU node")
#             if self._dsu_uid != other._dsu_uid:
#                 raise DSUException(f"Nodes with different uids should not be merged")
            
#             root_self = self.root()
#             root_other = other.root()

#             if root_self != root_other: # 不在同一个集合, 按秩合并
#                 if root_self._dsu_rank > root_other._dsu_rank:
#                     root_other._dsu_father = root_self
#                 elif root_self._dsu_rank < root_other._dsu_rank:
#                     root_self._dsu_father = root_other
#                 else:
#                     root_other._dsu_father = root_self
#                     root_self._dsu_rank += 1

#         if hasattr(cls, '__init__'): # 若原本定义了 __init__ 则保存起来
#             cls.__original_init__ = cls.__init__
        
#         cls.__init__ = __init__
#         cls.root = root
#         cls.merge = merge
        
#         return cls
    
#     return decorator


""" ==================================================================================================== """


def use_setmgr_node(cls):
    class SetManagerException(Exception): pass
    
    class SetManager:
        def __init__(self):
            self.set_id_cnt = 0
            self.sets = {}
        
        def create_set(self) -> int: # 创建新集合
            new_id = self.set_id_cnt
            self.sets[new_id] = set()
            self.set_id_cnt += 1
            return new_id
        
        def get_set_by_id(self, set_id) -> set: # 按 id 获取集合引用
            res = self.sets.get(set_id, None)
            if res is None:
                raise SetManagerException(f"Set with ID {set_id} does not exist")
            return res
        
        def remove_set(self, set_id): # 删除集合
            # TODO 如何处理其内的节点, 例如 structure 中如果也存了 ports, 直接 del 会在那里残留引用
            #       ... 不过引用计数为零的话应该会自动释放吧
            pass
        
        def add_node_into(self, node, set_id): # 将节点加入指定集合
            if node._setmgr_mgr != self:
                raise SetManagerException(f"Nodes in different spaces should not be added")
            
            self.get_set_by_id(set_id).add(node)
            node._setmgr_set_id = set_id
        
        def separate_node(self, node): # 单点分离成集
            if node._setmgr_mgr != self:
                raise SetManagerException(f"Node is not in current space")
            
            if len(node.belongs()) <= 1: # 本就单独成集
                return
            
            node.belongs().remove(node) # 从所属集中删除该节点
            self.add_node_into(node, self.create_set()) # 创建新集合并加入
        
        def merge_set(self, set_id_1, set_id_2):
            if set_id_1 == set_id_2:
                return
            
            if len(self.get_set_by_id(set_id_1)) < len(self.get_set_by_id(set_id_2)): # 小的并入大的
                set_id_1, set_id_2 = set_id_2, set_id_1
            
            for node in self.sets[set_id_2]:
                # TODO 集合大时效率很低, 但又要保证每个节点的 _setmgr_set_id 被修改. 除非查询所属集合专门再用并查集实现?
                #       ... 正常来说电路网表中直接相连的节点数应该不会太庞大, 甚至可以说较少, 或许暂时可以不管.
                self.add_node_into(node, set_id_1)
            
            del self.sets[set_id_2] # 该集合中为节点的引用, 删除集合保证节点不事二主, 不影响已经转移的节点
        
        def merge_set_by_nodes(self, node_1, node_2):
            if node_1._setmgr_mgr != self or node_2._setmgr_mgr != self:
                raise SetManagerException(f"Nodes out of current space should not be merged")

            self.merge_set(node_1._setmgr_set_id, node_2._setmgr_set_id)
    
    mgr = SetManager()
    
    def __init__(self, *args, **kwargs):
        self._setmgr_mgr.add_node_into(self, self._setmgr_mgr.create_set()) # 创建新集合并加入 (其中更新了 _setmgr_set_id)

        if hasattr(cls, '__original_init__'): # 如有则调用原有 __init__
            cls.__original_init__(self, *args, **kwargs)
    
    def belongs(self) -> set:
        return self._setmgr_mgr.get_set_by_id(self._setmgr_set_id)
    
    def merge(self, other_node):
        self._setmgr_mgr.merge_set_by_nodes(other_node, self)
    
    def separate(self):
        self._setmgr_mgr.separate_node(self)

    if hasattr(cls, '__init__'): # 若原本定义了 __init__ 则保存起来
        cls.__original_init__ = cls.__init__
    
    cls.__init__ = __init__
    cls.belongs = belongs
    cls.merge = merge
    cls.separate = separate
    
    cls._setmgr_mgr = mgr # 所属空间的集合管理器索引, 存为类属性, 对象也可访问 TODO
    
    return cls


@use_setmgr_node
class Node:
    def __init__(self, name): self.name = name
    def __repr__(self): return f"Node({self.name})"

import time
N = 100000
mgr = Node._setmgr_mgr

nodes = [Node(str(i)) for i in range(N)]

t = time.time()

for i in range(N - 1):
    # if i % 50 == 0:
    #     print(i)
    nodes[i].merge(nodes[i + 1])

print(time.time() - t)

