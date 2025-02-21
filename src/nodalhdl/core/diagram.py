from .signal import SignalType
from .utils import use_dict_object, use_dsu_node

import hashlib


""" Exceptions """
class DiagramTypeException(Exception): pass
class DiagramInstantiationException(Exception): pass


""" Diagram Type """
class DiagramType(type):
    diagram_type_pool = {} # 框图类型池, 去重
    
    def __new__(mcs, name: str, bases: tuple, attr: dict): # `mcs` here is the metaclass itself
        """
            创建新 Diagram 类型, 可能被调用的情况:
                (1.) 使用 class 继承 Diagram 创建子类.
                (2.) 使用中括号传递参数创建 Diagram 或其子类的衍生类.
                (3.) TODO 在衍生类基础上再加中括号传递参数.
                        ... 需要考虑该行为的物理意义, 无意义则应抛出异常, 可以在 __getitem__ 中判断是否已有参数 instantiation_arguments.
            最终都进入 __new__, 情况 (2.) 会在 attr 中带有参数 instantiation_arguments.
            创建类型:
                (1.) 构建新类名, 查重, 并创建新类. (注意 hash() 是不稳定的, 与运行时环境有关, 建议使用稳定的映射)
                        ... TODO 构建方案需改进, 目前直接使用 str(inst_args), 与子结构的 str 结果高度相关, 可能限制参数传递的多样性 (内部结构未体现在 str 结果中) 以及破坏哈希的全局稳定性 (str 中出现内存地址). 同时, 哈希重复是否要再检查一下参数是否严格相同, 以防止小概率的哈希冲突?
                (2.) 通过 setup 构建框图结构, 更新类属性 structure_template.
                (3.) 返回新类型.
            注:
                (1.) 框图类型具有唯一性, 在 diagram_type_pool 中进行去重.
                (2.) 框图类型一旦创建, 会且仅会在创建中执行一次 setup, structure_template 由此固定 (*).
                        ... TODO determined 以及 deduction 的所属改到 Structure 下, 是否需要在类型创建时也跑一下 deduction 给出一个最初的 determined 判断?
        """
        inst_args = attr.get("instantiation_arguments", ()) # 获取可能从 __getitem__ 传来的参数, 无则默认为空

        new_name = name
        if inst_args: # 若参数不为空则依据参数构建新名
            new_name = f"{name}_{hashlib.md5(str(inst_args).encode('utf-8')).hexdigest()}"
        
        if not new_name in mcs.diagram_type_pool.keys(): # 若尚未创建过
            new_cls = super().__new__(mcs, new_name, bases, attr) # 先创建类, setup() 可能未在子类中显式重写 (即未在 attr 中)
            setup_func = new_cls.setup
            
            try:
                new_cls.structure_template = setup_func(inst_args) # 生成结构
            except DiagramTypeException as e:
                if inst_args: # 有参数还出错, 说明是结构确实有误, 抛出原异常
                    raise
                new_cls.structure_template = None # 否则可能是 class 创建时空参构建导致的未定义行为, 结构留空, 待后续带参构建
            
            mcs.diagram_type_pool[new_name] = new_cls # 加入框图类型池

        return mcs.diagram_type_pool[new_name] # 从框图类型池中获取
    
    def __getitem__(cls, args: tuple): # `cls` here is the generated class
        """
            在已有 Diagram 类基础上通过中括号传入参数以构建新的类并返回.
            行为上是将 args 通过 attr 传入 __new__, 在其中统一处理.
        """
        return DiagramType(
            cls.__name__, # 传入无参框图名, 在 __new__ 中构建新名
            (cls, ), # 继承无参框图的属性和方法, 主要是 setup 和 deduction 等
            {"instantiation_arguments": args} # 传递参数交给 __new__ 创建
        )


