def class_attribute_isolator(attrs: list[str]):
    """
        类装饰器 class_attribute_isolator, 置于类前表明该类的部分类属性需要隔离 (由隔离列表 attrs 规定), 即:
            (1.) 若对象 obj 自己不包含名为 <x> 的属性, 而用户希望访问类属性 <x>, 则建议其使用 `type(obj).<x>` 或 `obj.__class__.<x>`.
            (2.) 若对象 obj 恰好拥有名为 <x> 的属性, 则 obj.<x> 访问的就是 obj 对象自身的 <x> 属性, 覆盖对类属性 <x> 的访问.
        其实现为覆写 __getattribute__ 方法, 访问时检查 name 是否在 attrs 中;
        同时, self.__dict__ 中只包含对象本身的属性, 不包含类属性, 故可以用于检查对象本身是否覆盖了该属性.
    """
    def decorator(cls):
        def new_getattribute(self, name):
            if name in attrs and name not in self.__dict__.keys(): # 访问的属性名在隔离列表中, 且对象自己不包含该属性
                raise AttributeError(f"\'type(object).{name}\' or \'object.__class__.{name}\' is recommended if you want to access the class attribute \'{name}\'")
            return super(cls, self).__getattribute__(name) # TODO
        
        cls.__getattribute__ = new_getattribute
        
        return cls
    
    return decorator


def use_dict_object(cls):
    """
        类装饰器 use_dict_object, 置于类前将为其添加 __apply_dict(self, d: dict) 方法.
        使用该方法可将字典 d 的结构 (用方括号引用) 转为对象结构 (用点号引用) 置于实例中.
        示例:
            @use_dict_object
            class Test:
                def __init__(self):
                    self.test = 1
            
            d = {
                "a": 1,
                "b": 2,
                "c": {
                    "d": "x",
                    "e": [5, 6],
                    "f": {
                        "g": 1.2,
                        "h": None
                    }
                }
            }
            
            o = Test()
            o.__apply_dict(d)
            
            print(o.__dict__)                       # {'test': 1, 'a': 1, 'b': 2, 'c': <...DictObject object at ...>}
            print(o.a)                              # 1
            print(o.c.d)                            # x
            o.a = 3
            print(o.a)                              # 3
    """
    class DictObject:
        def __init__(self, d: dict):
            for key, value in d.items():
                if isinstance(value, dict):
                    setattr(self, key, DictObject(value))
                else:
                    setattr(self, key, value)
    
    def __apply_dict(self, d: dict):
        self.__dict__.update(DictObject(d).__dict__)
    
    cls.__apply_dict = __apply_dict
    
    return cls


