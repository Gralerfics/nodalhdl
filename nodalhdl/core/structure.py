from .signal import SignalType, IOWrapper, Input, Output, Auto, Bundle
from .hdl import HDLFileModel

import sys
import weakref
import uuid
from typing import List, Dict, Set, Tuple, Union

import logging # TODO 搞一个分频道调试输出工具
logging.basicConfig(level = logging.INFO,format = '%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


""" Id """
class RuntimeId:
    """
        TODO
    """
    NULL_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
    id_pool: weakref.WeakValueDictionary[str, 'RuntimeId'] = weakref.WeakValueDictionary()
    
    def __init__(self, id_str: str):
        self.id_str: str = id_str
        self.next_id: RuntimeId = None # ensure the next_id is referenced by its previous id
    
    def __repr__(self):
        return f"<RuntimeId: {self.id_str} (next: {self.next_id.id_str if self.next_id is not None else None})>"
    
    def _next(self):
        next_id_str = str(uuid.uuid5(RuntimeId.NULL_NAMESPACE, self.id_str)).replace('-', '') # TODO 命名空间下生成的 next_id 和 uuid4 生成 id 的潜在冲突
        next_id = RuntimeId.get(next_id_str)
        return next_id
    
    @staticmethod
    def create(): # TODO 重复
        new_id_str = str(uuid.uuid4()).replace('-', '')
        new_id = RuntimeId(new_id_str)
        RuntimeId.id_pool[new_id_str] = new_id
        return new_id
    
    @staticmethod
    def get(id_str: str):
        if not id_str in RuntimeId.id_pool.keys(): # not in pool, add it
            new_id = RuntimeId(id_str)
            RuntimeId.id_pool[id_str] = new_id
            return new_id
        return RuntimeId.id_pool[id_str]
    
    def next(self):
        if self.next_id is None:
            self.next_id = self._next()
        return self.next_id


""" Structure """
class StructureException(Exception): pass
class StructureDeductionException(Exception): pass
class StructureGenerationException(Exception): pass

class Net:
    """
        Set of Node objects.
    """
    class Runtime:
        def __init__(self, attach_net: 'Net', runtime_id: RuntimeId):
            # properties
            self.id_weak: weakref.ReferenceType[RuntimeId] = weakref.ref(runtime_id)
            self.signal_type: SignalType = Auto # must be set by set_signal_type()
            
            # references
            self.attach_net: weakref.ReferenceType[Net] = weakref.ref(attach_net) # the net this runtime is attached to
            
            # initialization
            self.reset_type() # set signal type to the union of all nodes' signal type
        
        def set_type(self, signal_type: SignalType) -> bool:
            """
                Set runtime type. (IO-ignored)
            """
            new_st = signal_type.clear_io() # io wrapper cleared
            changed = new_st is not self.signal_type
            self.signal_type = new_st
            
            if changed: # the operation on this runtime changed the information
                s = self.attach_net().located_structure_weak()
                s.get_runtime(self.id_weak()).deduction_effective = True
            
            return changed
        
        def merge_type(self, signal_type: SignalType) -> bool:
            """
                Update runtime type by merging. (IO-ignored)
            """
            return self.set_type(self.signal_type.merges(signal_type))
        
        def reset_type(self) -> bool:
            """
                Reinitialize runtime type from nodes contained.
            """
            changed = False
            for node in self.attach_net().nodes_weak: # node is the object, not the weakref
                changed |= self.merge_type(node.origin_signal_type)
            return changed
    
    def create_runtime(self, runtime_id: RuntimeId) -> 'Net.Runtime':
        new_runtime = Net.Runtime(attach_net = self, runtime_id = runtime_id)
        self.runtimes[runtime_id] = new_runtime
        return new_runtime
    
    def get_runtime(self, runtime_id: RuntimeId) -> 'Net.Runtime':
        if self.runtimes.get(runtime_id) is None:
            return self.create_runtime(runtime_id)
        return self.runtimes[runtime_id]
    
    def __init__(self, located_structure: 'Structure'): # not allowed to create a Net/Node without a located structure
        # references
        self.nodes_weak: weakref.WeakSet[Node] = weakref.WeakSet()
        self.located_structure_weak: weakref.ReferenceType[Structure] = weakref.ref(located_structure)
        
        self.driver: weakref.ReferenceType[Node] = None # driver node (also in nodes_weak) or None, should be only one, originlly Output; others are loads
        self.latency: int = 0 # latency of the net, i.e. registers between driver and loads
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Net.Runtime] = weakref.WeakKeyDictionary()
    
    def __len__(self):
        return len(self.nodes_weak)
    
    def to_str(self, runtime_id: RuntimeId):
        return str({x.to_str(runtime_id) for x in self.nodes_weak})
    
    """
        The following actions (add_node, separate_node and merge) may change the structural information.
        They should not be called by the user directly, but by the Node object.
    """
    def add_node(self, node: 'Node'):
        if node.origin_signal_type.belongs(Output): # driver
            if self.driver is not None:
                raise StructureException("Net cannot have multiple drivers")
            self.driver = weakref.ref(node)
        
        self.nodes_weak.add(node)
        node.located_net = self
        for runtime in self.runtimes.values(): # update all related net runtime
            runtime.merge_type(node.origin_signal_type)
    
    def separate_node(self, node: 'Node'):
        if node not in self.nodes_weak:
            raise StructureException("Node not in net")
        
        if len(self.nodes_weak) == 1:
            return # only one node, no need to separate
        
        if self.driver is not None and self.driver() is node: # driver is removed
            self.driver = None
        
        self.nodes_weak.remove(node)
        Net(self.located_structure_weak()).add_node(node)
    
    def merge(self, other: 'Net'):
        if self is other:
            return
        
        if self.located_structure_weak() is not other.located_structure_weak():
            raise StructureException("Cannot merge nets from different structures")
        
        if self.driver is not None and other.driver is not None:
            raise StructureException("Merged net cannot have multiple drivers")
        
        net_h, net_l = (self, other) if len(self) > len(other) else (other, self)
        for node in net_l.nodes_weak: # [NOTICE] 会不会出现某个 node 被删除但尚未被 GC 掉的问题
            net_h.add_node(node) # all nodes' located_net will be set to net_h and net_l will be garbage collected

