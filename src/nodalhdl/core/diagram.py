from .signal import SignalType, IOWrapper
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
                (3.) 在衍生类基础上再加中括号传递参数. 或需考虑该行为的物理意义, 若希望阻止可以在 __getitem__ 中判断是否已有参数 instantiation_arguments.
            最终都进入 __new__, 情况 (2.) 会在 attr 中带有参数 instantiation_arguments.
            创建类型:
                (1.) 构建新类名, 查重, 并创建新类. (注意 hash() 是不稳定的, 与运行时环境有关, 建议使用稳定的映射)
                        ... TODO 构建方案需改进, 目前直接使用 str(inst_args), 与子结构的 str 结果高度相关, 可能限制参数传递的多样性 (内部结构未体现在 str 结果中) 以及破坏哈希的全局稳定性 (str 中出现内存地址). 同时, 哈希重复是否要再检查一下参数是否严格相同, 以防止小概率的哈希冲突?
                (2.) 通过 setup 构建框图结构, 更新类属性 structure_template.
                (3.) 返回新类型.
            注:
                (1.) 框图类型具有唯一性, 在 diagram_type_pool 中进行去重.
                (2.) 框图类型一旦创建, 会且仅会在创建中执行一次 setup, structure_template 由此固定 (*).
                (3.) 框图类型创建过程中, 结构固定前, 不应该运行 deduction, 因为:
                        (a.) 此举会破坏类型名 (即基类名和参数) 和结构之间的直接对应关系 (由 setup 定义).
                        (b.) deduction 目前规定为只可在例化后的 structure 上进行.
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
            except DiagramTypeException as e: # TODO 异常处理
                if e.args and len(e.args) >= 2 and e.args[1] == "force":
                    raise # 内部抛出重要异常, 原样处理
                
                if inst_args: # 有参数还出错, 说明是结构确实有误, 抛出原异常信息, 附带 force
                    raise DiagramTypeException(e.args[0], "force")
                
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
class StructureNet:
    """
        管理一组直接连接的 Nodes (Ports) 的集合为 Net.
        游离存储, 仅为下辖 node 所引用.
    """
    def __init__(self):
        self.nodes = set()
    
    def __len__(self):
        return len(self.nodes)
    
    def __repr__(self):
        return f"{self.nodes}"
    
    def merge_net(self, other_net):
        if self == other_net:
            return
        
        net_h, net_l = self, other_net
        if len(net_h) < len(net_l):
            net_h, net_l = net_l, net_h
        
        # 若 net 存有其他信息, 注意需要于此添加其他操作
        for node in net_l.nodes: # [NOTICE] 效率问题
            net_h.add_node(node)
        
        del net_l
    
    def add_node(self, node): # 添加节点, 双向绑定
        self.nodes.add(node)
        node.located_net = self
    
    def remove_node(self, node):
        self.nodes.remove(node)

