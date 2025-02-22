"""
    不严谨测试, 单在简单合并问题上并查集较 Python 12 下的 set 操作快 30% 左右;
    但五十万点下花费时间也就在一秒上下, 影响似乎不大;
    同时考虑并查集删除和全局情况查询实现上存在的麻烦;
    先用 set 操作实现.
"""

import time

N = 500000


class SetManager:
    def __init__(self):
        self.sets = {}
        self.set_id_counter = 0
    
    def create_set(self):
        set_id = self.set_id_counter
        self.sets[set_id] = set()
        self.set_id_counter += 1
        return set_id
    
    def add_node(self, node, set_id):
        self.sets[set_id].add(node)
        node.set_id = set_id
    
    def remove_node(self, node):
        set_id = node.set_id
        self.sets[set_id].remove(node)
        
        if not self.sets[set_id]:
            del self.sets[set_id]
        
        new_set_id = self.create_set()
        self.add_node(node, new_set_id)
    
    def merge_sets(self, set_id1, set_id2):
        if set_id1 == set_id2:
            return
        
        for node in self.sets[set_id2]:
            self.add_node(node, set_id1)
        
        del self.sets[set_id2]
    
    def are_in_same_set(self, node1, node2):
        return node1.set_id == node2.set_id
    
    def get_all_sets(self):
        return {set_id: list(nodes) for set_id, nodes in self.sets.items()}


class Node:
    def __init__(self, name):
        self.name = name
        self.set_id = None
    
    def __repr__(self):
        return f"Node({self.name})"


manager = SetManager()

t = time.time()

sets = [manager.create_set() for i in range(N)]

nodes = [Node(str(i)) for i in range(N)]

[manager.add_node(nodes[i], sets[i]) for i in range(N)]

for i in range(N - 1):
    manager.merge_sets(sets[0], sets[i + 1])

# for i in range(N - 1):
#     manager.remove_node(nodes[i + 1])
    
# print(manager.get_all_sets())

print(time.time() - t)


""" ===== """


def use_dsu_node(uid: str = ""):
    class DSUException(Exception): pass
    
    def decorator(cls):
        def __init__(self, *args, **kwargs):
            self.__dsu_father = self # 父节点初始化为自己
            self.__dsu_rank = 0  # 初始化秩为 0
            self.__dsu_uid = uid  # uid 不同的节点属不同空间, 不应被合并

            if hasattr(cls, '__original_init__'): # 如有则调用原有 __init__
                cls.__original_init__(self, *args, **kwargs)

        def root(self):
            if self.__dsu_father != self: # 路径压缩
                self.__dsu_father = self.__dsu_father.root()
            return self.__dsu_father

        def merge(self, other):
            if not hasattr(other, "__dsu_uid"):
                raise DSUException(f"Target node is not a DSU node")
            if self.__dsu_uid != other.__dsu_uid:
                raise DSUException(f"Nodes with different uids should not be merged")
            
            root_self = self.root()
            root_other = other.root()

            if root_self != root_other: # 不在同一个集合, 按秩合并
                if root_self.__dsu_rank > root_other.__dsu_rank:
                    root_other.__dsu_father = root_self
                elif root_self.__dsu_rank < root_other.__dsu_rank:
                    root_self.__dsu_father = root_other
                else:
                    root_other.__dsu_father = root_self
                    root_self.__dsu_rank += 1

        if hasattr(cls, '__init__'): # 若原本定义了 __init__ 则保存起来
            cls.__original_init__ = cls.__init__
        
        cls.__init__ = __init__
        cls.root = root
        cls.merge = merge
        
        return cls
    
    return decorator


@use_dsu_node("")
class NodeDSU:
    def __init__(self, name):
        self.name = name


t = time.time()

# 创建集合 (无需)

nodes = [NodeDSU(str(i)) for i in range(N)]

# 加入集合 (无需)

for i in range(N - 1):
    nodes[i + 1].merge(nodes[0])

# 移除
    
# 打印集合情况

print(time.time() - t)