class Node:
    """
        Circuit node.
    """
    def __init__(self, name: str, origin_signal_type: SignalType, located_structure: 'Structure', port_of_structure: 'Structure' = None, located_net: Net = None):
        # properties
        self.name: str = name # raw name, no need to be unique. layer information for ports will be added in StructuralNodes.nodes()
        self.origin_signal_type: SignalType = origin_signal_type # must be set by set_origin_type()
        
        # references
        self.located_net: Net # strong reference to Net
        if located_net is not None:
            self.located_net.add_node(self) # add_node() will set located_net to self
        else:
            Net(located_structure).add_node(self) # add_node() will update runtime signal type, so no need to be called after assigning origin_signal_type
        self.port_of_structure_weak: weakref.ReferenceType = weakref.ref(port_of_structure) if port_of_structure is not None else None # if the node is an external port of a structure, this will be the structure

    def to_str(self, runtime_id: RuntimeId):
        return f"<Node {self.name} {id(self)} ({self.origin_signal_type.__name__} -> {self.get_type(runtime_id).__name__})>"
    
    @property
    def is_port(self):
        return self.port_of_structure_weak is not None
    
    @property
    def located_structure(self):
        return self.located_net.located_structure_weak()
    
    def is_determined(self, runtime_id: RuntimeId):
        return self.get_type(runtime_id).determined
    
    def is_originally_determined(self):
        return self.origin_signal_type.determined
    
    def get_type(self, runtime_id: RuntimeId):
        """
            Get the runtime type of the located net by runtime_id. (non-IO)
        """
        return self.located_net.get_runtime(runtime_id).signal_type # .clear_io()
    
    def update_type(self, runtime_id: RuntimeId, signal_type: SignalType):
        """
            Update the runtime type of the located net by merging. (IO-ignored)
        """
        self.located_net.get_runtime(runtime_id).merge_type(signal_type)
    
    """
        The following actions (set_origin_type, merge, separate and delete) may change the structural information,
        which will invalidate the runtime information (completely invalidated!).
        Likewise, only the following methods are allowed if you want to change the structural information.
        All runtime information should be cleared, so that any runtime_id that passes through the structure loses its integrity.
    """
    def set_origin_type(self, signal_type: SignalType, do_not_clear_structure_runtime: bool = False):
        if self.origin_signal_type is signal_type: # no change
            return

        self.origin_signal_type = signal_type
        if not do_not_clear_structure_runtime:
            self.located_structure.clear_runtimes() # all runtime information is invalid, clear them

    def merge(self, other: 'Node'):
        if self.located_net is other.located_net: # same net, no change
            return
        
        self.located_net.merge(other.located_net)
        self.located_structure.clear_runtimes() # all runtime information is invalid, clear them
    
    def separate(self):
        if len(self.located_net) == 1: # only one node, no need to separate
            return
        
        self.located_net.separate_node(self)
        self.located_structure.clear_runtimes() # all runtime information is invalid, clear them
    
    def delete(self):
        if self.is_port:
            raise StructureException("Cannot delete a port node")
        
        self.located_net.nodes_weak.remove(self) # theoretically not necessary. this node should have been GCed after located_structure.nodes.remove()
        self.located_structure.nodes.remove(self)
        self.located_structure.clear_runtimes() # all runtime information is invalid, clear them

    """
        Latency setting will not change the structural information. Types are passed through the registers.
    """
    def set_latency(self, latency: int):
        self.located_net.latency = latency