def use_dsu_node(uid: str):
    """
        类装饰器 use_dsu_node, 置于类前将其实例作为并查集维护的节点.
        为节点实例添加 _dsu_father, _dsu_rank, _dsu_uid 属性以及 root(), merge(other) 方法, 加入并查集维护.
        示例:
            @use_dsu_node("A")
            class NodeA:
                def __init__(self, name):
                    self.name = name

            @use_dsu_node("B")
            class NodeB:
                def __init__(self, name):
                    self.name = name

            n1, n2, n3, n4, n5 = NodeA("A"), NodeA("B"), NodeA("C"), NodeA("D"), NodeA("E")
            m1, m2 = NodeB("X"), NodeB("Y")

            print(n1.root().name)               # A
            n1.merge(n2)
            print(n1.root().name)               # A
            n3.merge(n4)
            n4.merge(n5)
            print(n5.root().name)               # C
            n2.merge(n4)
            print(n3.root().name)               # A
            m1.merge(m2)
            print(m2.root().name)               # X
            m1.merge(n1)                        # DSUException: Nodes with different uids should not be merged
    """
    class DSUException(Exception): pass
    
    def decorator(cls):
        def __init__(self, *args, **kwargs):
            self._dsu_father = self # 父节点初始化为自己
            self._dsu_rank = 0  # 初始化秩为 0
            self._dsu_uid = uid  # uid 不同的节点属不同空间, 不应被合并

            if hasattr(cls, '__original_init__'): # 如有则调用原有 __init__
                cls.__original_init__(self, *args, **kwargs)

        def root(self):
            if self._dsu_father != self: # 路径压缩
                self._dsu_father = self._dsu_father.root()
            return self._dsu_father

        def merge(self, other):
            if not hasattr(other, "_dsu_uid"):
                raise DSUException(f"Target node is not a DSU node")
            if self._dsu_uid != other._dsu_uid:
                raise DSUException(f"Nodes with different uids should not be merged")
            
            root_self = self.root()
            root_other = other.root()

            if root_self != root_other: # 不在同一个集合, 按秩合并
                if root_self._dsu_rank > root_other._dsu_rank:
                    root_other._dsu_father = root_self
                elif root_self._dsu_rank < root_other._dsu_rank:
                    root_self._dsu_father = root_other
                else:
                    root_other._dsu_father = root_self
                    root_self._dsu_rank += 1

        if hasattr(cls, '__init__'): # 若原本定义了 __init__ 则保存起来
            cls.__original_init__ = cls.__init__
        
        cls.__init__ = __init__
        cls.root = root
        cls.merge = merge
        
        return cls
    
    return decorator


def use_setmgr_node(cls):
    """
        类装饰器 use_setmgr_node, 置于类前将其实例作为集合管理器维护的节点.
        支持集合合并, 单点分离, 集合内容查询等.
        示例:
            @use_setmgr_node
            class NodeA:
                def __init__(self, name): self.name = name
                def __repr__(self): return f"Node({self.name})"

            @use_setmgr_node
            class NodeB:
                def __init__(self, name): self.name = name
                def __repr__(self): return f"Node({self.name})"

            n1, n2, n3, n4, n5 = NodeA("A"), NodeA("B"), NodeA("C"), NodeA("D"), NodeA("E")
            m1, m2 = NodeB("X"), NodeB("Y")

            mgr1 = n1._setmgr_mgr
            print(mgr1.sets)                    # {0: {Node(A)}, 1: {Node(B)}, 2: {Node(C)}, 3: {Node(D)}, 4: {Node(E)}}
            n1.merge(n2)
            print(mgr1.sets)                    # {1: {Node(A), Node(B)}, 2: {Node(C)}, 3: {Node(D)}, 4: {Node(E)}}
            n3.merge(n4)
            n4.merge(n5)
            print(mgr1.sets)                    # {1: {Node(A), Node(B)}, 4: {Node(C), Node(D), Node(E)}}
            n4.merge(n2)
            print(mgr1.sets)                    # {1: {Node(B), Node(C), Node(A), Node(D), Node(E)}}
            n3.separate()
            n1.separate()
            print(mgr1.sets)                    # {1: {Node(B), Node(D), Node(E)}, 5: {Node(C)}, 6: {Node(A)}}
            n1.merge(n3)
            print(mgr1.sets)                    # {1: {Node(B), Node(D), Node(E)}, 5: {Node(C), Node(A)}}

            mgr2 = m1._setmgr_mgr
            m1.merge(m2)
            print(mgr2.sets)                    # {1: {Node(X), Node(Y)}}
            
            m1.merge(n3)                        # SetManagerException: Nodes out of current space should not be merged
    """
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
            
            for node in self.sets[set_id_2]: # TODO 集合大时效率很低, 但又要保证每个节点的 _setmgr_set_id 被修改. 除非查询所属集合专门再用并查集实现?
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
N = 10000
mgr = Node._setmgr_mgr

nodes = [Node(str(i)) for i in range(N)]

t = time.time()

for i in range(N - 1):
    if i % 50 == 0:
        print(i)
    nodes[i].merge(nodes[i + 1])

print(time.time() - t)

