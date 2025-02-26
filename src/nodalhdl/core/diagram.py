from .signal import SignalType, IOWrapper, Auto
from .utils import ObjDict

import hashlib

from inspect import isfunction


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
                (3.) 框图类型创建过程中, 结构固定前, 将原位局部非定态例化并运行一次 deduction.
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
                if new_cls.structure_template is not None:
                    new_cls.structure_template = new_cls.structure_template.instantiate(in_situ = True, reserve_safe_structure = True) # 原位局部非定态例化, 将可能需要修改的 undetermined 部分例化, 为推导做准备
                    new_cls.structure_template.deduction() # 生成后, 固定前, 进行一次推导, 自动补完与外界无关的省略信息, 理论上经过上一步的例化, 这里内部不会再需要例化
                    new_cls.structure_template.lock() # 固定生成的模板为非自由结构, 不能再修改
            except DiagramTypeException as e:
                raise # [NOTICE] 异常处理, 这里直接全部抛出, 要求用户必须处理无参行为
            
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
        return f"<Node {self.name} ({self.signal_type.__name__}, id: {id(self)})>"
    
    @property
    def determined(self): # 信号类型是否已经确定
        return self.signal_type.determined
    
    def merge(self, other_node: 'StructureNode'):
        self.located_net.merge_net(other_node.located_net)
    
    def separate(self):
        if len(self.located_net) <= 1: # 本就单独成集
            return
        
        self.located_net.remove_node(self)
        StructureNet().add_node(self)
    
    def delete(self):
        self.located_net.remove_node(self)
        del self

class StructureBox:
    """
        装有结构或框图类型的容器, 作为 structure 的子模块.
        Box 存在多种使用场景:
            (1.) 创建框图类型时, 在 setup 中使用 add_box, 传入 diagram_type. 这种情况下 structure 指向 diagram_type 的 structure_template, 必然是 locked (non-free) 的.
            (2.) 例如例化时, 可能需要创建普通 box, 直接装入 structure.
                (2.1) 如果是复制所得自由结构, structure 是 free 的.
                (2.2) 如果是用于自定义的固定结构, structure 是 locked 的.
            (3.) 例如 Extern Equivalent Box (EEB), 只需要空 box 模型, 手动添加 IO, structure 为 None.
        Box 是否为自由结构取决于其 structure 的情况.
        Box.IO 与 structure 永远保持一致, 除非 structure 为 None, 仅此时允许手动注册 IO, 否则直接或间接修改 structure 时都会重置 box 的状态, 并自动注册 IO.
    """
    def __init__(self, name: str, located_structure: 'Structure' = None):
        self.name = name
        self.located_structure = located_structure
        
        self.structure: Structure = None
        self.IO = ObjDict()
    
    def __repr__(self):
        return f"<Box {self.name} (io: {self.IO}, structure: {id(self.structure) if self.structure is not None else 'None'})>"
    
    @property
    def free(self): # box 的自由情况取决于其 structure
        if self.structure is None:
            # raise DiagramTypeException(f"This box has no structure")
            return False # [NOTICE]
        
        return self.structure.free
    
    @property
    def determined(self): # box 的结构是否确定取决于其 structure
        if self.structure is None:
            return True # [NOTICE]

        return self.structure.determined
    
    def _register_ports_from_structure(self, update: bool = False): # 从 self.structure 自动注册端口, 内部方法
        if self.structure is None:
            raise DiagramTypeException(f"A structure is needed for automatic port registration")
        
        def _build(d, update, io = None):
            if isinstance(d, ObjDict):
                if update:
                    for sub_key, sub_val in d.items():
                        _build(sub_val, update, io[sub_key])
                else:
                    return ObjDict({sub_key: _build(sub_val, update, io) for sub_key, sub_val in d.items()})
            else: # StructureNode
                if update:
                    io.signal_type = d.signal_type.flip_io()
                else:
                    return StructureNode(d.name, d.signal_type.flip_io(), located_box = self) # 注意创建时引用所属 box (self)
        
            return io
        
        self.IO = _build(self.structure.EEB.IO, update = update, io = self.IO)
    
    def set_structure(self, structure: 'Structure'): # 用 structure 重置结构
        self.IO = ObjDict()
        self.structure = structure
        self._register_ports_from_structure(update = False)
    
    def update_structure(self, structure: 'Structure'): # 用 structure 更新结构, 原有 IO 中的 StructureNode 是保留的, 只会更新其内容
        # TODO 检查 structure 是否和现有的 IO 一致
        self.structure = structure
        self._register_ports_from_structure(update = True)
    
    def register_port(self, name: str, port_dict):
        """
            手动注册端口, 要求 structure 为 None.
            port_dict 可能为 StructureNode 也可能是结构化存有 StructureNode 的 ObjDict.
        """
        if self.structure is not None:
            raise DiagramTypeException(f"IO ports are automatically registered from structure")
        
        self.IO[name] = port_dict
    
    def expand(self):
        pass # TODO 展开 box 到 located_structure 中. (将内部 box 移出时要访问外部 boxes)