class StructuralNodes(dict):
    def __init__(self, d: dict = {}):
        for key, value in d.items():
            if isinstance(value, dict):
                self[key] = StructuralNodes(value)
            else:
                self[key] = value
    
    def __getitem__(self, key) -> Union[Node, 'StructuralNodes']: # for type hinting
        return super().__getitem__(key)
    
    def __getattr__(self, name) -> Union[Node, 'StructuralNodes']: # for type hinting
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
    
    def to_str(self, runtime_id: RuntimeId):
        return str({n.name: n.to_str(runtime_id) for _, n in self.nodes()})
    
    def connect(self, other: 'StructuralNodes'):
        for k, v in self.items():
            if isinstance(v, Node):
                v.merge(other[k])
            elif isinstance(v, StructuralNodes):
                v.connect(other[k])
    
    def nodes(self, prefix: str = "") -> List[Tuple[str, Node]]:
        """
            Return all Node objects in a list with their full names.
            The full name contains the layer information, e.g. "foo_bar_baz".
        """
        res = []
        for k, v in self.items():
            if isinstance(v, Node):
                res.append((v.name, v))
            elif isinstance(v, StructuralNodes):
                res.extend(v.nodes(prefix + k + "_"))
        return res
    
    def update_runtime(self, self_runtime_id: RuntimeId, other: 'StructuralNodes', other_runtime_id: RuntimeId = None):
        """
            Use other's runtime info (under other_runtime_id) to update self (under self_runtime_id).
        """
        if other_runtime_id is None:
            other_runtime_id = self_runtime_id
        
        def _update(to_p: Union[Node, StructuralNodes], from_p: Union[Node, StructuralNodes]):
            if isinstance(to_p, Node) and isinstance(from_p, Node) and to_p.name == from_p.name:
                to_p.update_type(self_runtime_id, from_p.get_type(other_runtime_id))
            elif isinstance(to_p, StructuralNodes) and isinstance(from_p, StructuralNodes):
                for k, v in to_p.items():
                    _update(v, from_p[k])
            else:
                raise StructureException("Mismatched structural nodes")
        
        _update(self, other)