""" Structure """
class Structure:
    """

    """
    determined = False
    
    @use_dsu_node("structure_ports")
    class Port:
        """
            并查集的元素单位, 并存有 (如果有的话) 所属 box
            TODO 是否需要修改并查集的结构, 使其可以做到快速地获取某 uid 的并查集下所有的集合和集合下的元素索引列表
                分析需求:
                    (1.) 类型推导: 可以通过遍历每个 port (需要存储推导范围内所有 port), 分别 find,
                         准备好多个类别 (Net) 各自对应一类的 root, find 到哪个就在哪个 Net 记录 fan_in, fan_out 和类型情况,
                         每次迭代需要更新各 net 的驱动情况, 并反映到每个相关的 port (net 中也要记录相连的 port, 以及合法情况下 fan_out 只应有一个, 可专门存),
                         如果 box 未 determined, 则还需要更新 box 的情况 (如果已经 determined 则其 in 和 out 都已经确定) ...
                    (2.) 内部展开: 主要是端口连接以及结构的问题, port 和 box 等列表需要添加被展开的结构的列表,
                         外 port 和内 port 需要消除 IOWrapper 后合并集合, 或最好能合并后直接删掉.
                    (3.) 自动寄存器插入: 每个 net 连接一个 fan_out (驱动源) 和多个 fan_in (被驱动端), 寄存器实际上就是插在 fan_out 路线上,
                         注意! 为了插入寄存器需要将 port 从 net 中分离! 需要删除操作. 或需放弃并查集 (虚点法太脏了);
                         寄存器插入还要考虑同步的问题, 需要从输入端一级一级赋予秩, 迭代可能有点慢.
        """
        # def __init__(self):
        #     self.__dsu_uid = "TODO" # TODO 每个 Structure 对象都应该隔离开, 所以按内存地址哈希隔开. (所以例化的话应该重建结构而不止分 inst_name?)
        
        pass # TODO
    
    @use_dict_object
    class Box:
        """
            TODO
            Box 是否考虑可加两种东西: 框图类型 (含 structure_template) 或直接加 Structure? 还是始终后者? 重点在于框图类型有没有存储的必要. 感觉还是要的.
                    ... 要不直接装 structure, 有需求的话放一个框图类型?
            将 port 作为对象属性添加进去, 方便引用
        """
        def __init__(self):
            self.diagram_type = None
        
        pass # TODO
    
    def __init__(self):
        self.inst_name = None # 例化后才分配
        
        pass # TODO
    
    def deduction(self):
        """
            TODO 可分结构的自动推导, 通过在集合结构上的迭代完成.
            注:
                (1.) 统一过程, 除了基本算子中须用户覆写.
                (2.) 类型推导仅在框图类型创建时, setup 之后, 执行一次.
                (3.) 传入一个 Structure, 结果 (修改) 直接存入其中 (带副作用的过程), 返回一个 bool 代表是否固化成功 (即 determined).
                (4.) TODO 如果迭代结束还存在 undetermined 类型的信号, 则说明该结构 undetermined, 不可被例化 (这里是否给了 A[x][y][z] 这样的结构一些存在的可能性? 分步固化?)
        """
        
        pass # TODO
        
    def add_port(self, signal_type: SignalType):
        pass # TODO
    
    def add_box(self, diagram_type: DiagramType):
        pass # TODO
    
    def connect(self, port_1: Port, port_2: Port):
        port_1.merge(port_2)
    
    def connects(self, ports: list[Port]):
        if len(ports) <= 1:
            return
        for idx, port in enumerate(ports):
            if idx != 0:
                ports[0].merge(port)


""" Diagram Base """
class Diagram(metaclass = DiagramType):
    is_operator = False # 是否是基本算子 (即无内部结构)
    structure_template = None # 结构模板
    
    def __init__(self):
        """
            TODO 例化, 与框图类型切割, 返回一个仅表示结构的 Structure 对象 (内部也这样递归下来, 框图类型中或许要有地方标注一下类型, 这里就全去掉).
                    ... 为 Structure 分配 inst_name.
            注:
                (1.) 统一过程, 继承者不可覆写.
        """
        
        pass # TODO
    
    @staticmethod
    def setup(args: tuple = ()) -> Structure:
        """
            框图结构生成, 可能含参, 此处为空, 继承者须覆写.
        """
        return None

