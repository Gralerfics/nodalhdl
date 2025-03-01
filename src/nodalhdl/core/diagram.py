from .signal import SignalType, IOWrapper
from .utils import ObjDict

import uuid
from inspect import isfunction


""" Diagram Type """
class DiagramTypeException(Exception): pass

class DiagramType(type):
    diagram_type_pool = {} # 框图类型池, 去重
    
    UUID_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
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
                        ... 改用一下 uuid3, 虽然还是 str.
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
            new_name = f"{name}_{str(uuid.uuid3(DiagramType.UUID_NAMESPACE, str(inst_args))).replace('-', '_')}"
        
        if not new_name in mcs.diagram_type_pool.keys(): # 若尚未创建过
            new_cls = super().__new__(mcs, new_name, bases, attr) # 先创建类, setup() 可能未在子类中显式重写 (即未在 attr 中)
            setup_func = new_cls.setup
            
            try:
                new_structure: Structure = setup_func(inst_args) # 生成结构
                if new_structure is not None:
                    new_structure.instantiate(in_situ = True, reserve_safe_structure = True) # 原位局部非定态例化, 将可能需要修改的 undetermined 部分例化, 为推导做准备
                    new_structure.deduction() # 生成后固定前进行一次推导, 自动补完与外界无关的省略信息
                    new_structure.apply_runtime() # 直接固定信号类型原始值为首次推导结果
                    new_structure.lock() # 固定生成的模板为非自由结构, 不能再修改
                new_cls.structure_template = new_structure
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
        
        self.runtime_id = None
        self.runtime_signal_type = None # 运行时信号类型, 不要直接修改, 而是调用方法; 保证是去除 IO 的
    
    def __len__(self):
        return len(self.nodes)
    
    def __repr__(self):
        return f"{self.nodes}"
    
    """
        下面这些方法可能造成 net 结构变化, 请注意 runtime_signal_type 等信息的传递和更新.
    """
    def merge_net(self, other_net: 'StructureNet'):
        if self == other_net:
            return
        
        net_h, net_l = self, other_net
        if len(net_h) < len(net_l):
            net_h, net_l = net_l, net_h
        
        for node in net_l.nodes: # [NOTICE] 效率问题
            net_h.add_node(node)
        
        del net_l
    
    def add_node(self, node: 'StructureNode'): # 添加节点, 双向绑定
        self.nodes.add(node)
        node.located_net = self
        self.merge_runtime_type(node.origin_signal_type) # 加节点自动更新 runtime_signal_type
    
    def remove_node(self, node: 'StructureNode'):
        self.nodes.remove(node)
        self.init_runtime_type() # 删节点自动更新 runtime_signal_type
    
    """
        下面是对 runtime_signal_type 进行操作的方法.
    """
    def get_runtime_type(self):
        return self.runtime_signal_type
    
    def init_runtime_type(self) -> bool: # 遍历 nodes 得到初始情况, 返回是否发生变化
        flag = False
        for node in self.nodes:
            flag |= self.merge_runtime_type(node.origin_signal_type)
        return flag
    
    def set_runtime_type(self, signal_type: SignalType) -> bool: # 忽略 IO, 返回是否发生变化
        new_st = signal_type.clear_io()
        flag = new_st != self.runtime_signal_type
        self.runtime_signal_type = new_st # 仅该方法可直接修改 runtime_signal_type, 这是由于要考虑对 runtime_deduction_effected 的操作
        
        if flag: # 如果 runtime 信息发生了改变, 说明正在进行的类型推导产生收益, 标记在 runtime_deduction_effected 中
            for node in self.nodes:
                if node.located_box is not None and node.located_box.located_structure is not None:
                    node.located_box.located_structure.runtime_deduction_effected = True
        
        return flag
    
    def merge_runtime_type(self, signal_type: SignalType) -> bool: # 返回是否发生了变化
        if self.runtime_signal_type is None:
            return self.set_runtime_type(signal_type)
        else:
            return self.set_runtime_type(self.runtime_signal_type.merges(signal_type))