class Structure:
    """
        Diagram structure.
    """
    class Runtime:
        def __init__(self, attach_structure: 'Structure', runtime_id: RuntimeId):
            # properties
            self.id_weak: weakref.ReferenceType[RuntimeId] = weakref.ref(runtime_id)
            self.deduction_effective: bool = False
            self.originally_determined_hdl_file_model: HDLFileModel = None # only originally determined structure can reuse HDL file model; and runtimes will be cleared if the structure is changed
            
            # references
            self.attach_structure: weakref.ReferenceType[Structure] = weakref.ref(attach_structure) # the structure this runtime is attached to

        def set_originally_determined_hdl_file_model(self, hdl_file_model: HDLFileModel):
            if not self.attach_structure().is_reusable:
                raise StructureException("Cannot set originally determined HDL file model for a originally undetermined structure")
            
            self.originally_determined_hdl_file_model = hdl_file_model
    
    def create_runtime(self, runtime_id: RuntimeId) -> 'Structure.Runtime':
        new_runtime = Structure.Runtime(attach_structure = self, runtime_id = runtime_id)
        self.runtimes[runtime_id] = new_runtime
        return new_runtime

    def get_runtime(self, runtime_id: RuntimeId) -> 'Structure.Runtime':
        if self.runtimes.get(runtime_id) is None:
            return self.create_runtime(runtime_id)
        return self.runtimes[runtime_id]
    
    def clear_runtimes(self):
        self.runtimes.clear()
    
    def __init__(self):
        # properties
        self.id = str(uuid.uuid4()).replace('-', '')
        
        self.custom_deduction: callable = None
        self.custom_generation: callable = None
        
        # references (internal structure)
        self.ports_inside_flipped: StructuralNodes = StructuralNodes() # to be connected to internal nodes, IO flipped (EEB)
        self.substructures: Dict[str, 'Structure'] = {} # instance_name -> structure
        self.nodes: Set[Node] = set() # non-IO nodes
        
        # references (external structure)
        self.ports_outside: Dict[Tuple[str, str], StructuralNodes] = {} # Tuple[located_structure_id, inst_name_in_that_structure] -> IO in the located structure
        self.instance_number: int = 0 # number of instances
        # self.located_structures_weak: weakref.WeakValueDictionary = weakref.WeakValueDictionary() # located_structure_id -> located_structure
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Structure.Runtime] = weakref.WeakKeyDictionary() # runtime_id -> runtime info
    
    @property
    def is_operator(self):
        return self.custom_deduction is not None and self.custom_generation is not None
    
    @property
    def is_runtime_applicable(self):
        """
            Check if the structure and all its originally undetermined substructures are singletons, i.e. do not have multiple located structures.
            Only these structures can apply runtime information.
            Originally determined structures have same information that they will not conflict.
        """
        # return len(self.located_structures_weak) <= 1 and all([subs.is_singleton for subs in self.substructures.values()])
        return self.is_reusable or (self.instance_number <= 1 and all([subs.is_runtime_applicable for subs in self.substructures.values()]))
    
    @property
    def is_reusable(self):
        return self.is_originally_determined()

    def is_runtime_integrate(self, runtime_id: RuntimeId):
        """
            Check if the structure and all its substructures have runtime information with runtime_id.
            Runtime information in structures will be cleared when there are structural modifications.
            No need to check all nodes and ports, their runtime information should be called by the structures.
        """
        return runtime_id in self.runtimes.keys() and all([subs.is_runtime_integrate(runtime_id.next()) for subs in self.substructures.values()])
    
    def is_determined(self, runtime_id: RuntimeId): # all ports and substructures are determined
        ports_determined = all([p.is_determined(runtime_id) for _, p in self.ports_inside_flipped.nodes()])
        substructures_determined = all([s.is_determined(runtime_id.next()) for s in self.substructures.values()])
        return ports_determined and substructures_determined
    
    def is_originally_determined(self): # i.e. reusable structure
        ports_determined = all([p.is_originally_determined() for _, p in self.ports_inside_flipped.nodes()])
        substructures_determined = all([s.is_originally_determined() for s in self.substructures.values()])
        return ports_determined and substructures_determined
    
    def substitute_substructure(self, inst_name: str, structure: 'Structure'):
        """
            将 inst_name 对应的子结构移出该结构, 并替换为 structure.
            要求 inst_name 对应的子结构和 structure 的端口类型完全一致.
            用于深度复制: 递归浅复制配合此方法即可实现深复制.
        """
        pass # TODO
    
    def duplicate(self, shallow: bool = False) -> 'Structure':
        """
            shallow: 是否浅复制, 即只复制一层结构, 子结构保留原引用.
        """
        pass # TODO
    
    def apply_runtime(self, runtime_id: RuntimeId):
        """
            Fix the runtime information under runtime_id into the structure.
            The structure should be singleton and runtime-integrate.
            (*) note:
                set_origin_type() will be called, which clears the runtime information in the structure (not in the net so do not worry that node.get_type(runtime_id) will fail after calling set_origin_type).
                but if the runtime information is applied, the change must be safe, the runtime_id should be kept valid.
                e.g. the user wants to apply an RID to a structure and then use its generation, if the RID information is destroyed as mentioned above, there will be a problem;
                this behavior is reasonable, so the RID information should be retained, by asserting `do_not_clear_structure_runtime = True` in set_origin_type().
        """
        if self.is_reusable: # no need to apply runtime for reusable structure
            return
        
        if not self.is_runtime_applicable:
            raise StructureException("Only singleton structure can apply runtime")
        
        if not self.is_runtime_integrate(runtime_id):
            raise StructureException("Invalid (not integrate) runtime ID")
        
        for _, port in self.ports_inside_flipped.nodes(): # apply runtime info to internal nodes
            port.set_origin_type(port.origin_signal_type.applys(port.get_type(runtime_id)), do_not_clear_structure_runtime = True) # (*)
        
        for ports in self.ports_outside.values(): # apply runtime info to all outside ports
            for _, port in ports.nodes():
                port.set_origin_type(port.origin_signal_type.applys(port.get_type(runtime_id)), do_not_clear_structure_runtime = True) # (*)
        
        for node in self.nodes: # apply runtime info to all nodes (may be not necessary)
            node.set_origin_type(node.origin_signal_type.applys(node.get_type(runtime_id)), do_not_clear_structure_runtime = True) # (*)
        
        for subs in self.substructures.values(): # apply runtime info to all substructures, recursively
            subs.apply_runtime(runtime_id.next())
    
    def deduction(self, runtime_id: RuntimeId):
        """
            Automatic type deduction.
        """
        structure_runtime = self.get_runtime(runtime_id) # ensure runtime information is created, for integrity consideration
        
        if self.is_operator:
            self.custom_deduction(IOProxy(self.ports_inside_flipped, runtime_id, flipped = True))
            return
        
        while not self.is_determined(runtime_id): # stop if already determined
            structure_runtime.deduction_effective = False # reset flag before a new round of deduction
            
            """
                subs.ports_outside[] are under the structure `self` (with runtime_id);
                subs.ports_inside_flipped is under the substructure `subs` (with next_runtime_id).
            """
            for sub_inst_name, subs in self.substructures.items():
                # update substructure's ports with external ports (should be synchronized even though determined, the same below)
                subs.ports_inside_flipped.update_runtime(runtime_id.next(), subs.ports_outside[(self.id, sub_inst_name)], runtime_id) # s.ports_outside[(self.id, sub_inst_name)] is the IO of `s` connected in `self`
                
                """
                    deduction() should be recursively executed on all substructures, so that the runtime information can be passed down,
                    in order to maintain the integrity of the runtime information.
                    (*) Why some time the runtime information is passed down without deduction?
                        Because is_determined(rid) called get_type(rid) in ports, which will create runtime information for the net.
                        When initialized, reset_type will be called, and then merge_type, then set_type, which will fetch runtime information for the structure (if type changed).
                """
                subs.deduction(runtime_id.next()) # recursive deduction
                
                # update external ports with substructure's ports
                subs.ports_outside[(self.id, sub_inst_name)].update_runtime(runtime_id, subs.ports_inside_flipped, runtime_id.next())
            
            if not structure_runtime.deduction_effective: # no change, stop
                break
    
    # TODO TODO TODO TODO TODO
    def generation(self, runtime_id: RuntimeId, prefix: str = "") -> HDLFileModel:
        """
            Generate HDL file model.
            prefix: e.g. this structure is instanced in somewhere as "bar" under "layer_xxx_foo_", then the prefix should be "layer_xxx_foo_bar_".
        """
        if not self.is_determined(runtime_id):
            raise StructureGenerationException("Only determined structure can be converted to HDL")
        
        if not self.is_runtime_integrate(runtime_id):
            raise StructureGenerationException("Invalid (not integrate) runtime ID")
        
        if self.is_reusable: # clear previous prefix if reusable
            prefix = ""
        
        res = HDLFileModel(f"hdl_{prefix}{self.id[:8]}") # create file model and set entity name
        
        net_wires: Dict[Net, List[str, List[str]]] = {} # net -> (driver_wire_name, load_wire_names[])
        
        for port_full_name, port in self.ports_inside_flipped.nodes(): # add ports
            direction = "out" if port.origin_signal_type.belongs(Input) else "in" # ports_inside_flipped is IO flipped
            res.add_port(f"{port_full_name}", direction, port.get_type(runtime_id)) # use full name
            
            if net_wires.get(port.located_net) is None:
                net_wires[port.located_net] = [None, []]
            
            if port.origin_signal_type.belongs(Output):
                net_wires[port.located_net][0] = port_full_name
            else:
                net_wires[port.located_net][1].append(port_full_name)
        
        if self.is_operator: # custom generation for operator
            self.custom_generation(res, IOProxy(self.ports_inside_flipped, runtime_id.next(), flipped = True))
        else: # universal generation for non-operators
            for sub_inst_name, subs in self.substructures.items(): # instantiate components
                mapping = {}
                for port_full_name, port in subs.ports_outside[(self.id, sub_inst_name)].nodes(): # must use subs.ports_outside, which locates in self
                    port_wire_name = f"{sub_inst_name}_io_{port_full_name}" # inst_name_io_node_full_name
                    mapping[port_full_name] = port_wire_name
                    res.add_signal(port_wire_name, port.get_type(runtime_id)) # add signal for port wire
            
                    if net_wires.get(port.located_net) is None:
                        net_wires[port.located_net] = [None, []]
                    
                    if port.origin_signal_type.belongs(Output):
                        net_wires[port.located_net][0] = port_wire_name
                    else:
                        net_wires[port.located_net][1].append(port_wire_name)
                
                odhdl = subs.get_runtime(runtime_id).originally_determined_hdl_file_model # reuse HDL file model for the substructure
                if odhdl is not None:
                    res.inst_component(sub_inst_name, odhdl, mapping)
                else:
                    res.inst_component(sub_inst_name, subs.generation(runtime_id.next(), prefix + sub_inst_name + "_"), mapping)
        
        for net, (driver_wire_name, load_wire_names) in net_wires.items():
            if driver_wire_name is not None:
                if net.latency == 0: # comb
                    """
                                 +--> load_0
                                 |
                        driver --+--> load_i
                                 |
                                 +--> load_n
                    """
                    for load_wire_name in load_wire_names:
                        res.add_assignment(load_wire_name, driver_wire_name)
                else: # seq
                    """
                                                            +--> load_0
                                                            |
                        driver ----> reg_next | ... | reg --+--> load_i
                                                            |
                                                            +--> load_n
                    """
                    reg_next_name, reg_name = res.add_register(driver_wire_name, net.get_runtime(runtime_id).signal_type, latency = net.latency)
                    res.add_assignment(reg_next_name, driver_wire_name)
                    for load_wire_name in load_wire_names:
                        res.add_assignment(load_wire_name, reg_name)
        
        if self.is_reusable: # save HDL file model for originally determined structure
            self.get_runtime(runtime_id).set_originally_determined_hdl_file_model(res)
        
        return res
    
    def add_port(self, name: str, signal_type: SignalType) -> Node:
        if not signal_type.perfectly_io_wrapped:
            raise StructureException("Port signal type should be perfectly IO wrapped")
        
        def _extract(key: str, t: SignalType):
            if t.belongs(IOWrapper):
                return Node(key, t.flip_io(), located_structure = self) # (1.) io is flipped in ports_inside_flipped, (2.) ports inside are connected with internal nodes/nets, so located_structure is set to self
            elif t.belongs(Bundle):
                return StructuralNodes({k: _extract(key + "_" + k, v) for k, v in t._bundle_types.items()}) # node_name should be layered

        new_port = _extract(name, signal_type)
        self.ports_inside_flipped[name] = new_port
        
        return new_port
    
    def add_node(self, name: str, signal_type: SignalType, latency: int = 0) -> Node:
        if signal_type.io_wrapper_included:
            signal_type = signal_type.clear_io()
        
        new_node = Node(name, signal_type, located_structure = self)
        new_node.set_latency(latency)
        self.nodes.add(new_node) # remember to add to nodes, or it may be garbage collected
        
        return new_node
    
    def add_substructure(self, inst_name: str, structure: 'Structure') -> 'StructureProxy':
        if inst_name in self.substructures.keys():
            raise StructureException("Instance name already exists")
        
        self.substructures[inst_name] = structure # strong reference to the substructure
        structure.instance_number += 1
        # structure.located_structures_weak[self.id] = self # weak reference to the located structure in the substructure
        
        def _create(io: Union[Node, StructuralNodes]):
            if isinstance(io, Node):
                return Node(io.name, io.origin_signal_type.flip_io(), located_structure = self, port_of_structure = structure)
            else: # StructuralNodes
                return StructuralNodes({k: _create(v) for k, v in io.items()})
        
        structure.ports_outside[(self.id, inst_name)] = _create(structure.ports_inside_flipped) # duplicate and flip internal ports to create external ports
        
        return StructureProxy(structure, self.id, inst_name)
    
    def connect(self, node_1: Node, node_2: Node):
        node_1.merge(node_2)
    
    def connects(self, nodes: List[Node]):
        for idx, node in enumerate(nodes):
            if idx != 0:
                self.connect(nodes[0], node)

