from .signal import *
# from .operator import *

import hashlib


""" Exceptions """
class DiagramTypeException(Exception): pass
class DiagramInstantiationException(Exception): pass


""" Utils """
class DiagramStructure: # TODO 算子或也应该在这里定义
    def __init__(self):
        pass # TODO
        # 外 port
        # 内部


""" Metatypes """
class DiagramType(type):
    PARAMETER_INSTANTIATED_ATTRNAME = "parameter_instantiated"
    STRUCTURE_ATTRNAME = "structure"
    DETERMINED_ATTRNAME = "determined"
    
    type_pool = {} # 模块查重 (TODO: 哈希重复是否要再检查一下参数是否相同)
    
    def __new__(cls, name, bases, attr): # `cls` here is the metaclass itself (DiagramType)
        """
            一般会在两种情况下被调用:
                (1.) 使用 class 定义 Diagram 等类时, 行为上即无参构建结构模板.
                (2.) 使用 Diagram[...] 等在 __getitem__ 中带参创建新类时, 行为上需要注意, 这种情况的调用是多余的:
                    __getitem__ 将在 attr 中传入 `<PARAMETER_INSTANTIATED_ATTRNAME>: True` 属性,
                    若该属性为 False 或不存在则为情况 (1.), 正常处理;
                    否则为情况 (2.), 需跳过已经在 __getitem__ 中完成且结果已经传入 attr 中的构建过程.
        """
        new_cls = super().__new__(cls, name, bases, attr) # 先创建类, 因为 setup() 可能未在 attr 中显式重写
        
        if not attr.get(DiagramType.PARAMETER_INSTANTIATED_ATTRNAME, False): # 非带参派生模板, 按 (1.) 行为处理
            new_structure, new_determined = None, False
            try:
                new_structure = new_cls.setup() # 无参生成结构
                new_determined = True # TODO 类型推导后确认是否 determined, 并给 new_cls.determined 赋值, 暂时给 True TODO
            except Exception as e:
                pass # 默认值如前, 若 setup() 缺省参数会抛出异常或类型推导出错, 则结构留空, determined 直接置 False, 等待后续带参构建
            setattr(new_cls, DiagramType.STRUCTURE_ATTRNAME, new_structure)
            setattr(new_cls, DiagramType.DETERMINED_ATTRNAME, new_determined)

        return new_cls
    
    def __getitem__(cls: 'Diagram', args: tuple): # `cls` here is the generated class
        """
            在已有 Diagram 类基础上通过中括号传入参数以构建新的类并返回, 行为上即带参构建结构模板.
                    ... 使用 DiagramType 构建新类时会再调用 __new__, 在 __new__ 中会依据是否有 `<PARAMETER_INSTANTIATED_ATTRNAME>: True` 判断是否已经带参创建.
        """
        new_name = f"{cls.__name__}_TODO" # 类名与参数构建新名 TODO
        new_cls = DiagramType(
            new_name,
            (cls, ), # 继承无参模板的属性和方法, 主要是 setup 以及祖传的 deduction 和 __init__
            {
                DiagramType.PARAMETER_INSTANTIATED_ATTRNAME: True,
                DiagramType.STRUCTURE_ATTRNAME: cls.setup(args),
                DiagramType.DETERMINED_ATTRNAME: True # TODO 类型推导后确认是否 determined, 暂时给 True TODO
            } # 这里如果出问题, 例如参数错误, 直接抛出异常不再捕获
        )
        return new_cls


""" Types """
class Diagram(metaclass = DiagramType):
    is_operator = False # 是否是基本算子 (即无内部结构)
    parameter_instantiated = False # 见 DiagramType.__new__ 的注释
    
    structure = None
    determined = False # 是否定型 (即是否可例化), 理论上可以通过类型推导得出, 此处特殊空结构, 为 False
    
    def __init__(self):
        if not self.determined:
            raise DiagramInstantiationException(f"Undetermined diagram \'{type(self).__name__}\' cannot be instantiated.") # TODO type(self)?
        pass # TODO 统一例化过程, 模板到实例, 继承者不可更改
    
    @classmethod
    def deduction(cls): # TODO 类型推导
        print('deduction.')
        pass
        # return TODO
    
    @staticmethod
    def setup(args: tuple = ()) -> DiagramStructure: # 模板结构生成, 可能含参, 此处为空结构无参, 继承者须覆写
        return DiagramStructure()


""" Derivatives """
class Addition(Diagram): # 带参 Diagram 示例, 整数加法
    @staticmethod
    def setup(args) -> DiagramStructure:
        # 类型检查
        
        
        return DiagramStructure()


