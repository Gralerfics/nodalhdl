def class_attribute_isolator(attrs): # list[str]
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


class ObjDict(dict):
    """
        直接继承 dict, 为其赋予属性访问的能力.
        示例:
            obj = ObjDict({"a": 1, "b": 2, "c": {"d": 3}})

            print(obj.a)        # 1
            print(obj.c)        # {'d': 3}
            print(obj.c.d)      # 3

            obj.a = 100
            print(obj.a)        # 100

            obj.e = 5
            print(obj.e)        # 5

            del obj.e
            print(obj.get('e', None))   # None

            print(obj.items())          # dict_items([('a', 100), ('b', 2), ('c', {'d': 3})])
    """
    def __init__(self, d: dict = {}):
        for key, value in d.items():
            if isinstance(value, dict):
                self[key] = ObjDict(value)
            else:
                self[key] = value
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"\'{self.__class__.__name__}\' object has no attribute \'{name}\'")

    def __setattr__(self, name, value):
        if name in self:
            self[name] = value
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            super().__delattr__(name)
    
    # def _collect_list(self, target_type, mode): # mode: keys, values, items
    #     def _collect(d):
    #         res = []
    #         for key, value in d.items():
    #             if isinstance(value, ObjDict):
    #                 res.extend(_collect(value))
    #             elif isinstance(value, target_type):
    #                 res.append((key, value) if mode == "items" else (key if mode == "keys" else value))
    #         return res
    #     return _collect(self)
    
    # def selective_keys(self, target_type): # 递归地将类型为 target_type 的键收集起来, 以下方法类似
    #     return self._collect_list(target_type, "keys")
    
    # def selective_values(self, target_type):
    #     return self._collect_list(target_type, "values")
    
    # def selective_items(self, target_type):
    #     return self._collect_list(target_type, "items")