class Structure:
    """
        框图结构.
        structure 下辖 boxes, 特殊的 EEB 存有端口节点 (ports) 的索引.
        node 和 net 游离存储, 不直接在 structure 中引用, 遍历结构应从 ports 开始.
        
        structure 对应 VHDL 中的 entity 一级, 其 name 对应 entity name, 也即被其他模块引用时的 component name.
        如果被其他 structure 引用, 例化名 (或者叫 label) 对应 box 的 name.
        同样地, 如果被内部展开, structure (entity) 一级就被消融了, 展开的结构名前以某种形式加上 box name (原 label) 作为前缀防止冲突.
        
        structure 具有 free 属性, 用于判断是否为自由结构, 即不依赖于框图类型. 非自由结构是只读的, 要修改必须先拷贝.
                ... TODO 添加措施强制不可修改非自由结构.
        自由结构不代表内部所有部分都自由, 例如 box 可能是 locked 的, 但 structure 本身是 free 的. 此时可以修改 structure 的结构, 但不能修改 box 的内部结构.
    """
    def __init__(self, name: str):
        self.name = name
        self.free = True # 默认创建时为自由结构, 若经过框图类型 setup, 在 __new__ 时会被 .lock() 递归锁定
        
        self.custom_deduction = None # 自定义类型推导, 用于定义 operator
        self.custom_vhdl = None # 自定义 VHDL 生成, 用于定义 operator
        
        self.boxes = {} # 包含的 boxes
        
        """
            关于 External Equivalent Box (EEB), 即将 structure 以外视作一个内外翻转的大 box,
            其 ports 为 structure 的外部端口, 注意 Input 和 Output 反转 (解决外部 IO 相对内部方向相反的问题).
            这样的操作可解决 structure 的 IO 和内部 box 的 IO 类型不同, 影响统一处理的问题.
            
            在创建 structure 时, 需要创建一个 EEB, 并在后续的 add_port 调用中为其注册 IO.
        """
        self.add_box("_extern_equivalent_box")
    
    @property
    def EEB(self) -> StructureBox:
        return self.boxes["_extern_equivalent_box"]
    
    @property
    def IO(self):
        # 给外面看的? 似乎暂时可以补药. 写的话也应该不是 StructureNode, 而是作为信息展示
        # 还有与此相似的需求: 是否要允许以 structure.xxx.<name> 的形式 (即类似 box.IO 的对象结构) 引用 boxes 和 nodes/ports?
        pass # [NOTICE]
    
    @property
    def determined(self):
        port_dict = self.EEB.IO
    
        def _search(d):
            if isinstance(d, ObjDict):
                return all(_search(sub_val) for sub_val in d.values())
            else: # StructureNode
                return d.determined
        
        return _search(port_dict)
    
    def instantiate(self, in_situ: bool = True, reserve_safe_structure: bool = True):
        """
            例化当前结构.
            注:
                (1.) 在此拓展 `例化` 之概念, 不是只有 DiagramType 才算模板, 可以例化, 用户自定义的 non-free structure 也是模板, 也可以例化.
                     区别在于前者允许以参数化的方式创建结构 (setup), 后者则是直接靠用户搭建.
                     前者是基于后者的, 因为前者创建后得到的 structure_template 也是一个 non-free structure, 所以 `例化` 正统在 Structure.
                     由此需要对例化作出一些分类:
                    (1.1) 向上考虑 (注意, lock 操作是递归的, non-free structure 下必然都是 non-free 的; determined 也是类似, determined 的结构下必然都是 determined 的):
                        (1.1.1) 原位局部例化: 浅层 free 的部分不复制, 就在原地修改, 返回原 structure 的引用.
                                考虑的是例如 setup 中的 deduction 场景, 结构已经是新建的.
                                (in_situ = True)
                        (1.1.2) 全局例化: 返回的 structure 是一个全新的结构.
                                (in_situ = False)
                    (1.2) 向下考虑 (注意, 只有 locked 的结构才能被多处引用, 因为 locked 之后才能保证不被修改, 是安全的):
                        (1.2.0) 注意, in_situ 优先于 reserve_safe_structure.
                                例如若 in_situ 为 True, 在非定态例化中碰到 undetermined 但 free 的结构, 也不会例化, 保留原结构.
                        (1.2.1) 非定态例化: 只例化 undetermined 的部分, 保留 determined 的部分.
                                例化的目的是创建一个用于修改而不影响原结构的结构, 故此处的考虑就是在推导场景下, 只例化需要修改的部分.
                                (reserve_safe_structure = True)
                        (1.2.2) 深度例化: 深层 determined 且 locked 部分也例化.
                                (reserve_safe_structure = False)
                (2.) 注意例如 custom_deduction 等属性也需要复制, 引用即可.
                (3.) 不一定是完全的复制, 搜索应是从 ports 开始, 不与 ports 以某种方式相连的部分或可认为无意义.
        """
        res: Structure = None
        
        if self.free and in_situ: # 原位局部例化, 当前结构 free, 使用原结构引用, 只需要向下递归直至碰到 locked 的结构 TODO 待检查
            res = self
            
            for box in self.boxes.values():
                if box.structure is None:
                    continue # 无结构 box (例如 EEB) 局部例化中不需要处理
                
                if not reserve_safe_structure or not box.determined:
                    # 不保留安全结构, 或者保留但遇到了非定态的结构, 需要继续深入
                    box.update_structure(box.structure.instantiate(in_situ = in_situ, reserve_safe_structure = reserve_safe_structure)) # 使用 update 保留原有结构
        
        else: # 创建新自由结构, 从此向下递归都是新结构
            res = Structure(self.name)
            
            # 一些需要同步的属性
            res.custom_deduction = self.custom_deduction
            res.custom_vhdl = self.custom_vhdl

            # 遍历 boxes, 复制结构
            for box in self.boxes.values():
                map_dict = dict()
                
                # 1. 创建新 box
                new_box = res.add_box(box.name)
                
                # 2. 有结构的 box 需要考虑 structure 是否沿用
                if box.structure is not None:
                    if not reserve_safe_structure or not box.determined:
                        # 不保留安全结构, 或者保留但遇到了非定态的结构, 一定递归例化
                        new_box.set_structure(box.structure.instantiate(in_situ = in_situ, reserve_safe_structure = reserve_safe_structure))
                    else:
                        # 安全结构, 可用原先的 structure 引用
                        new_box.set_structure(box.structure)
            
                # 3. 建立从 box.IO 到 new_box.IO 的映射, 同时复制无结构 box 的 IO
                def _build(d, new_d):
                    if isinstance(d, ObjDict):
                        for sub_key, sub_val in d.items():
                            # 如果 new_box.IO 没有对应结构, 说明是无结构 box, 顺带在此创建其 IO 拷贝
                            if not new_d.get(sub_key, False):
                                if isinstance(sub_val, ObjDict):
                                    new_d[sub_key] = ObjDict()
                                else: # StructureNode
                                    new_d[sub_key] = StructureNode(sub_key, sub_val.signal_type, located_box = new_box)
                            
                            # 递归建立映射
                            _build(sub_val, new_d[sub_key])
                    else: # StructureNode
                        map_dict[d] = new_d
                        
                        # 4. 上溯到 net, 无则令 net' = new_d.located_net 并映射, 有则合并 net
                        net = d.located_net
                        if net not in map_dict.keys():
                            map_dict[net] = new_d.located_net
                        else:
                            map_dict[net].merge_net(new_d.located_net)
                
                _build(box.IO, new_box.IO)
                
                # 5. 暂时忽略非 IO 的 node, 它们不影响连接关系, 如需处理可遍历 net
        
        return res
    
    def lock(self):
        """
            锁定结构, 使其变为非自由结构, 不能再修改.
            递归锁定该结构以及其下属所有 box 的结构.
            目前的 locked 某种意义上就是将 structure 作为一个可复用的模板了, 可以是用户自定义的, 或是使用 setup 生成的.
        """
        self.free = False
        for box in self.boxes.values():
            if box.structure is not None: # 忽略例如 EEB 这样无结构的 box
                box.structure.lock()
    
    def register_deduction(self, func):
        self.custom_deduction = func
    
    def register_vhdl(self, func):
        self.custom_vhdl = func
    
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
            signal_type 应为 perfectly IO-wrapped 的, 这里需要递归提取出以 IO Wrapper 为最小单位的信号, 分别创建 StructureNode 后组成 ObjDict 返回.
            注:
                (1.) 理论上这里可以设计成直接用字典替代 Bundle 结构, 但为了保持一致性, 也便于验证, 还是传 SignalType.
                (2.) 独立于 add_node 进行处理是考虑 ports 需要翻转并附于 External Equivalent Box (EEB) 上 (见前注释, 需为 self.EEB 注册 IO).
        """
        if not signal_type.perfectly_io_wrapped:
            raise DiagramTypeException(f"Imperfect IO-wrapped signal type cannot be attached to a port")
        
        def _build(key: str, t: SignalType):
            if t.belongs(IOWrapper):
                return StructureNode(key, t.flip_io(), located_box = self.EEB) # 注意创建时引用所属 box (EEB)
            else: # 必然是 Bundle, 否则通不过 perfectly_io_wrapped
                return ObjDict({sub_key: _build(sub_key, sub_t) for sub_key, sub_t in t._bundle_types.items()})
        
        new_port = _build(name, signal_type)
        
        self.EEB.register_port(name, new_port) # 注册为 EEB 端口
        
        return new_port # 返回结构化端口或 StructureNode 对象
    
    def add_box(self, name: str, arg = None):
        """
            添加盒子, 创建后加入 boxes 并返回即可.
            可传入 diagram_type 或 structure, 用于确定 box 的结构.
        """
        new_box = StructureBox(name, located_structure = self) # 注意引用所属 structure (self)
        
        if isinstance(arg, DiagramType):
            new_box.set_structure(arg.structure_template)
        elif isinstance(arg, Structure):
            new_box.set_structure(arg)
        
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
    
    def deduction(self) -> bool:
        """
            可分结构的自动推导, 通过从 structure 和 box 的 port 出发沿 net 的迭代完成.
            
            进行推导的结构必须 free, 而只有 determined 的结构不会被继续递归调用 deduction;
            这意味着推导不应该碰到 non-free 的 undetermined 结构, 所以在推导前需要先进行一次例化 (建议原位局部非定态), 这可以将所有 undetermined 部分例化为 free 的.
            
            从所有 box 的 ports 迭代, 处理到 box 的时候看下是否 .determined, 是的话似乎不用做什么;
            不是的话再看是否 .free, 是的话递归推导, 不是的话先例化 (例化直接递归到 determined 模块), 再递归推导, 推导可能导致 box ports 更新, 更新的 ports 重新加入队列.
                    ... 所以或许可以不用等碰到了再例化, 而是直接把 boxes 中非 determined 的非 free 的 box 先例化掉.
            
            [!] 进入 box 继续 deduction 前, 需要将 box.IO 同步到 box.structure.EEB.IO; deduction 后, 需要反向同步.
        """
        if not self.free:
            raise DiagramInstantiationException(f"Only free structure can be deduced. You can call .instantiate() to get a free structure")
        
        if self.custom_deduction is not None:
            return self.custom_deduction(self) # 基本算子的自定义推导
        
        # TODO
    
    def vhdl(self):
        """
            生成 VHDL.
            注:
                (1.) 暂时只考虑 VHDL.
                (2.) 关于 vhdl 方法只接收 structure 作为参数合理性的推导:
                     operator 内部结构仅有 ports 有意义 => args 只影响 ports 声明 => args 的信息已经在 ports 中体现 (如果涉及复杂的映射那就不管了) => 无需 args
        """
        if not self.determined: # 只有确定的结构才能转换为 HDL
            raise DiagramInstantiationException(f"Only determined structure can be converted to HDL")
        
        if self.custom_vhdl is not None: # 基本算子的自定义 VHDL 生成
            return self.custom_vhdl(self)
        
        # TODO


""" Diagram Base """
class DiagramInstantiationException(Exception): pass

class Diagram(metaclass = DiagramType):
    is_operator = False # 是否是基本算子 (见 @operator)
    structure_template: Structure = None # 结构模板
    
    def __init__(self):
        raise DiagramTypeException(f"Use `.instantiate()` instead if you want to instantiate a Diagram")
    
    @property
    def determined(self):
        if self.structure_template is None:
            return True # [NOTICE]
        
        return self.structure_template.determined
    
    @classmethod
    def instantiate(cls, reserve_safe_structure = True) -> Structure:
        """
            例化, 获得一个自由结构用于修改, 继承者不可覆写.
            本质上只是调用 structure_template 的 instantiate 方法 (见 Structure.instantiate 注释).
        """
        return cls.structure_template.instantiate(in_situ = False, reserve_safe_structure = reserve_safe_structure)
    
    @staticmethod
    def setup(args: tuple = ()) -> Structure:
        """
            框图结构生成, 可能含参, 此处为空, 继承者须覆写.
        """
        return None

def operator(cls):
    """
        类装饰器 operator, 置于 Diagram 的子类前表明该类为基本算子 (即不可再分, 直接对应 VHDL).
        基本算子也允许 undetermined, 可能出现几种情况:
            (1.) 关于在 setup 后运行 deduction, 这种情况下如果运行后 determined 了, 就没问题了. 例如用户省略 output 的类型.
            (2.) 若确确实实就是 undetermined, 那么就需要参与到推导中. 当然, 此时已经例化了.
        其实现:
            (1.) 增加或修改类属性 is_operator 为 True, 作为标记.
            (2.) 关于成员方法:
                (2.1) 要求类中必须实现 deduction(s) 方法, 用于类型推导.
                    (2.1.1) 自动包装 setup 方法, 取使其返回的 structure 对象用 register_deduction 注册 deduction 方法.
                (2.2) 要求类中必须实现 vhdl(s) 方法, 用于生成 VHDL 代码.
                    (2.2.1) 自动包装 setup 方法, 取使其返回的 structure 对象用 register_vhdl 注册 vhdl 方法.
            (3.) 返回类.
    """
    setattr(cls, "is_operator", True) # (1.)
    
    if not any(isfunction(method) and method.__name__ == 'deduction' for method in cls.__dict__.values()): # (2.1)
        raise DiagramTypeException(f"Diagram type \'{cls.__name__}\' must implement method \'deduction\'.")
    
    if not any(isfunction(method) and method.__name__ == 'vhdl' for method in cls.__dict__.values()): # (2.2)
        raise DiagramTypeException(f"Diagram type \'{cls.__name__}\' must implement method \'vhdl\'.")
    
    setup_func = cls.setup
    
    def setup_wrapper(args):
        res: Structure = setup_func(args)
        
        res.register_deduction(cls.deduction) # (2.1.1)
        res.register_vhdl(cls.vhdl) # (2.2.1)
        
        return res
    
    cls.setup = setup_wrapper
    
    return cls # (3.)