# def operator(cls):
#     """
#         类装饰器 operator, 置于 Diagram 的子类前表明该类为基本算子 (即不可再分, 直接对应 VHDL).
#         其实现:
#             (1.) 增加或修改类属性 is_operator 为 True, 作为标记.
#             (2.) 要求必须覆写 deduction() 类型推导方法.
#                     ... TODO 有没有可能这个 deduction() 继承自其他基本算子, 不需要主动实现了?
#                     ... TODO 后或可从 VHDL 或结构的定义中提取出来.
#                 (2.1) 若用户实现了 deduction() 但忘记加 @staticmethod, 帮其加上, 不过这样是在破坏严谨性.
#                         ... TODO 在严格模式下不允许.
#             (3.) TODO 要求必须在结构中声明到 VHDL 的映射过程.
#     """
#     setattr(cls, "is_operator", True) # (1.)
    
#     if not any(isinstance(method, staticmethod) and method.__name__ == 'deduction' for method in cls.__dict__.values()): # (2.)
#         raise DiagramTypeException(f"Diagram type \'{cls.__name__}\' must implement staticmethod method \'deduction\'.")
    
#     # if __USE_STRICT_MODE:
#     #     if not any(isinstance(method, staticmethod) and method.__name__ == 'deduction' for method in cls.__dict__.values()): # (2.)
#     #         raise DiagramTypeException(f"Diagram type \'{cls.__name__}\' must implement staticmethod \'deduction\'.")
#     # else:
#     #     deduction_method = cls.__dict__.get('deduction', None) # (2.)
#     #     if not deduction_method:
#     #         raise DiagramTypeException(f"Diagram type \'{cls.__name__}\' must implement staticmethod \'deduction\'.")
        
#     #     if not isinstance(deduction_method, staticmethod): # (2.1)
#     #         cls.deduction = staticmethod(deduction_method)
    
#     return cls


""" Derivatives """ # TODO: 之后或许应该将此搬移到别处
from .signal import SignalType, UInt, SInt, Input, Output, Auto

# @operator
class Addition(Diagram): # 带参基本算子示例, 整数加法
    @staticmethod
    def setup(args):
        # 参数合法性检查
        if len(args) != 2 or not all([isinstance(arg, SignalType) and arg.determined for arg in args]):
            raise DiagramTypeException(f"Invalid argument(s) \'{args}\' for diagram type Addition[<op1_type (SignalType, determined)>, <op2_type (SignalType, determined)>].")
        op1_type, op2_type = args
        if not (op1_type.belongs(UInt) and op2_type.belongs(UInt) or op1_type.belongs(SInt) and op2_type.belongs(SInt)):
            raise DiagramTypeException(f"Only UInt + UInt or SInt + SInt is acceptable")
        
        # 创建结构
        res = Structure()
        
        # 声明 Ports, Input 和 Output, [] 内不确定可以写 Auto 或其他 Undetermined 类型, 供推导.
        #       ... 推导可能是通过内部输出导出 Output 的类型, 也可能是通过内部连接的模块得到 Input 的类型, 或其他, 不要局限.
        
        # TODO deduction 如何给出? 现在它在 structure 里了, 应该给个函数接口什么的吧.
        
        return res

class TestDiagram(Diagram): # 带参 Diagram 示例
    @staticmethod
    def setup(args):
        # TODO 参数合法性检查
        
        # 创建结构
        res = Structure()
        
        # TODO 声明 Ports, Input 和 Output, [] 内不确定可以写 Auto 或其他 Undetermined 类型, 供推导.
        #       ... 推导可能是通过内部输出导出 Output 的类型, 也可能是通过内部连接的模块得到 Input 的类型, 或其他, 不要局限.
        
        # TODO 加入 Box.
        #       ... 其内有 inner 属性, 存储 DiagramType (根据其 ports 得到外 Ports) 或 ExternalWorld (根据前面声明的 Ports 得到外 Ports).
        #       ... 外 Ports 类型最外层应为 IOWrapper, 例如如果是 Bundle, 应递归寻找到 IOWrapper 为止, 可能得到多个 Ports.
        
        # TODO 加入 Ports (无 IOWrapper) / 连接关系 (自动维护并查集).
        
        return res