"""
    关于元类的一系列试验:
    
    (1.) 使用 class 带 metaclass 参数创建类
        创建类时带上 metaclass = DiagramType 则会调用 __new__ (__new__ 是 type 的方法, DiagramType 继承了 type).
                ... TODO 也就是说不加 metaclass, 默认的就是 metaclass = type ?
            cls 为 __new__ 所在的元类本身;
            name 为正在创建的类的名称;
            bases 为正在创建的类的父类 (tuple 表示);
            attr 为正在创建的类具有的属性.
        例如:
            class DiagramType(type):
                def __new__(cls, name, bases, attr):
                    print('DiagramType.__new__', cls, name, bases, attr)
                    return super().__new__(cls, name, bases, attr)
            
            class Diagram(metaclass = DiagramType):
                a = 1
                def f(x):
                    return x
        该 Diagram 类的创建会调用 DiagramType 的 __new__ 方法, 传入的四个参数分别为:
            <class '__main__.DiagramType'>
            'Diagram'
            tuple()
            {'__module__': '__main__', '__qualname__': 'Diagram', 'a': 1, 'f': <function Diagram.f at 0x000001F1005C59E0>}
    
    (2.) 使用 class 带继承属性创建 (1.) 中所建类的子类
        元类如同被继承一般, 使得所建子类也会调用其 __new__ 方法.
            创建的子类由继承关系, 会得到父类的属性;
            但调用 __new__ 时传入的 attr 参数不会包含继承属性.
        例如:
            class TestClass(Diagram):
                a = 2
        调用 __new__ 时传入的四个参数为:
            <class '__main__.DiagramType'>
            'TestClass'
            (<class '__main__.Diagram'>, )
            {'__module__': '__main__', '__qualname__': 'TestClass', 'a': 2}
    
    (3.) 使用 type 创建 (1.) 中所建类的子类
        例如:
            TestClass = type('TestClass', (Diagram, ), {'a': 2})
        该 TestClass 类创建时调用 __new__ 方法传入的四个参数为:
            <class '__main__.DiagramType'>
            'TestClass'
            (<class '__main__.Diagram'>, )
            {'a': 2}
        由于继承 Diagram, T.a 和 T.f(x) 都还在, 而 T.a 的值被 attr 覆盖为 2, 可见此处 attr 代表的是子类新添加的属性, 不包括父类的属性.
                ... 父类的情况已包含在 bases 中, 再包含在 attr 中显得冗余.
        同时, 与 (2.) 比对可以发现 attr 中缺失了 '__module__': '__main__', '__qualname__': 'TestClass' 两个属性, 但创建所得 TestClass 还是具有这两个属性的.
                ... TODO 或为类的必要属性, 会自动加上? 例如 __module__ 概与文件、运行入口有关?
        * 注意, 如果使用 type 创建, 不传入父类 (即 bases 为空) 则不会调用到 DiagramType 的 __new__. (该结论后续见 (4.))
    
    (4.) 使用 DiagramType 创建 (1.) 中所建类的子类
        正常情况下创建类即使用 type 进行创建, 本质上调用的就是 type.__new__, 所以我们可以直接使用我们的元类 (例如前述 DiagramType) 来创建新类.
        例如:
            TestClass = DiagramType('TestClass', (Diagram, ), {'a': 3})
        传入的四个参数为:
            <class '__main__.DiagramType'>
            'TestClass'
            (<class '__main__.Diagram'>, )
            {'a': 3}
        可见和 (3.) 的情况基本是一致的, 区别在于 (3.) 如果不继承 Diagram 这样带又重写过 __new__ 方法的元类, 则进入的还是 type.__new__ 而非 DiagramType.__new__,
        而这里的情况则是不管继承不继承, 都会进入 DiagramType.__new__.
        * 注意, 这里既直接调用 DiagramType, 又注明了父类为 Diagram, 但总体只会调用一次 __new__.
        接下来在 (5.) 中尝试使用 DiagramType 创建并继承另一个声明非 DiagramType 元类的类。
    
    (5.) 使用 DiagramType 创建另一个使用不同元类的类的子类
        例如, 新定义:
            class OtherType(type):
                def __new__(cls, name, bases, attr):
                    print('OtherType.__new__', name, bases, attr)
                    return super().__new__(cls, name, bases, attr)

            class Other(metaclass = OtherType):
                b = 5
                def g(x):
                    return 2 * x
        再使用 DiagramType 创建继承自 Other 的类:
            TestClass = DiagramType('TestClass', (Other, ), {'a': 4})
        就可以看到:
            TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
        非常舒服地报错了, 子类的元类必须和其所有父类的元类都相同或为其子类, 不存在歧义的问题.
    
    (6.) 在元类中定义属性
        TODO
    
    (7.) 关于 __new__
        TODO
"""