class StructureNode:
    """
        线路结点, 存有 (如果有的话) 所属 box (有的话应该是 IO Wrapped 的, IO 的 Nodes 又称 Ports).
        
        node 指向唯一的 net, net 存有所包含 node 的集合.
        node 指向唯一的 box (如有), box 也存有所有的相关 node (port).
        
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
    def __init__(self, name: str, signal_type: SignalType, located_net: StructureNet = None, located_box: 'StructureBox' = None):
        self.located_net: StructureNet = located_net
        if self.located_net is None:
            StructureNet().add_node(self)
        else:
            self.located_net.add_node(self)
        
        self.located_box: StructureBox = located_box
        
        self.inst_name = None
        
        self.name = name
        self.signal_type = signal_type
    
    def __repr__(self):
        return f"<{self.name} ({self.signal_type.__name__})>"
    
    def merge(self, other_node: 'StructureNode'):
        self.located_net.merge_net(other_node.located_net)
    
    def separate(self):
        if len(self.located_net) <= 1: # 本就单独成集
            return
        
        self.located_net.remove_node(self)
        StructureNet().add_node(self)

class StructureBox:
    """
        装有结构或框图类型的容易, 作为 structure 的子模块.
        Box 存在两种场景中:
            (1.) 作为框图类型下 structure_template (Structure) 中的 box, 存有 diagram_type.
                 此时为了让嵌套结构更加统一, box.structure 将引用 diagram_type.structure_template.
                 structure_template 在框图类型构建后应是只读的, 不会被修改, 适合被重复引用.
                 在这种情况下, box 创建时需要参考 structure_template 里的 EEB 注册 IO.
            (2.) 作为 Extern Equivalent Box (EEB), 由调用者 structure 手动注册 IO.
            (3.) 作为框图类型例化后所得 structure 中的 box, 存有新的 structure.
                 例化过程需要参考框图类型下 structure_template 的结构, 深拷贝 (需要特别实现) 出新的 structure.
        判断标准在于传入的 diagram_type 是否为 None, 为 None 则为场景 (2.).
    """
    def __init__(self, name: str, diagram_type: DiagramType = None):
        self.inst_name = None
        
        self.name = name
        self.diagram_type = diagram_type
        self.structure: Structure = None
        
        self.IO_dict = {} # 值为 StructureNode 的引用. 不要直接修改, 除非修改同时置 IO_obj_up_to_date 为 False
        
        if diagram_type is not None:
            self.structure = diagram_type.structure_template # (1.)
            
            def _build(d):
                if isinstance(d, dict):
                    return {sub_key: _build(sub_val) for sub_key, sub_val in d.items()}
                else: # 若正常使用 register_port 这里一定是 StructureNode, 需要到这一级重新创建
                    return StructureNode(d.name, d.signal_type)
            
            self.IO_dict = _build(self.structure.EEB.IO_dict)
        # else: # (2.) & (3.) TODO 不提供模板时, 例如例化时的处理, 是否还允许提供 structure 以自动提取 ports? 或是都要求手动 register_port?
        
        # IO 对象结构构造
        self.IO_obj: DictObject = DictObject(self.IO_dict) # 不要直接调用, 会延迟更新
        self.IO_obj_up_to_date = True
    
    @property
    def IO(self): # 延迟更新, 调用时检查
        if not self.IO_obj_up_to_date:
            # del self.IO_obj
            self.IO_obj = DictObject(self.IO_dict)
            self.IO_obj_up_to_date = True
        
        return self.IO_obj
    
    def register_port(self, name: str, port_dict): # port 可能为 StructureNode 也可能是结构化存有 StructureNode 的 dict (内部都用 dict, DictObject 仅方便使用)
        self.IO_dict[name] = port_dict
        self.IO_obj_up_to_date = False

class Structure:
    """
        框图结构.
        structure 下辖 boxes, 特殊的 EEB 存有端口节点 (ports) 的索引.
        node 和 net 游离存储, 不直接在 structure 中引用, 遍历结构应从 ports 开始.
        structure 不设 name 和 inst_name, 结构就只是结构信息, 装进 box 才是实体.
        其下的 box, node 设 name 和 inst_name, inst_name 未例化时为 None, 例化后参考 name 和结构进行分配.
    """
    def __init__(self):
        self.instantiated = False # 是否为例化后的结构
        self.determined = False # 推导后确定值 TODO: 写成 @property 用所有 port 的 determined 计算?
        
        self.custom_deduction = None # 自定义类型推导, 用于定义 operator
        
        self.boxes = {} # 包含的 boxes
        
        """
            关于 External Equivalent Box (EEB), 即将 structure 以外视作一个内外翻转的大 box,
            其 ports 为 structure 的外部端口, 注意 Input 和 Output 反转 (解决外部 IO 相对内部方向相反的问题).
            这样的操作可解决 structure 的 IO 和内部 box 的 IO 类型不同, 影响统一处理的问题.
            
            在创建 structure 时, 需要创建一个 EEB, 并在后续的 add_port 调用中为其注册 IO.
        """
        self.add_box("_extern_equivalent_box", None)
    
    @property
    def EEB(self) -> StructureBox:
        return self.boxes["_extern_equivalent_box"]
    
    @property
    def IO(self):
        # 给外面看的? 似乎暂时可以补药. 写的话也应该不是 StructureNode, 而是作为信息展示
        # TODO 还有与此相似的需求: 是否要允许以 structure.xxx.<name> 的形式 (即类似 box.IO 的对象结构) 引用 boxes 和 nodes/ports?
        pass
    
    def deduction(self) -> bool:
        """
            TODO 可分结构的自动推导, 通过从 structure 和 box 的 port 出发沿 net 的迭代完成.
            注:
                (1.) 
            如果迭代结束还存在 undetermined 类型的信号, 则说明该结构 undetermined (这里是否给了 A[x][y][z] 这样的结构一些存在的可能性? 分步固化?)
        """
        if not self.instantiated:
            raise DiagramInstantiationException(f"Instantiation is needed before deduction")
        
        if self.custom_deduction is not None:
            return self.custom_deduction(self)
        
        pass # TODO
    
    def register_deduction(self, func):
        self.custom_deduction = func
    
    def add_node(self, name: str, signal_type: SignalType):
        """
            添加节点, 主要用于辅助构建框图, 创建返回即可.
            signal_type 中的 IO Wrapper 将被忽略 (方便用户直接以 ports 的类型添加节点).
        """
        if not signal_type.io_wrapper_included:
            signal_type = signal_type.clear_io() # 忽略 IO Wrapper
        
        return StructureNode(name, signal_type)
    
    def add_port(self, name: str, signal_type: SignalType):
        """
            添加端口, 这里仅指 structure 的外显端口.
            独立于 node 进行处理是考虑 ports 需要翻转并附于 External Equivalent Box (EEB) 上 (见前注释, 需为 self.boxes["_extern_equivalent_box"] 注册 IO).
            signal_type 应为 perfectly IO-wrapped, 这里需要递归提取出以 IO Wrapper 为最小单位的信号, 分别创建 StructureNode 后组成 DictObject 返回.
        """
        if not signal_type.perfectly_io_wrapped:
            raise DiagramTypeException(f"Imperfect IO-wrapped signal type cannot be attached to a port")
        
        def _build(key: str, t: SignalType):
            if t.belongs(IOWrapper):
                return StructureNode(key, t)
            else: # 必然是 Bundle, 否则通不过 perfectly_io_wrapped
                return {sub_key: _build(sub_key, sub_t) for sub_key, sub_t in t._bundle_types.items()}
        
        new_port_dict = _build(name, signal_type) # 提取, 创建 Node, 合成 dict
        
        self.EEB.register_port(name, new_port_dict) # 注册为 EEB 端口
        
        return DictObject(new_port_dict) if isinstance(new_port_dict, dict) else new_port_dict # 返回便于使用的对象结构或 StructureNode 对象
    
    def add_box(self, name: str, diagram_type: DiagramType = None):
        """
            添加盒子, 创建后加入 boxes 并返回即可.
            若传入了 diagram_type, 在 StructureBox 的构造方法中会自动注册 IO.
        """
        new_box = StructureBox(name, diagram_type)
        
        self.boxes[name] = new_box
        
        return new_box
    
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
    is_operator = False # 是否是基本算子 (见 @operator)
    structure_template: Structure = None # 结构模板
    
    def __init__(self):
        raise DiagramTypeException(f"Use `.instantiate()` instead if you want to instantiate a Diagram")
    
    @classmethod
    def instantiate(cls) -> Structure:
        """
            TODO 例化, 与框图类型切割, 把 structure_template 深拷贝出来, 返回一个仅表示结构的 Structure 对象
                    ... 内部也这样递归下来, 框图类型中或许要有地方标注一下类型, 这里就全去掉
                    ... 分配 inst_name
                    ... 分布式地存储 net 和 node 导致此处复制的方法需要考虑, 可能也需要搜索
                            ... 故不一定是完全的复制, 搜索应是从 ports 开始, 不与 ports 以某种方式相连的部分或可认为无意义
            注:
                (1.) 统一过程, 继承者不可覆写.
            TODO [!] 一个问题, 如果有些模板是确定的, 类型推导没有改变它, 那么这个模板在生成代码中是可以复用的.
                    ... 但例化将结构与框图类型切割, 例如一个确定模板在一个结构中被使用于两处, 例化后难以获知这两处是否来自同一模板, 就难以复用 hdl 文件.
        """
        
        pass # TODO
    
    @staticmethod
    def setup(args: tuple = ()) -> Structure:
        """
            框图结构生成, 可能含参, 此处为空, 继承者须覆写.
        """
        return None

def operator(cls):
    """
        类装饰器 operator, 置于 Diagram 的子类前表明该类为基本算子 (即不可再分, 直接对应 VHDL).
        其实现:
            (1.) 增加或修改类属性 is_operator 为 True, 作为标记.
            (2.) 关于类型推导:
                (2.1) 要求类中必须实现 setup(args) 方法, 用于检查参数和声明结构 (基本算子中只管 ports).
                (2.2) 要求类中必须实现 deduction(s) 方法, 用于类型推导.
                (2.3) 自动包装 setup 方法, 取使其返回的 structure 对象用 register_deduction 注册 deduction 方法.
            (3.) 要求类中必须实现 TODO vhdl
        TODO [!] 一个问题, 基本算子似乎不方便使用 Auto 等不定类型. 因为 hdl 的生成依赖 args 而非仅仅信号类型, 但 args 未被规定一定是信号类型.
                ... 具体地, 一个不定的基本算子, 类型推导后或可确定信号类型, 但无法获知信号类型如何对应 args, 也就无法获得生成 hdl 的具体 args.
                ... 是否要特殊化基本算子? 因为 Addition[Auto, Auto] 这种还挺好用的. 让生成 hdl 的函数不仅接收 args 还接收 ports!
    """
    setattr(cls, "is_operator", True) # (1.)
    
    # TODO
    
    return cls