class StructureNode:
    """
        线路结点, 存有 (如果有的话) 所属 box (有的话应该是 IO Wrapped 的, IO 的 Nodes 又称 Ports).
        
        node 指向唯一的 net, net 存有所包含 node 的集合.
        node 指向唯一的 box (如有), box 也存有所有的相关 node (port).
    """
    def __init__(self, name: str, signal_type: SignalType, located_net: StructureNet = None, located_box: 'StructureBox' = None):
        self.located_net: StructureNet = located_net
        self.located_box: StructureBox = located_box
        
        self.name = name
        self._private_origin_signal_type = signal_type # 不要直接修改
        
        if self.located_net is None: # 注意 add_node 中使用了 origin_signal_type, 要在赋值之后调用
            StructureNet().add_node(self)
        else:
            self.located_net.add_node(self)
    
    def __repr__(self):
        return f"<Node {self.name} ({self.origin_signal_type.__name__} -> {self.signal_type.__name__}, id: {id(self)})>"
    
    @property
    def origin_signal_type(self):
        return self._private_origin_signal_type

    @property
    def located_structure(self):
        """
            寻找节点所在 structure.
            若节点为 port, 即作为某个 box 的端口, 那么可以通过 .located_box.located_structre 访问;
            若节点为 node, 则需要遍历 .located_net, 寻找到一个 port 再访问.
            如果未能成功, 返回 None, 代表该节点游离, 也就不会对结构产生影响.
        """
        if self.located_box is not None: # port
            return self.located_box.located_structure
        else: # node
            if self.located_net is None:
                return None
            for node in self.located_net.nodes:
                if node.located_box is not None:
                    return node.located_box.located_structure
        
        return None
    
    @property
    def signal_type(self):
        """
            根据 runtime_id 情况自动更新所在 net 的 runtime_signal_type 并返回.
            返回的类型是去除 IO 的, net 上存的类型不可能协调 Input 和 Output.
                    ... TODO 无驱动和多驱动问题的判断, 应该也是要写在 init_ 和 merge_ 里 (init_ 时把驱动存在 net 中, merge_ 方便直接判断).
            以及, 按照注册 IO 的方式, origin_signal_type 一定都是最外层单 IO Wrapped 的.
        """
        s = self.located_structure
        if s is None:
            raise AttributeError(f"The node is not connected to a structure")
        
        n = self.located_net
        if n.runtime_id != s.runtime_id: # runtime_id 不一致, 更新 net 的 runtime_id, 重置 runtime_signal_type
            n.init_runtime_type()
            n.runtime_id = s.runtime_id
        
        return n.get_runtime_type()
    
    @property
    def determined(self):
        return self.signal_type.determined
    
    """
        以下方法可能修改 origin_signal_type, 这有可能影响其所在 net 的 runtime_signal_type (例如信息量减少), 注意要重置.
    """
    def set_origin_signal_type(self, signal_type: SignalType):
        self._private_origin_signal_type = signal_type
        self.located_net.init_runtime_type() # 重置
    
    """
        以下操作可能变更框图结构, 执行后需要刷新 runtime_signal_type.
        注:
            (1.) 如何确认图结构发生变化?
                 看操作是否波及 port, 如果操作没有让 ports 关系变化 (例如加入/删除单个 node), 则该操作并不会改变图结构.
                 若操作改变了 ports 关系 (例如导致了两个 ports 所在 net 合并 (即使操作的是 node), 分离某个 port 等), 则会改变拓扑.
            (2.) 如何找到其所属 structure?
                 由 (1.), 变更必然由 port 导致, port 中记录有 located_box, 而 box 中记录有 located_structure.
            (3.) 如何刷新 runtime_signal_type?
                 runtime_signal_type 保存在 net 中, 可以遍历 structure 找到所有 ports 后修改.
                 但每次修改都遍历 structure 太冗余, 考虑延迟更新, 在 structure 中记录 runtime_id 作为运行时标识,
                 net 里面也存一个, 二者一致表示 net 当前版本与 structure 同步.
                 当发生结构变化时, 更新 structure 的 runtime_id, 更新在 update_runtime_id() 中实现.
                 注意, 这里需要递归更新所有子结构的 runtime_id, 这是由于外部推导结果的失效可能导致内部推导结果的失效, 但只更新外部 runtime_id 不会触发内部的延迟更新 (内部 net 的 located_structure 不涉外部).
    """
    def merge(self, other_node: 'StructureNode'):
        self.located_net.merge_net(other_node.located_net)
        
        if self.located_structure is not None:
            self.located_structure.update_runtime_id() # 更新 structure runtime_id
    
    def separate(self):
        if len(self.located_net) <= 1: # 本就单独成集
            return
        
        self.located_net.remove_node(self)
        StructureNet().add_node(self)
        
        if self.located_box is not None: # port 断连, 一定影响了结构, 更新 structure runtime_id
            if self.located_structure is not None:
                self.located_structure.update_runtime_id()
        else: # node 断连, 只需要重置所在 net 的 runtime 信息
            self.located_net.init_runtime_type()
    
    def delete(self):
        if self.located_box is not None: # port, 不允许删除
            raise DiagramTypeException(f"An active port (under a box) is not allowed to be deleted")
        
        self.located_net.remove_node(self)
        self.located_net.init_runtime_type() # node 删除, 重置 runtime 信息即可
        del self
    
    """
        以下方法皆直接调用所在 net 的方法, 只是为了方便调用.
    """
    def get_runtime_type(self):
        return self.located_net.get_runtime_type()
    
    def init_runtime_type(self):
        self.located_net.init_runtime_type()
    
    def set_runtime_type(self, signal_type: SignalType):
        self.located_net.set_runtime_type(signal_type)
    
    def merge_runtime_type(self, signal_type: SignalType) -> bool:
        return self.located_net.merge_runtime_type(signal_type)

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
    def __init__(self, name: str, located_structure: 'Structure'):
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
            return True # EEB 是确定的

        # TODO 是否要为 _register_ports_from_structure - _build 注释 (2.) 的情况加双保险, 判断 box.IO 是否也确定?
        
        return self.structure.determined
    
    def _register_ports_from_structure(self, update: bool = False): # 从 self.structure 自动注册端口, 内部方法
        if self.structure is None:
            raise DiagramTypeException(f"A structure is needed for automatic port registration")
        
        def _build(d, update, old_d = None):
            """
                遍历 structure.EEB.IO 参照其构建其所在 box 的 IO.
                非 update 模式用于 box.IO 还未和其他结构发生联系的情况, 此时 box.IO 中的 StructureNode 都是复制属性新创建的;
                update 模式用于 box.IO 已经被使用的情况, 此时要保留原先的 StructureNode 对象和它们身上携带的 net 关系, 不新创建 node 而是修改原有的属性,
                所以 update 模式下应当要求传入的 structure.EEB.IO 和原 box.IO (self.IO) 结构一致.
                
                注:
                    (1.) 为什么不合并两种用途?
                         要建就重建, 要修就原封不动, 不允许出现混杂的操作, 没有物理意义.
                    (2.) 为什么复制 runtime 信息?
                         考虑情况, structure 推导后留下 runtime 信息, 放入 box 时只复制了 origin 信息, 导致 structure 是 determined 但 box 不是.
                         如果 box.determined 不考虑 box.IO 是否 determined, 就可能导致不进入内部的推导, runtime 信息无法传递出来.
            """
            if isinstance(d, ObjDict):
                if update:
                    for sub_key, sub_val in d.items():
                        _build(sub_val, update, old_d[sub_key])
                else:
                    return ObjDict({sub_key: _build(sub_val, update, old_d) for sub_key, sub_val in d.items()})
            else: # StructureNode
                if update:
                    old_d.set_origin_signal_type(d.origin_signal_type.flip_io()) # 注意使用 set_ 函数, 其中会更新其所在 net 的 runtime_signal_type
                    old_d.located_net.merge_runtime_type(d.located_net.get_runtime_type()) # [!] 复制节点时 origin 信息应来自参考节点的 origin 信息 (上一行), 然后再更新可能携带的 runtime 信息到自己的 runtime 信息, 见注释 (2.)
                else:
                    new_node = StructureNode(d.name, d.origin_signal_type.flip_io(), located_box = self) # 注意创建时引用所属 box (self)
                    new_node.located_net.merge_runtime_type(d.located_net.get_runtime_type()) # [!] 同上
                    return new_node
        
            return old_d
        
        self.IO = _build(self.structure.EEB.IO, update = update, old_d = self.IO)
    
    def set_structure(self, structure: 'Structure', update: bool = False): # 用 structure 重置结构
        if update:
            pass # [NOTICE] 检查 structure 是否和现有的 IO 一致
        
        if not update:
            self.IO = ObjDict()
        
        self.structure = structure
        self._register_ports_from_structure(update = update)
    
    def register_port(self, name: str, port_dict):
        """
            手动注册端口, 要求 structure 为 None.
            port_dict 可能为 StructureNode 也可能是结构化存有 StructureNode 的 ObjDict.
        """
        if self.structure is not None:
            raise DiagramTypeException(f"IO ports are automatically registered from structure")
        
        self.IO[name] = port_dict
    
    def deduction(self):
        """
            对 box 下的 structure 进行类型推导.
            由于 box.IO 与 structure.EEB.IO 对应,
        """
        if self.structure is None:
            return
        
        def _update(from_d, to_d): # 遍历 .IO, 将 from_d 的 runtime 信息更新到 to_d
            if isinstance(from_d, ObjDict):
                for sub_key, sub_val in from_d.items():
                    _update(sub_val, to_d[sub_key])
            else: # StructureNode
                to_d.located_net.merge_runtime_type(from_d.located_net.get_runtime_type())
        
        _update(self.IO, self.structure.EEB.IO) # 将 box.IO 所属 net 的 runtime 信息更新到 structure.EEB.IO
        
        if not self.structure.determined: # 实际上如果结构确定, deduction 也会很快退出来; 前后两个 _update 必须执行, 确保 box.IO 确定但结构不确定的情况以及 box.IO 不确定但结构确定的情况都能最终完成同步
            self.structure.deduction() # 递归推导
        
        _update(self.structure.EEB.IO, self.IO) # 将 structure.EEB.IO 的 runtime 信息更新到 box.IO
    
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
        
        self.runtime_id = str(uuid.uuid4()) # 用于表示结构变化的 id
        self.runtime_deduction_effected = False # 用于表示推导中是否产生收益的标识
        
        """
            关于 External Equivalent Box (EEB), 即将 structure 以外视作一个内外翻转的大 box,
            其 ports 为 structure 的外部端口, 注意 Input 和 Output 反转 (解决外部 IO 相对内部方向相反的问题).
            这样的操作可解决 structure 的 IO 和内部 box 的 IO 类型不同, 影响统一处理的问题.
            
            在创建 structure 时, 需要创建一个 EEB, 并在后续的 add_port 调用中为其注册 IO.
        """
        self.add_box("_extern_equivalent_box")
    
    def __repr__(self):
        return f"<Structure {self.name} (free: {self.free}, determined: {self.determined}, runtime_id: {self.runtime_id})>"
    
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
    
        def _search(d): # 自身所有 IO
            if isinstance(d, ObjDict):
                return all([_search(sub_val) for sub_val in d.values()])
            else: # StructureNode, determined 来自会自动处理 runtime 问题的 .signal_type 的判断
                return d.determined
        
        return _search(port_dict) and all([box.determined for box in self.boxes.values()]) # 加上所有下辖 box 确定
    
    def update_runtime_id(self):
        """
            递归更新当前以及所有子结构的 runtime_id.
            变化即可, 无需内外 id 一致. 这是基于 structure 独立性的考虑, 即 structure 并不清楚自己是否被装入 box 成为了子结构, 所以涉及外部结构变化的更新都需要外部结构主动实施.
        """
        self.runtime_id = str(uuid.uuid4())
        
        for box in self.boxes.values():
            if box.structure is not None:
                box.structure.update_runtime_id()
    
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
        
        if self.free and in_situ: # 原位局部例化, 当前结构 free, 使用原结构引用, 只需要向下递归直至碰到 locked 的结构
            res = self
            
            for box in self.boxes.values():
                if box.structure is None:
                    continue # 无结构 box (例如 EEB) 局部例化中不需要处理
                
                if not reserve_safe_structure or not box.determined:
                    # 不保留安全结构, 或者保留但遇到了非定态的结构, 需要继续深入
                    box.set_structure(box.structure.instantiate(in_situ = in_situ, reserve_safe_structure = reserve_safe_structure), update = True) # 使用 update 保留原有结构
        
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
                                else: # StructureNode, origin_ 就应复制 origin_, runtime 信息在后面 net 中复制
                                    new_d[sub_key] = StructureNode(sub_key, sub_val.origin_signal_type, located_box = new_box)
                            
                            # 递归建立映射
                            _build(sub_val, new_d[sub_key])
                    else: # StructureNode
                        map_dict[d] = new_d
                        
                        # 4. 上溯到 net, 无则令 new_net (net') = new_d.located_net 并建立映射, 复制信息; 有则合并 net
                        net: StructureNet = d.located_net
                        new_net: StructureNet = new_d.located_net
                        new_net.set_runtime_type(net.get_runtime_type()) # 复制 runtime_signal_type 信息 ([NOTICE] 结构完全复制, 推导结果自然也可以)
                        if net not in map_dict.keys():
                            map_dict[net] = new_net
                        else:
                            map_dict[net].merge_net(new_net)
                
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
    
    def apply_runtime(self):
        """
            将当前 runtime 推导信息直接应用到 origin 上.
            遍历所有 boxes 下的 ports, 修改 origin_signal_type, 再递归修改子结构.
            TODO 是否需要考虑 nodes? 目前看没有影响, 暂时只考虑 ports. 考虑 nodes
            TODO [global] 用到的地方太多了, 什么时候把遍历 box.IO 的功能封装成迭代器之类的, 不要每次都写一遍递归.
        """
        def _apply(d): # 遍历 .IO 操作每个 port
            if isinstance(d, ObjDict):
                for sub_val in d.values():
                    _apply(sub_val)
            elif isinstance(d, StructureNode):
                d.set_origin_signal_type(d.origin_signal_type.applys(d.located_net.get_runtime_type()))
        
        for box in self.boxes.values():
            _apply(box.IO) # EEB.IO 这次也要修改
            
            if box.structure is not None:
                box.structure.apply_runtime()
    
    def deduction(self) -> bool:
        """
            可分结构的自动推导, 通过从 structure 和 box 的 port 出发沿 net 的迭代完成.
            
            进行推导的结构必须 free, 而只有 determined 的结构不会被继续递归调用 deduction;
            这意味着推导不应该碰到 non-free 的 undetermined 结构, 所以在推导前需要先进行一次例化 (建议原位局部非定态), 这可以将所有 undetermined 部分例化为 free 的.
            
            从所有 box 的 ports 迭代, 处理到 box 的时候看下是否 .determined, 是的话似乎不用做什么;
            不是的话再看是否 .free, 是的话递归推导, 不是的话先例化 (例化直接递归到 determined 模块), 再递归推导, 推导可能导致 box ports 更新, 更新的 ports 重新加入队列.
                    ... 所以或许可以不用等碰到了再例化, 而是直接把 boxes 中非 determined 的非 free 的 box 先例化掉.
            
            进入 box 继续 deduction 前, 需要将 box.IO 同步到 box.structure.EEB.IO; deduction 后, 需要反向同步. 这实现在了 StructureBox.deduction 中. 为独立的顶层 structure 调用 deduction 时不需要该操作, 因为外部已没有 box, 其他情况则需要注意.
            
            TODO 基于信息熵的顺序选择, 还没想好, 先直接遍历直到收敛.
            
            关于 runtime_deduction_effected, deduction 针对一个 structure 进行, 每次调用 net 的 set_runtime_type 如果产生有效修改则会置 runtime_deduction_effected 为 True,
            即该标记监测该 structure 下直辖的 net (located_structure = self) 的变化情况, 不包括 box 中 deduction 的结果,
            这样做是由于, 即便假设 box 内部推导产生了收益但未反映到 ports, 而其他 net 都没有改变, 这种情况也可认为已经收敛, 因为再对 box 进行一次推导也不会有变化, 外围 net 不变 deduction 在 box 的状态上就幂等.
        """
        if not self.free:
            raise DiagramInstantiationException(f"Only free structure can be deduced. You can call .instantiate() to get a free structure")
        
        print("Deduction on structure: ", self)
        
        if self.custom_deduction is not None:
            print("Custom deduction:")
            print("Before: ", self.EEB.IO)
            self.custom_deduction(self) # 基本算子的自定义推导
            print("After: ", self.EEB.IO)
            return
        
        while not self.determined:
            self.runtime_deduction_effected = False # 开始一轮推导时置为未产生收益
            print("New round.")
        
            for box in self.boxes.values():
                print("Deduction on box: ", box)
                
                if box.determined: # 已经确定的 box 不需要继续推导; 若未确定, deduction 前的例化应该已经保证其为 free 的
                    print("Determined box, skip.")
                    continue
                
                print("Before: ", box.IO)
                box.deduction() # 递归推导, 双向同步在 StructureBox.deduction 中完成
                print("After: ", box.IO)
            
            if not self.runtime_deduction_effected: # 一轮结束无收益则结束推导
                print("Not changed, stop.")
                break
    
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

