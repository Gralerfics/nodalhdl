from .signal import SignalType
from .utils import DictObject

import hashlib


""" Diagram Type """
class DiagramTypeException(Exception): pass

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
class StructureNetManagerException(Exception): pass

class StructureNetManager:
    """
        管理 Net 的集合.
    """
    def __init__(self):
        self.nets = set()
    
    # TODO: 将其他 mgr 内容导入该 mgr 的方法 (内部展开操作需要该功能)
    # def
    
    def create_net(self, *args, **kwds): # 创建新 net 并返回引用
        new_net = StructureNet(*args, **kwds)
        self.nets.add(new_net)
        return new_net
    
    def remove_net(self, net: 'StructureNet'): # 删除 net TODO ?
        self.nets.remove(net)
        del net
    
    def create_node(self, *args, **kwds):
        new_node = StructureNode(*args, **kwds)
        new_node.netmgr = self # 引用所属的 net manager
        self.add_node_into_net(new_node, self.create_net()) # 创建新 net 并加入 (其中也更新了节点的 located_net)
        return new_node
    
    def add_node_into_net(self, node: 'StructureNode', net: 'StructureNet'): # 将节点加入指定集合
        if node.netmgr != self:
            raise StructureNetManagerException(f"Nodes that are not managed by this manager should not be operated")
        
        net.add(node)
        node.located_net = net
    
    def separate_node(self, node: 'StructureNode'): # 单点分离成集
        if node.netmgr != self:
            raise StructureNetManagerException(f"Nodes that are not managed by this manager should not be operated")
        
        if len(node.located_net) <= 1: # 本就单独成集
            return
        
        node.located_net.remove(node) # 从所属集中删除该节点
        self.add_node_into_net(node, self.create_net()) # 创建新集合并加入
    
    def merge_net(self, net_1: 'StructureNet', net_2: 'StructureNet'): # 合并两个 net
        if net_1 == net_2:
            return
        
        net_h, net_l = net_1, net_2
        if len(net_h) < len(net_l): # 确保是小的并入大的
            net_h, net_l = net_l, net_h
        
        for node in net_l.nodes:
            # TODO 集合大时效率低, 但又要保证每个节点的 located_net 被修改. 除非查询所属集合专门再用并查集实现? 成本可能更高.
            #       ... 正常来说电路网表中直接相连的节点数应该不会太庞大, 甚至可以说较少, 或许暂时可以不管.
            # TODO 如果 net 还存了别的信息这里也要注意处理.
            self.add_node_into_net(node, net_h)
        
        self.remove_net(net_l) # 该集合中为节点的引用, 删除集合保证节点不事二主, 不影响已经转移的节点
    
    def merge_net_by_nodes(self, node_1: 'StructureNode', node_2: 'StructureNode'):
        if node_1.netmgr != self or node_2.netmgr != self:
            raise StructureNetManagerException(f"Nodes that are not managed by this manager should not be operated")

        self.merge_net(node_1.located_net, node_2.located_net)

class StructureNet:
    """
        管理一组直接连接的 Nodes (Ports) 的集合称 Net.
        TODO 不直接使用 set 的原因是可能可以直接存储例如驱动信号等信息, 方便查询.
                ... 注意这种情况 merge_net 方法也要修改 TODO merge 的实现放到 net 这里来 TODO 这样也有问题, 为了方便合并 mgr, net 应独立于 mgr, 这样就难以合理调用 mgr.
    """
    def __init__(self):
        self.nodes = set()
    
    def __len__(self):
        return len(self.nodes)
    
    def __repr__(self):
        return f"Net({self.nodes})"
    
    def add(self, node):
        self.nodes.add(node)
    
    def remove(self, node):
        self.nodes.remove(node)

