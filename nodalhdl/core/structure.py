from .signal import SignalType, IOWrapper, Input, Auto
from .hdl import HDLFileModel
from .utils import ObjDict

import weakref
import uuid
from inspect import isfunction
from typing import List, Dict, Set

import logging # TODO 搞一个分频道调试输出工具
logging.basicConfig(level = logging.INFO,format = '%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


""" Structure """
class StructureException(Exception): pass
class StructureDeductionException(Exception): pass
class StructureGenerationException(Exception): pass

class RuntimeId:
    """
        Used as keys for runtimes (weakref.WeakKeyDictionary),
        when all references to a RuntimeId object are lost, the corresponding runtime will be garbage collected.
    """
    def __init__(self):
        self.id: str = str(uuid.uuid4())

class Net:
    """
        结点集合.
        TODO
    """
    class Runtime:
        def __init__(self, attach_net: 'Net', runtime_id: RuntimeId = None):
            # properties
            self.id: RuntimeId = runtime_id if runtime_id is not None else RuntimeId()
            self.signal_type: SignalType = Auto # must be set by set_signal_type()
            
            # references
            self.attach_net: weakref.ReferenceType[Net] = weakref.ref(attach_net) # the net this runtime is attached to
            
            # initialization
            self.reset_type() # set signal type to the union of all nodes' signal type
        
        def set_type(self, signal_type: SignalType) -> bool:
            new_st = signal_type.clear_io() # io wrapper cleared
            changed = new_st is not self.signal_type
            self.signal_type = new_st
            
            if changed: # the operation on this runtime changed the information
                s = self.attach_net().located_structures_weak()
                if s.runtimes.get(self.id) is None: # no record for this runtime_id in the structure, create one
                    s.create_runtime(self.id)
                s.runtimes[self.id].deduction_effective = True
            
            return changed
        
        def merge_type(self, signal_type: SignalType) -> bool:
            return self.set_type(self.signal_type.merges(signal_type))
        
        def reset_type(self) -> bool:
            changed = False
            for node in self.attach_net().nodes_weak: # node is the object, not the weakref
                changed |= self.merge_type(node.origin_signal_type)
            return changed
    
    def create_runtime(self, runtime_id: RuntimeId = None) -> 'Net.Runtime':
        new_runtime = Net.Runtime(attach_net = self, runtime_id = runtime_id)
        self.runtimes[new_runtime.id] = new_runtime
        return new_runtime
    
    def __init__(self, located_structure: 'Structure'): # not allowed to create a Net/Node without a located structure
        # references
        self.nodes_weak: weakref.WeakSet[Node] = weakref.WeakSet()
        self.located_structures_weak: weakref.ReferenceType[Structure] = weakref.ref(located_structure)
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Net.Runtime] = {}
    
    def __len__(self):
        return len(self.nodes_weak)
    
    def __repr__(self):
        return str({x for x in self.nodes_weak})
    
    def add_node(self, node: 'Node'):
        self.nodes_weak.add(node)
        node.located_net = self
        for runtime in self.runtimes.values(): # update all related net runtime
            runtime.merge_type(node.origin_signal_type)
    
    def merge(self, other: 'Net'):
        if self is other:
            return
        
        if self.located_structures_weak() is not other.located_structures_weak():
            raise StructureException("Cannot merge nets from different structures.")
        
        net_h, net_l = (self, other) if len(self) > len(other) else (other, self)
        for node in net_l.nodes_weak:
            net_h.add_node(node) # all nodes' located_net will be set to net_h and net_l will be garbage collected

