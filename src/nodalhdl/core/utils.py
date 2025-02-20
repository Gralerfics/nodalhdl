def class_attribute_isolator(attrs: list[str]):
    def decorator(cls):
        """
            类装饰器 attribute_isolator, 置于类前表明该类的部分类属性需要隔离 (由隔离列表 attrs 规定), 即:
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

