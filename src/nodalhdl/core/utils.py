def class_attribute_isolator(attrs: list[str]):
    def decorator(cls):
        """
            类装饰器 class_attribute_isolator, 置于类前表明该类的部分类属性需要隔离 (由隔离列表 attrs 规定), 即:
                (1.) 若对象 obj 自己不包含名为 <x> 的属性, 而用户希望访问类属性 <x>, 则建议其使用 `type(obj).<x>` 或 `obj.__class__.<x>`.
                (2.) 若对象 obj 恰好拥有名为 <x> 的属性, 则 obj.<x> 访问的就是 obj 对象自身的 <x> 属性, 覆盖对类属性 <x> 的访问.
            其实现为覆写 __getattribute__ 方法, 访问时检查 name 是否在 attrs 中;
            同时, self.__dict__ 中只包含对象本身的属性, 不包含类属性, 故可以用于检查对象本身是否覆盖了该属性.
        """
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


def use_dsu_node(uid: str = ""):
    def decorator(cls):
        """
            类装饰器 use_dsu_node, 置于类前将其实例作为并查集维护的节点.
            为节点实例添加 __dsu_father, __dsu_rank, __dsu_uid 属性以及 root(), merge(other) 方法, 加入并查集维护.
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

# print(n1.root().name)               # A
# n1.merge(n2)
# print(n1.root().name)               # A
# n3.merge(n4)
# n4.merge(n5)
# print(n5.root().name)               # C
# n2.merge(n4)
# print(n3.root().name)               # A
# m1.merge(m2)
# print(m2.root().name)               # X

