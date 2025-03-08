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
            
            if changed: # TODO runtime signal type changed
                pass # 对应 runtime_id 的 deduction_effected 要变 True
            
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
    
    def __init__(self):
        # references
        self.nodes_weak: weakref.WeakSet[Node] = weakref.WeakSet()
        
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
            Net().add_node(self) # add_node() will update runtime ssignal type, so no need to be called after assigning origin_signal_type
        self.located_structure_weak: weakref.ReferenceType = weakref.ref(located_structure) # the ID of the structure whose internal nodes this node is connected to
        self.port_of_structure_weak: weakref.ReferenceType = None # if the node is an external port of a structure, this will be the structure

    @property
    def is_port(self):
        return self.port_of_structure_weak is not None
    
    def set_origin_type(self, signal_type: SignalType):
        self.origin_signal_type = signal_type
        for runtime in self.located_net.runtimes.values(): # reset all related net runtime
            runtime.reset_type(self.located_net)
    
    def get_type(self, runtime_id: RuntimeId):
        if self.located_net.runtimes.get(runtime_id) is None:
            # no record for this runtime, initialize one
            self.located_net.create_runtime(runtime_id)
        return self.located_net.runtimes[runtime_id].signal_type

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