class Node:
    """
        线路结点.
        TODO
    """
    def __init__(self, name: str, origin_signal_type: SignalType, located_structure: 'Structure', located_net: Net = None):
        # properties
        self.name: str = name
        self.origin_signal_type: SignalType = origin_signal_type # must be set by set_origin_type()
        
        # references
        self.located_net: Net # strong reference to Net
        if located_net is not None:
            self.located_net.add_node(self) # add_node() will set located_net to self
        else:
            Net(located_structure).add_node(self) # add_node() will update runtime ssignal type, so no need to be called after assigning origin_signal_type
        self.port_of_structure_weak: weakref.ReferenceType = None # if the node is an external port of a structure, this will be the structure

    @property
    def is_port(self):
        return self.port_of_structure_weak is not None
    
    @property
    def located_structure(self):
        return self.located_net.located_structures_weak()
    
    def get_type(self, runtime_id: RuntimeId):
        if self.located_net.runtimes.get(runtime_id) is None:
            # no record for this runtime, initialize one
            self.located_net.create_runtime(runtime_id)
        return self.located_net.runtimes[runtime_id].signal_type
    
    def is_determined(self, runtime_id: RuntimeId):
        return self.get_type(runtime_id).determined
    
    """
        以下操作可能变更框图结构/下属节点原始类型, 将导致 runtime 信息失效.
        注意, 完全失效! 因为变更可能导致子结构/当前结构端口的类型推导发生变化, 从而影响到父/子结构的推导有效性.
        应当清空自己的所有 runtime 信息, 使得任何经过该结构的 runtime_id 失去完整性.
        TODO: 还有一个问题, runtime_id 是推导时从推导的顶层结构开始传递的, 理论上需要阻止用户在不涉及顶层结构的情况下使用该 runtime_id.
                ... 例如, 检查父结构是否有该 id, 若有说明这不是顶层结构, 则不允许单独使用其 runtime 信息.
                ... 开始推导后得到的 runtime_id 应该由推导者持有, 例如前端页面. 这里最多可能有一个 check_runtime() 方法, 用来校验完整性.
                ... 不过好像不被持有的 runtime_id 和对应的 runtime 可能直接被 GC 掉了.
    """
    def set_origin_type(self, signal_type: SignalType):
        self.origin_signal_type = signal_type
        self.located_structure.runtimes.clear() # all runtime information is invalid, clear them

    def merge(self, other: 'Node'):
        self.located_net.merge(other.located_net)
        self.located_structure.runtimes.clear() # all runtime information is invalid, clear them

class StructuralNodes(ObjDict):
    def connect(self, other: 'StructuralNodes'):
        pass # TODO 信号束连接

class Structure:
    """
        结构.
        TODO
    """
    class Runtime:
        def __init__(self, attach_structure: 'Structure', runtime_id: RuntimeId = None):
            # properties
            self.id: RuntimeId = runtime_id if runtime_id is not None else RuntimeId()
            self.deduction_effective: bool = False
            
            # references
            self.attach_structure: weakref.ReferenceType[Structure] = weakref.ref(attach_structure) # the structure this runtime is attached to
    
    def create_runtime(self, runtime_id: RuntimeId = None) -> 'Structure.Runtime':
        new_runtime = Structure.Runtime(attach_structure = self, runtime_id = runtime_id)
        self.runtimes[new_runtime.id] = new_runtime
        return new_runtime
    
    def __init__(self, name: str = None):
        # properties
        self.id = str(uuid.uuid4())
        self.name = name # TODO 允许同名? 问题关键在同层级同名结构或同名复用结构的生成过程
        
        # references (internal structure)
        self.ports_inside_flipped: StructuralNodes = StructuralNodes() # to be connected to internal nodes, IO flipped (EEB)
        self.substructures: Dict[str, 'Structure'] = {} # instance_name -> structure
        
        # references (external structure)
        self.ports_outside: Dict[str, StructuralNodes] = {} # located_structure_id -> IO in the located structure
        self.located_structures_weak: weakref.WeakValueDictionary = weakref.WeakValueDictionary() # located_structure_id -> located_structure
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Structure.Runtime] = {} # runtime_id -> runtime info

    def check_runtime(self, runtime_id: RuntimeId):
        """
            TODO
            递归检查该 runtime_id 是否存在于所有子结构中, 若是则说明该 runtime_id 对应的 runtime 信息有效.
            因为结构/原始类型如果发生变化, 该结构的所有 runtime 信息会被删除.
        """

class StructureProxy:
    """
        结构代理.
        将由 add_substructure 返回, 方便用户进行获取端口等操作.
        TODO
    """
    def __init__(self, structure: Structure, located_structure_id: str):
        self.proxy_structure = structure # the structure to be proxied
        self.located_structure_id = located_structure_id # proxy the structure in the structure with located_structure_id
        
        self.IO = structure.ports_outside[located_structure_id]