class StructureNode:
    """
        线路结点, 存有 (如果有的话) 所属 box (有的话应该是 IO Wrapped 的, IO 的 Nodes 又称 Ports).
        继承 SetManagerNodeBase, 被指定集合管理器管理.
        分析需求:
            (1.) 类型推导: 可以通过遍历每个 port (需要存储推导范围内所有 port), 分别 find,
                    准备好多个类别 (Net) 各自对应一类的 root, find 到哪个就在哪个 Net 记录 fan_in, fan_out 和类型情况,
                    每次迭代需要更新各 net 的驱动情况, 并反映到每个相关的 port (net 中也要记录相连的 port, 以及合法情况下 fan_out 只应有一个, 可专门存),
                    如果 box 未 determined, 则还需要更新 box 的情况 (如果已经 determined 则其 in 和 out 都已经确定) ...
            (2.) 内部展开: 主要是端口连接以及结构的问题, port 和 box 等列表需要添加被展开的结构的列表,
                    外 port 和内 port 需要消除 IOWrapper 后合并集合, 或最好能合并后直接删掉.
            (3.) 自动寄存器插入: 每个 net 连接一个 fan_out (驱动源) 和多个 fan_in (被驱动端), 寄存器实际上就是插在 fan_out 路线上,
                    注意! 为了插入寄存器需要将 port 从 net 中分离! 需要删除操作. 或需放弃并查集 (虚点法太脏了);
                    寄存器插入还要考虑同步的问题, 需要从输入端一级一级赋予秩, 迭代可能有点慢;
                    选取插入位置还需要进行时序分析, 估计中间模块的延迟.
    """
    def __init__(self, name: str, signal_type: SignalType):
        self.inst_name = None
        
        self.name = name
        self.signal_type = signal_type
    
    def __repr__(self):
        return f"Node({self.name})"
    
    def merge(self, other_node):
        self.netmgr.merge_net_by_nodes(other_node, self)
    
    def separate(self):
        self.netmgr.separate_node(self)

class StructureBox:
    """
        TODO
        Box 是否考虑可加两种东西: 框图类型 (含 structure_template) 或直接加 Structure? 还是始终后者? 重点在于框图类型有没有存储的必要. 感觉还是要的.
                ... 要不直接装 structure, 有需求的话放一个框图类型?
        将 port 作为对象属性添加进去, 方便引用
        
        Box 存在两种场景中:
            (1.) 作为框图类型下 structure_template (Structure) 中的 box, 存有 diagram_type.
            (2.) 作为框图类型例化后所得 structure 中的 box, 存有 structure.
        判断标准在于传入的 diagram_type 是否为 None, 为 None 则为场景 (2.).
        
        TODO 关于 ports
    """
    def __init__(self, name: str, diagram_type: DiagramType = None):
        self.inst_name = None
        
        self.name = name
        
        self.diagram_type = diagram_type
        self.structure = None
        if diagram_type is None: # (2.)
            self.structure = Structure()
    
    # def register_port(self, port: StructurePort):
    #     pass # TODO

class Structure:
    """
        TODO
        structure 不设 name, 有 name 的当是其下的 box, node/port 等.
                ... 此 name 不是 inst_name, 但 inst_name 参考该 name 而来.
        每个 structure 内建一个 netmgr 管理网表结构, net 游离态, 不依赖 netmgr, 故可以简单地合并多个 netmgr.
    """
    def __init__(self):
        self.inst_name = None # 例化后才分配
        self.determined = False # 推导后确定值
        
        self.netmgr = StructureNetManager()
        
        self.boxes = []
        # self.io_ports = {}
    
    def deduction(self):
        """
            TODO 可分结构的自动推导, 通过在集合结构上的迭代完成.
            注:
                (1.) TODO
                (?.) TODO 如果迭代结束还存在 undetermined 类型的信号, 则说明该结构 undetermined (这里是否给了 A[x][y][z] 这样的结构一些存在的可能性? 分步固化?)
        """
        
        pass # TODO
    
    def add_node(self, name: str, signal_type: SignalType):
        """
            signal_type 根据是否有 IO Wrapper 分类:
                (1.) 完全无 IO Wrapper, 为 node.
                (2.) 所有信号上溯皆有且仅有一个 IO Wrapper, 为 port.
                (3.) 不完整包裹的, 以及 IO Wrapper 存在嵌套的, 皆为非法.
                TODO: 检查分类的方法实现到 signal 中如何?
            对于 port, 递归寻找, 以 IO Wrapper 为最小单位构建需要添加的 ports.
        """
        
        pass # TODO
        
        return # TODO 返回 Port 对象或一个 DictObject (?)
    
    def add_box(self, name: str, diagram_type: DiagramType):
        box = StructureBox(name, diagram_type)
        
        pass # TODO 关于 ports 和 box.xxx 的处理
        
        return box
    
    def connect(self, port_1: StructureNode, port_2: StructureNode):
        port_1.merge(port_2)
    
    def connects(self, ports: list[StructureNode]):
        if len(ports) <= 1:
            return
        for idx, port in enumerate(ports):
            if idx != 0:
                ports[0].merge(port)