class NodeProxy:
    def __init__(self, node: Node, runtime_id: str, flipped: bool = False):
        self.proxy_node = node
        self.runtime_id = runtime_id
        self.flipped = flipped
    
    @property
    def dir(self):
        is_in = self.proxy_node.origin_signal_type.belongs(Input)
        return Input if is_in ^ self.flipped else Output
    
    @property
    def type(self):
        return self.proxy_node.get_type(self.runtime_id)
    
    def update(self, signal_type: SignalType):
        self.proxy_node.update_type(self.runtime_id, signal_type)

class IOProxy:
    def __init__(self, io: StructuralNodes, runtime_id: str, flipped: bool = True):
        self.proxy: Dict[str, Union[NodeProxy, IOProxy]] = {}
        
        for k, v in io.items():
            v: Union[Node, StructuralNodes]
            if isinstance(v, Node):
                self.proxy[k] = NodeProxy(v, runtime_id, flipped)
            else: # StructuralNodes
                self.proxy[k] = IOProxy(v, runtime_id, flipped)
    
    def __getattr__(self, name):
        if name in self.proxy.keys():
            return self.proxy[name]
        else:
            super().__getattr__(name)

class StructureProxy:
    """
        Structure proxy.
        Make convenient for user on getting structural ports. As a return value of add_substructure.
    """
    def __init__(self, structure: Structure, located_structure_id: str, inst_name: str = None):
        self.proxy_structure = structure # the structure to be proxied
        self.located_structure_id = located_structure_id # proxy the structure in the structure with located_structure_id
        self.inst_name: str = inst_name
    
    @property
    def IO(self):
        return self.proxy_structure.ports_outside[(self.located_structure_id, self.inst_name)]