""" Diagram Base """
class DiagramInstantiationException(Exception): pass

class Diagram(metaclass = DiagramType):
    is_operator = False # 是否是基本算子 (即无内部结构)
    structure_template = None # 结构模板
    
    def __init__(self): # TODO 要不要覆写 __call__ 让类实例化行为变成调用 instantiate?
        raise DiagramTypeException(f"Use `.instantiate()` instead if you want to instantiate a Diagram")
    
    @classmethod
    def instantiate(cls) -> Structure:
        """
            TODO 例化, 与框图类型切割, 把 structure_template 深拷贝出来, 返回一个仅表示结构的 Structure 对象
                    ... 内部也这样递归下来, 框图类型中或许要有地方标注一下类型, 这里就全去掉.
                    ... 分配 inst_name.
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
#             (2.) TODO
#     """
#     setattr(cls, "is_operator", True) # (1.)
    
#     # TODO
    
#     return cls


""" Derivatives """ # TODO: 之后或许应该将此搬移到别处
from .signal import SignalType, UInt, SInt, Input, Output, Auto, Bundle

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
        
        # 声明 IO Ports
        res.add_node("op1", Input[op1_type])
        res.add_node("op2", Input[op2_type])
        res.add_node("res", Output[Auto]) # Output[UInt[max(op1_type.W, op2_type.W) + 1]])
        
        # TODO deduction 如何给出? 现在它在 structure 里了, 应该给个函数接口什么的吧.
        
        return res

class TestDiagram(Diagram): # 带参 Diagram 示例
    @staticmethod
    def setup(args):
        # TODO 参数合法性检查
        
        # 创建结构
        res = Structure()
        
        # TODO 声明 IO Ports, [] 内不确定可以写 Auto 或其他 Undetermined 类型, 供推导.
        #       ... 推导可能是通过内部输出导出 Output 的类型, 也可能是通过内部连接的模块得到 Input 的类型, 或其他, 不要局限.
        ab = res.add_node("ab", Bundle[{"a": Input[UInt[8]], "b": Input[UInt[8]]}])
        c = res.add_node("c", Input[UInt[4]])
        z = res.add_node("z", Output[Auto])
        
        # TODO 加入 Box.
        #       ... 其内存储 DiagramType (根据其 ports 得到外 Ports) 或 ExternalWorld (根据前面声明的 Ports 得到外 Ports).
        #       ... 外 Ports 类型最外层应为 IOWrapper, 例如如果是 Bundle, 应递归寻找到 IOWrapper 为止, 可能得到多个 Ports.
        add_ab = res.add_box("add_ab", Addition[UInt[8], Auto])
        add_abc = res.add_box("add_abc", Addition[Auto, Auto])
        
        # TODO 加入连接关系 / Ports (非 IO), 自动维护集合.
        res.connect(ab.a, add_ab.IO.op1)
        res.connect(ab.b, add_ab.IO.op2)
        res.connect(add_ab.IO.res, add_abc.IO.op1)
        res.connect(c, add_abc.IO.op2)
        res.connect(add_abc.IO.res, z)
        
        return res

