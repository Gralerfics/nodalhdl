from .signal import SignalType, BundleType, Auto, IOWrapper, Input, Output, Bundle
from .hdl import HDLFileModel

import sys
import weakref
import uuid
import dill
from typing import List, Dict, Set, Tuple, Union


""" Id """
class RuntimeIdException(Exception): pass

class RuntimeId:
    """
        RuntimeId.get(id_str): runtime_id
        runtime_id.next(inst_name): next runtime_id
    """
    NULL_NAMESPACE = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
    id_pool: weakref.WeakValueDictionary[str, 'RuntimeId'] = weakref.WeakValueDictionary()
    
    def __init__(self, id_str: str = None):
        if id_str is None:
            raise RuntimeIdException("Please create a runtime id object using RuntimeId.create()")
        
        self.id_str: str = id_str
        self.nexts: Dict[str, RuntimeId] = {} # ensure the next ids are referenced by their previous id, or they might be GCed
    
    def __repr__(self):
        return f"<RuntimeId: {self.id_str}>"
    
    def _next(self, key: str):
        next_id_str = str(uuid.uuid5(RuntimeId.NULL_NAMESPACE, self.id_str + "_" + key)).replace('-', '')
        next_id = RuntimeId.get(next_id_str)
        return next_id
    
    @staticmethod
    def create():
        new_id_str = str(uuid.uuid5(RuntimeId.NULL_NAMESPACE, str(uuid.uuid4()))).replace('-', '')
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
    
    def next(self, key: str):
        if self.nexts.get(key) is None:
            self.nexts[key] = self._next(key)
        return self.nexts[key]


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
    
    def clear_runtimes(self):
        self.runtimes.clear()
    
    def __init__(self, located_structure: 'Structure'): # not allowed to create a Net/Node without a located structure
        self.id = str(uuid.uuid4()).replace('-', '')
        
        # references
        self.nodes_weak: weakref.WeakSet[Node] = weakref.WeakSet()
        self.located_structure_weak: weakref.ReferenceType[Structure] = weakref.ref(located_structure)
        
        self.driver: weakref.ReferenceType[Node] = None # driver node (also in nodes_weak) or None, should be only one, originlly Output; others are loads
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Net.Runtime] = weakref.WeakKeyDictionary()
    
    def __len__(self):
        return len(self.nodes_weak)
    
    def get_loads(self): # ports(*) that are not drivers
        return [n for n in self.nodes_weak if n is not self.driver() and n.is_port]
    
    """
        Latency management.
    """
    @property
    def is_sequential(self):
        return any([n.latency > 0 for n in self.nodes_weak])
    
    def transform_driver_latency_to_loads(self):
        """
            Move the driver latency to the loads.
            The driver latency will be set to 0, and the loads' latency will add the driver latency.
        """
        if self.driver() is None:
            return
        
        driver_latency = self.driver().latency
        for load in self.get_loads():
            load.set_latency(driver_latency + load.latency)
        
        self.driver().set_latency(0)
    
    def transform_to_best_distribution(self):
        """
            Move the latency to the drivers as more as possible.
            This minimizes the number of registers. (But in fact, registers on different loads in the same net might be optimized by most of the synthesizers.
        """
        if self.driver() is None:
            return
        
        loads = self.get_loads()
        loads_max_common_latency = min([load.latency for load in loads])
        for load in loads:
            load.set_latency(load.latency - loads_max_common_latency)

        self.driver().set_latency(self.driver().latency + loads_max_common_latency)
    
    """
        The following actions (add_node, separate_node and merge) may change the structural information.
        They should not be called by the user directly, but by the Node object.
    """
    def _add_node(self, node: 'Node'):
        if node in self.nodes_weak: # avoid duplicate add (note that `node.located_net is self` should not be used for checking: some nodes' located_net may be assigned previously, but have not been added to the nodes_weak)
            return
        
        if node.origin_signal_type.belongs(Output): # driver
            if self.driver is not None:
                raise StructureException("Net cannot have multiple drivers")
            self.driver = weakref.ref(node)
        
        self.nodes_weak.add(node)
        node.located_net = self
        
        self.clear_runtimes() # structural modification, runtime information should be cleared
    
    def _separate_node(self, node: 'Node'):
        if node not in self.nodes_weak:
            raise StructureException("Node not in net")
        
        if len(self.nodes_weak) == 1:
            return # only one node, no need to separate
        
        if self.driver is not None and self.driver() is node: # driver is removed
            self.driver = None
        
        self.nodes_weak.remove(node)
        Net(self.located_structure_weak())._add_node(node)
    
    def _merge(self, other: 'Net'):
        if self is other:
            return
        
        if self.located_structure_weak() is not other.located_structure_weak():
            raise StructureException("Cannot merge nets from different structures")
        
        if self.driver is not None and other.driver is not None:
            raise StructureException("Merged net cannot have multiple drivers")
        
        net_h, net_l = (self, other) if len(self) > len(other) else (other, self)
        for node in net_l.nodes_weak:
            net_h._add_node(node) # all nodes' located_net will be set to net_h and net_l will be garbage collected

class Node:
    """
        Circuit node.
    """
    def __init__(self, name: str, origin_signal_type: SignalType, is_port: bool, located_structure: 'Structure' = None, located_net: Net = None, latency: int = 0, layered_name: str = None):
        # properties
        self.id = str(uuid.uuid4()).replace('-', '')
        self.name: str = name # raw name, no need to be unique. layer information for ports will be added in StructuralNodes.nodes()
        self.layered_name: str = layered_name if layered_name is not None else name # a.k.a. full name in structural ports
        self.origin_signal_type: SignalType = origin_signal_type # must be set by set_origin_type()
        self.is_port: bool = is_port
        self.latency: int = latency # latency, only for ports
        # [NOTICE] 关于直接串联多个寄存器可能导致的 Hold 违例问题. 应该在前端考虑还是留待后端考虑?
        if self.latency > 0 and not self.is_port:
            raise StructureException("Latency can only be set for ports")
        
        # properties (for ports in ports_outside)
        self.of_structure_inst_name: str = None # ports and only ports in ports_outside have this property
        
        # references
        self.located_net: Net = located_net # strong reference to Net
        
        if self.located_net is not None:
            if located_structure is not None:
                raise StructureException(f"located_structure not needed when located_net is provided")
            self.located_net._add_node(self) # add_node() will set located_net to self
        else:
            if located_structure is None:
                raise StructureException(f"located_structure is needed when located_net is not provided")
            Net(located_structure)._add_node(self) # add_node() will update runtime signal type, so no need to be called after assigning origin_signal_type
    
    def __repr__(self):
        return f"Node<{self.name} ({self.layered_name}), {self.origin_signal_type.base}, {self.of_structure_inst_name}>"
    
    @property
    def is_originally_determined(self):
        return self.origin_signal_type.determined
    
    @property
    def located_structure(self):
        return self.located_net.located_structure_weak()
    
    def is_determined(self, runtime_id: RuntimeId):
        return self.get_type(runtime_id).determined

    def runtime_info(self, runtime_id: RuntimeId):
        return f"<Node {self.name} ({self.get_type(runtime_id).__name__})>"
    
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
    def _structural_modification(self):
        self.located_structure._structural_modified()
    
    def set_origin_type(self, signal_type: SignalType, safe_modification: bool = False):
        if self.origin_signal_type is signal_type: # no change
            return

        self.origin_signal_type = signal_type
        
        if not safe_modification: # safe_modification: this modification do not influence runtime info
            self._structural_modification() # structural modification

    def merge(self, other: 'Node'):
        if self.located_net is other.located_net: # same net, no change
            return
        
        self.located_net._merge(other.located_net)
        
        self._structural_modification() # structural modification
    
    def counteract(self, other: 'Node', equiv_node_name: str = ""):
        if self.located_net is other.located_net: # same net, no change
            return
        
        if not self.is_port or not other.is_port:
            raise StructureException("Counteract only allowed between an inside port (other) and its outside port (self)")
        
        # add equivalent node (reserve original signal type info)
        equiv_node_type = other.origin_signal_type.merges(other.origin_signal_type)
        equiv_node = Node(equiv_node_name, equiv_node_type, is_port = False, located_net = self.located_net)
        self.located_structure.nodes.add(equiv_node)

        # latency setting
        driver_node, load_node = (self, other) if self.origin_signal_type.belongs(Output) else (other, self)
        driver_node.set_latency(driver_node.latency + load_node.latency)
        load_node.set_latency(0)
        driver_node.located_net.transform_driver_latency_to_loads()
        
        # remove two nodes
        n_self, n_other = self.located_net, other.located_net
        n_self._separate_node(self)
        n_other._separate_node(other)
        n_self._merge(n_other)
        
        self._structural_modification() # structural modification
    
    def separate(self):
        if len(self.located_net) == 1: # only one node, no need to separate
            return
        
        self.located_net._separate_node(self)
        
        self._structural_modification() # structural modification
    
    def delete(self):
        if self.is_port:
            raise StructureException("Cannot delete a port node")
        
        self.located_net.nodes_weak.remove(self) # theoretically not necessary. this node should have been GCed after located_structure.nodes.remove()
        self.located_structure.nodes.remove(self)
        
        self._structural_modification() # structural modification

    """
        Latency setting will not change the structural information (i.e. influence runtime type infos). Types are passed through the registers.
    """
    def set_latency(self, latency: int):
        if not self.is_port:
            raise StructureException("Cannot set latency for non-port node")
        self.latency = latency
    
    def incr_latency(self, incr: int):
        self.set_latency(self.latency + incr)

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
    
    def runtime_info(self, runtime_id: RuntimeId):
        return "[" + ", ".join([n.runtime_info(runtime_id) for _, n in self.nodes()]) + "]"
    
    def connect(self, other: 'StructuralNodes'):
        for k, v in self.items():
            if isinstance(v, Node):
                v.merge(other[k])
            elif isinstance(v, StructuralNodes):
                v.connect(other[k])
    
    def nodes(self, prefix: str = "", filter: str = "all", flipped: bool = False) -> List[Tuple[str, Node]]:
        """
            Return all Node objects in a list with their full names.
            The full name contains the layer information, e.g. "foo_bar_baz".
            `filter` can be "all", "in" or "out" to filter the ports with the given direction.
                `flipped` is used with `filter` to indicate that whether the ports' directions are flipped, e.g. in ports_inside_flipped.
        """
        real_filter = "in" if flipped and filter == "out" else ("out" if flipped and filter == "in" else filter)
        
        res = []
        for k, v in self.items():
            if isinstance(v, Node):
                if real_filter == "all" or (real_filter == "in" and v.origin_signal_type.belongs(Input)) or (real_filter == "out" and v.origin_signal_type.belongs(Output)):
                    res.append((prefix + v.name, v))
            elif isinstance(v, StructuralNodes):
                res.extend(v.nodes(prefix + k + "_", filter, flipped))
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
            
            # references
            self.attach_structure: weakref.ReferenceType[Structure] = weakref.ref(attach_structure) # the structure this runtime is attached to

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
    
    def _structural_modified(self):
        self.clear_runtimes() # clear runtime info
        self.reusable_hdl = None
        self.timing_info = None
    
    def __init__(self, unique_name: str = None):
        # properties
        self.id = str(uuid.uuid4()).replace('-', '')
        self.unique_name: str = unique_name
        
        # properties (customized params, some for operators)
        self.custom_params = {}
        self.custom_sequential: bool = False # should be asserted to True if there are registers in custom_generation (raw_content)
        self.custom_deduction: callable = None
        self.custom_generation: callable = None
        
        # properties (destroy when structural information changed)
        self.reusable_hdl: HDLFileModel = None # only for reusable structure
        self.timing_info: Dict[Tuple[str, str], float] = None # timing info after STA, (I-port full name, O-port full name) -> delay
        
        # references (internal structure)
        self.ports_inside_flipped: StructuralNodes = StructuralNodes() # to be connected to internal nodes, IO flipped (EEB)
        self.substructures: Dict[str, 'Structure'] = {} # instance_name -> structure
        self.nodes: Set[Node] = set() # non-IO nodes
        
        # references (external structure)
        self.ports_outside: Dict[Tuple[str, str], StructuralNodes] = {} # Tuple[located_structure_id, inst_name_in_that_structure] -> IO in the located structure
        
        # runtime
        self.runtimes: weakref.WeakKeyDictionary[RuntimeId, Structure.Runtime] = weakref.WeakKeyDictionary() # runtime_id -> runtime info
    
    @property
    def instance_number(self):
        return len(self.ports_outside.keys())
    
    @property
    def is_operator(self):
        """
            Check if the structure is an operator, i.e. not allowed to expand.
            Some structures do not have substructures, but they are not operators; operators should have no substructures.
        """
        return self.custom_deduction is not None and self.custom_generation is not None
    
    @property
    def is_reusable(self): # i.e. originally determined
        ports_determined = all([p.is_originally_determined for _, p in self.ports_inside_flipped.nodes()])
        substructures_determined = all([s.is_reusable for s in self.substructures.values()])
        return ports_determined and substructures_determined
    
    @property
    def is_sequential(self):
        ports_inside_nets_flag = any([p.latency > 0 for _, p in self.ports_inside_flipped.nodes()])
        subs_ports_outside_nets_flag = any([any([p.latency > 0 for _, p in self.get_subs_ports_outside(subs_inst_name).nodes()]) for subs_inst_name in self.substructures.keys()])
        return ports_inside_nets_flag or subs_ports_outside_nets_flag or self.custom_sequential or any([subs.is_sequential for subs in self.substructures.values()])
    
    @property
    def is_singleton(self):
        return (self.is_operator or self.instance_number <= 1) and all([subs.is_singleton for subs in self.substructures.values()])
    
    @property
    def is_strictly_singleton(self):
        return self.instance_number <= 1 and all([subs.is_singleton for subs in self.substructures.values()])
    
    @property
    def is_runtime_applicable(self):
        """
            Check if the structure and all its originally undetermined substructures are singletons, i.e. do not have multiple located structures.
            Only these structures can apply runtime information.
            Originally determined structures have same information that they will not conflict.
        """
        return self.is_reusable or (self.instance_number <= 1 and all([subs.is_runtime_applicable for subs in self.substructures.values()]))
    
    @property
    def is_flattened(self):
        return all([subs.is_operator for subs in self.substructures.values()])
    
    @property
    def is_flatly_timed(self):
        return all([subs.timing_info is not None for subs in self.substructures.values()])

    def is_runtime_integrate(self, runtime_id: RuntimeId):
        """
            Check if the structure and all its substructures have runtime information with runtime_id.
            Runtime information in structures will be cleared when there are structural modifications.
            No need to check all nodes and ports, their runtime information should be called by the structures.
        """
        return runtime_id in self.runtimes.keys() and all([subs.is_runtime_integrate(runtime_id.next(sub_inst_name)) for sub_inst_name, subs in self.substructures.items()])
    
    def is_determined(self, runtime_id: RuntimeId): # all ports and substructures are determined
        ports_determined = all([p.is_determined(runtime_id) for _, p in self.ports_inside_flipped.nodes()])
        substructures_determined = all([s.is_determined(runtime_id.next(n)) for n, s in self.substructures.items()])
        return ports_determined and substructures_determined
    
    def runtime_info(self, runtime_id: RuntimeId, indent: int = 0, fqn: str = "<root>"):
        res = " " * indent + f"{fqn} ({self.id[:8]}, {self.instance_number} ref(s){", R" if self.is_reusable else ""}), IO: {self.ports_inside_flipped.runtime_info(runtime_id)}.\n"
        for sub_inst_name, subs in self.substructures.items():
            res += subs.runtime_info(runtime_id.next(sub_inst_name), indent + 4, fqn + "." + sub_inst_name)
        return res
    
    def get_nets(self) -> List[Net]:
        """
            Traverse the structure and return all nets connected to the ports and nodes.
        """
        res: Set[Net] = set()
        
        for _, port in self.ports_inside_flipped.nodes():
            res.add(port.located_net)
        
        for sub_inst_name, subs in self.substructures.items():
            for _, port in subs.ports_outside[(self.id, sub_inst_name)].nodes():
                res.add(port.located_net)
        
        for node in self.nodes:
            res.add(node.located_net)
        
        return list(res)
    
    def get_subs_ports_outside(self, subs_inst_name: str) -> StructuralNodes:
        return self.substructures[subs_inst_name].ports_outside[(self.id, subs_inst_name)]
    
    def duplicate(self) -> 'Structure':
        """
            Deep copy of the structure.
            Reusable substructures under the structure will also be duplicated, and certainly not including ports_outside those are not under this new structure.
        """
        s_build_map: Dict[Structure, Structure] = {} # reference structure -> duplicated structure
        
        def _duplicate(ref_s: Structure):
            new_s = Structure()
            
            new_s.unique_name = ref_s.unique_name
            new_s.reusable_hdl = ref_s.reusable_hdl # ?
            
            new_s.custom_params = ref_s.custom_params.copy()
            new_s.custom_deduction = ref_s.custom_deduction
            new_s.custom_generation = ref_s.custom_generation
            
            # nets
            net_build_map: Dict[Net, Net] = {} # reference net -> duplicated net
            
            def _trace_net(ref_node: Node) -> Net: # check if the located_net of ref_node is already duplicated, return net'
                ref_net = ref_node.located_net
                if net_build_map.get(ref_net) is not None:
                    return net_build_map[ref_net]
                else:
                    new_net = Net(new_s)
                    net_build_map[ref_net] = new_net
                    return new_net
            
            # ports
            def _build_ports(ref: Union[StructuralNodes, Node]) -> StructuralNodes:
                if isinstance(ref, Node):
                    # check if the net is already duplicated, obtain new_net (net')
                    new_net = _trace_net(ref)
                    
                    # duplicate the port under net'
                    new_port = Node(ref.name, ref.origin_signal_type, is_port = ref.is_port, located_net = new_net, latency = ref.latency, layered_name = ref.layered_name)
                    return new_port
                else: # StructuralNodes
                    return StructuralNodes({k: _build_ports(v) for k, v in ref.items()})
            
            # internal ports
            new_s.ports_inside_flipped = _build_ports(ref_s.ports_inside_flipped)
            
            # internal nodes
            for ref_node in ref_s.nodes:
                # check if the net is already duplicated, obtain new_net (net')
                new_net = _trace_net(ref_node)
                
                # duplicate the node under net'
                new_node = Node(ref_node.name, ref_node.origin_signal_type, is_port = ref_node.is_port, located_net = new_net, latency = ref_node.latency)
                new_s.nodes.add(new_node)
            
            # substructures
            for sub_inst_name, ref_subs in ref_s.substructures.items():
                # check if the substructure is already duplicated, obtain new_subs (subs')
                if s_build_map.get(ref_subs) is not None:
                    new_subs = s_build_map[ref_subs]
                else:
                    new_subs = _duplicate(ref_subs)
                    s_build_map[ref_subs] = new_subs
                
                # new_s.substructures
                new_s.substructures[sub_inst_name] = new_subs
                
                # new_subs.ports_outside
                new_subs_ports_outside = _build_ports(ref_subs.ports_outside[(ref_s.id, sub_inst_name)])
                for _, p in new_subs_ports_outside.nodes():
                    p.of_structure_inst_name = sub_inst_name
                new_subs.ports_outside[(new_s.id, sub_inst_name)] = new_subs_ports_outside
            
            return new_s
        
        return _duplicate(self)
    
    def strip(self, deep: bool = False, deep_to_operators: bool = False) -> 'Structure':
        """
            Strip the structure, i.e. duplicate and reassign the substructures those are referenced more than once.
            After strip the structure can perform apply_runtime().
            `deep`: process reusable substructures if True, False by default. After deep-strip (singletonize), expand() can be performed.
            `deep_to_operators`: if deep is True, deep_to_operators will decide if the operators should be stripped.
        """
        res = self.duplicate() if self.instance_number > 1 and (not self.is_reusable or deep) else self
        
        def _strip(s: Structure):
            for sub_inst_name, subs in dict(s.substructures).items(): # copy the dict to avoid dynamic modification
                """
                    if subs.instance_number > 1, it might be needed to be stripped, in this case:
                        if not subs.is_reusable, it should be stripped;
                        or it is a reusable substructure, but deep is True, it might be needed to be stripped, in this case:
                            if not subs.is_operator, it should be stripped;
                            or it is an operator, but deep_to_operators is True, it should also be stripped.
                """
                if subs.instance_number > 1 and (not subs.is_reusable or (deep and (not subs.is_operator or deep_to_operators))):
                    # need to strip
                    new_subs = subs.duplicate()
                    
                    # move ports_outside from (ref_)subs to new_subs (just move, of_structure_inst_name is not changed)
                    new_subs.ports_outside[(s.id, sub_inst_name)] = subs.ports_outside[(s.id, sub_inst_name)]
                    del subs.ports_outside[(s.id, sub_inst_name)]
                    
                    # replace the substructure
                    s.substructures[sub_inst_name] = new_subs
                    
                    _strip(new_subs) # recursive strip on new substructure
                else:
                    # current structure do not need to be stripped (substructures could need), recursive strip
                    _strip(subs)
        
        _strip(res)
        
        return res
    
    def singletonize(self, singletonize_operators: bool = False):
        self.strip(deep = True, deep_to_operators = singletonize_operators)
    
    def expand(self, shallow: bool = False):
        """
            Expand the substructures, w/o operators.
            Must be singleton, i.e. instance_number <= 1 or .is_operator for all substructures, which can be achieved by singletonize().
                P.S. the ports_inside of the `reusable substructures which are not operators` are going to be moved out, so they should be singleton.
                     operators need not be expanded, so they can be reused.
                     so asserting .is_singleton instead of .is_strictly_singleton is enough.
            `shallow`: only expand one level, False by default. If False, expand iteratively until there are only operators in substructures[].
            
            Notes when expanding:
                (1.) `self`, `subs` and `sub_subs`. We need to move out `sub_subs` and remove `subs`.
                (2.) Elements to be moved out: subs.ports_inside_flipped, subs.nodes, subs.substructures[] (sub_subs), sub_subs.ports_outside[].
                (3.) For subs.ports_inside_flipped: it should be counteract with subs.ports_outside[], leaving an equivalent node, keeping the origin type.
                (4.) All nets under subs should be moved out (modify .located_structure_weak) from `subs` into `self`.
                (5.) When moving out, elements with inst_name should add a prefix (the inst_name of subs).
                (6.) sub_subs.ports_outside[]'s key should be updated (subs.id -> self.id, inst_name -> new_inst_name).
        """
        if not self.is_singleton:
            raise StructureException("Only singleton structure can be expanded")
        
        first_round = True
        while first_round or not shallow:
            first_round = False
            non_operator_exists = False
            new_substructures: Dict[str, Structure] = {}
            
            # expand substructures (shallow, w/o operators)
            for sub_inst_name, subs in self.substructures.items():
                if subs.is_operator:
                    # operator, move into new_substructures
                    new_substructures[sub_inst_name] = subs
                else:
                    # non-operator, expand
                    non_operator_exists = True
                    
                    # merge subs.ports_inside_flipped and subs.ports_outside
                    sub_ports_o, sub_ports_i = sorted(subs.ports_outside[(self.id, sub_inst_name)].nodes()), sorted(subs.ports_inside_flipped.nodes())
                    for idx in range(len(sub_ports_o)):
                        sub_port_o, sub_port_i = sub_ports_o[idx][1], sub_ports_i[idx][1]
                        
                        # merge net
                        sub_port_i.located_net.located_structure_weak = weakref.ref(self)
                        sub_port_o.counteract(sub_port_i, equiv_node_name = sub_inst_name + "_io_" + sub_port_i.name) # counteract, this two ports removed, type merged and assigned to a equi node, latency merged
                    
                    # move out the nodes
                    for sub_node in subs.nodes:
                        sub_node.located_net.located_structure_weak = weakref.ref(self)
                        sub_node.name = sub_inst_name + "_" + sub_node.name # nodes are not generated in generation(), only provide information in dedution(), so the names do not matter
                        self.nodes.add(sub_node)
                        subs.nodes.remove(sub_node)
                    
                    # sub-substructures
                    for sub_sub_inst_name, sub_subs in subs.substructures.items():
                        new_inst_name = sub_inst_name + "_" + sub_sub_inst_name
                        
                        # modify ports_outside keys
                        sub_sub_ports_o = sub_subs.ports_outside[(subs.id, sub_sub_inst_name)]
                        sub_subs.ports_outside[(self.id, new_inst_name)] = sub_sub_ports_o
                        del sub_subs.ports_outside[(subs.id, sub_sub_inst_name)]
                        
                        # modify the ports' of_structure_inst_name in ports_outside
                        # and move out the nets connected to sub_subs's ports_outside
                        for _, p in sub_sub_ports_o.nodes():
                            p.of_structure_inst_name = new_inst_name
                            p.located_net.located_structure_weak = weakref.ref(self)
                        
                        # move out
                        new_substructures[new_inst_name] = sub_subs
            
            # replace substructures, old one will be GCed
            self.substructures = new_substructures
            
            if not non_operator_exists: # all expanded
                break
    
    def apply_runtime(self, runtime_id: RuntimeId):
        """
            Fix the runtime information under runtime_id into the structure.
            The structure should be runtime_applicable and runtime-integrate.
            (*) note:
                set_origin_type() will be called, which clears the runtime information in the structure (not in the net so do not worry that node.get_type(runtime_id) will fail after calling set_origin_type).
                but if the runtime information is applied, the change must be safe, the runtime_id should be kept valid.
                e.g. the user wants to apply an RID to a structure and then use its generation, if the RID information is destroyed as mentioned above, there will be a problem;
                this behavior is reasonable, so the RID information should be retained, by asserting `do_not_clear_structure_runtime = True` in set_origin_type().
        """
        if self.is_reusable: # no need to apply runtime for reusable structure
            return
        
        if not self.is_runtime_applicable:
            raise StructureException("The structure cannot apply runtime")
        
        if not self.is_runtime_integrate(runtime_id):
            raise StructureException("Invalid (not integrate) runtime ID")
        
        for _, port in self.ports_inside_flipped.nodes(): # apply runtime info to internal nodes
            port.set_origin_type(port.origin_signal_type.applys(port.get_type(runtime_id)), safe_modification = True) # (*)
        
        for ports in self.ports_outside.values(): # apply runtime info to all outside ports
            for _, port in ports.nodes():
                port.set_origin_type(port.origin_signal_type.applys(port.get_type(runtime_id)), safe_modification = True) # (*)
        
        for node in self.nodes: # apply runtime info to all nodes (may be not necessary)
            node.set_origin_type(node.origin_signal_type.applys(node.get_type(runtime_id)), safe_modification = True) # (*)
        
        for sub_inst_name, subs in self.substructures.items(): # apply runtime info to all substructures, recursively
            subs.apply_runtime(runtime_id.next(sub_inst_name))
    
    def deduction(self, runtime_id: RuntimeId):
        """
            Automatic type deduction.
        """
        structure_runtime = self.get_runtime(runtime_id) # ensure runtime information is created, for integrity consideration
        
        if self.is_operator:
            self.custom_deduction(self, IOProxy(self.ports_inside_flipped, runtime_id, flipped = True))
            return
        
        while not self.is_determined(runtime_id): # stop if already determined
            structure_runtime.deduction_effective = False # reset flag before a new round of deduction
            
            """
                subs.ports_outside[] are under the structure `self` (with runtime_id);
                subs.ports_inside_flipped is under the substructure `subs` (with next_runtime_id).
            """
            for sub_inst_name, subs in self.substructures.items():
                # update substructure's ports with external ports (should be synchronized even though determined, the same below)
                subs.ports_inside_flipped.update_runtime(runtime_id.next(sub_inst_name), subs.ports_outside[(self.id, sub_inst_name)], runtime_id) # s.ports_outside[(self.id, sub_inst_name)] is the IO of `s` connected in `self`
                
                """
                    deduction() should be recursively executed on all substructures, so that the runtime information can be passed down,
                    in order to maintain the integrity of the runtime information.
                    (*) Why some time the runtime information is passed down without deduction?
                        Because is_determined(rid) called get_type(rid) in ports, which will create runtime information for the net.
                        When initialized, reset_type will be called, and then merge_type, then set_type, which will fetch runtime information for the structure (if type changed).
                """
                subs.deduction(runtime_id.next(sub_inst_name)) # recursive deduction
                
                # update external ports with substructure's ports
                subs.ports_outside[(self.id, sub_inst_name)].update_runtime(runtime_id, subs.ports_inside_flipped, runtime_id.next(sub_inst_name))
            
            if not structure_runtime.deduction_effective: # no change, stop
                break
    
    def generation(self, runtime_id: RuntimeId, top_module_name: str = "root") -> HDLFileModel: # `top_module_name` is better to be called `prefix` for sub-levels
        """
            Generate HDL file model.
            prefix: e.g. this structure is instanced in somewhere as "bar" under "layer_xxx_foo_", then the prefix should be "layer_xxx_foo_bar_".
        """
        if not self.is_determined(runtime_id):
            raise StructureGenerationException("Only determined structure can be converted to HDL")
        
        if not self.is_runtime_integrate(runtime_id):
            raise StructureGenerationException("Invalid (not integrate) runtime ID")
        
        # naming
        if self.is_reusable:
            if self.reusable_hdl is not None:
                return self.reusable_hdl
            else:
                top_module_name = self.unique_name if self.unique_name is not None else self.id[:8]
        
        # create file model and set entity name
        model = HDLFileModel(entity_name = f"{top_module_name}", file_name = f"hdl_{top_module_name}")
        
        net_wires: Dict[Net, List[List[str, int], List[List[str, int]]]] = {} # net -> [[driver_wire_name, latency], [[load_wire_name, latency], ...]]
        
        def fill_net_wires(port: Node, wire_name: str):
            if net_wires.get(port.located_net) is None:
                net_wires[port.located_net] = [[None, 0], []]
            
            if port.origin_signal_type.belongs(Output):
                net_wires[port.located_net][0] = [wire_name, port.latency] # add driver
            else:
                net_wires[port.located_net][1].append([wire_name, port.latency]) # add load
        
        # add ports into model according to ports_inside_flipped
        for port_full_name, port in self.ports_inside_flipped.nodes():
            direction = "out" if port.origin_signal_type.belongs(Input) else "in" # ports_inside_flipped is IO flipped
            model.add_port(f"{port_full_name}", direction, port.get_type(runtime_id)) # use full name
            
            # fill net_wires
            fill_net_wires(port, wire_name = port_full_name)
        
        # substructures
        if self.is_operator:
            # custom generation for operator
            self.custom_generation(self, model, IOProxy(self.ports_inside_flipped, runtime_id, flipped = True))
        else:
            # universal generation for non-operators
            for sub_inst_name, subs in self.substructures.items():
                mapping = {}
                for port_full_name, port in subs.ports_outside[(self.id, sub_inst_name)].nodes(): # must use subs.ports_outside, which locates in self
                    port_wire_name = f"{sub_inst_name}_io_{port_full_name}" # inst_name_io_node_full_name
                    mapping[port_full_name] = port_wire_name
                    model.add_signal(port_wire_name, port.get_type(runtime_id)) # add signal for port wire

                    # fill net_wires
                    fill_net_wires(port, wire_name = port_wire_name)
                
                model.inst_component(sub_inst_name, subs.generation(runtime_id.next(sub_inst_name), top_module_name + "_" + sub_inst_name), mapping)
        
        # build nets according to net_wires
        for net, ((driver_wire_name, driver_latency), loads_info) in net_wires.items():
            if driver_wire_name is not None:
                """
                    driver_wire_name (= center_wire_name)
                """
                center_wire_name = driver_wire_name
                
                # driver
                if driver_latency > 0:
                    """
                        driver_wire_name --> reg_next_0_d_{name} | ... | reg_{l-1}_d_{name} (= center_wire_name)
                    """
                    reg_next_name, reg_name = model.add_register("d_" + driver_wire_name, net.get_runtime(runtime_id).signal_type, latency = driver_latency)
                    model.add_assignment(reg_next_name, driver_wire_name)
                    center_wire_name = reg_name
                
                # loads
                for idx, (load_wire_name, load_latency) in enumerate(loads_info):
                    """
                        center_wire_name (= end_wire_name)
                    """
                    end_wire_name = center_wire_name
                    
                    if load_latency > 0:
                        """
                            center_wire_name --> reg_next_0_l_{name} | ... | reg_{l-1}_l_{name} (= end_wire_name)
                        """
                        reg_next_name, reg_name = model.add_register(f"l_" + load_wire_name, net.get_runtime(runtime_id).signal_type, latency = load_latency)
                        model.add_assignment(reg_next_name, center_wire_name)
                        end_wire_name = reg_name
                    
                    """
                        end_wire_name --> load_wire_name
                    """
                    model.add_assignment(load_wire_name, end_wire_name)
        
        # save model for reusable structures
        if self.is_reusable:
            self.reusable_hdl = model
        
        return model
    
    def add_port(self, name: str, signal_type: SignalType) -> Node:
        if not signal_type.perfectly_io_wrapped:
            raise StructureException("Port signal type should be perfectly IO wrapped")
        
        def _extract(key: str, t: SignalType, prefix: str = ""):
            """
                Extract sub-ports with IOWrapper as independent Node objects.
                The names are the raw names, instead of the full names (with layer information).
                StructuralNodes().nodes() will add the layer information to the returned full names.
            """
            if t.belongs(IOWrapper):
                return Node(key, t.flip_io(), is_port = True, located_structure = self, layered_name = prefix + key) # (1.) io is flipped in ports_inside_flipped, (2.) ports inside are connected with internal nodes/nets, so located_structure is set to self
            elif t.belongs(Bundle):
                return StructuralNodes({k: _extract(k, v, prefix = prefix + key + "_") for k, v in t._bundle_types.items()})

        new_port = _extract(name, signal_type)
        self.ports_inside_flipped[name] = new_port
        
        return new_port
    
    def add_node(self, name: str, signal_type: SignalType) -> Node:
        if signal_type.io_wrapper_included:
            signal_type = signal_type.clear_io()
        
        new_node = Node(name, signal_type, is_port = False, located_structure = self)
        self.nodes.add(new_node) # remember to add to nodes, or it may be garbage collected
        
        return new_node
    
    def add_substructure(self, inst_name: str, structure: 'Structure') -> 'StructureProxy':
        if inst_name in self.substructures.keys():
            raise StructureException("Instance name already exists")
        
        self.substructures[inst_name] = structure # strong reference to the substructure
        
        def _create(io: Union[Node, StructuralNodes]):
            if isinstance(io, Node):
                new_port = Node(io.name, io.origin_signal_type.flip_io(), is_port = True, located_structure = self, layered_name = io.layered_name)
                new_port.of_structure_inst_name = inst_name
                return new_port
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
    
    def save_dill(self, file_path: str):
        with open(file_path, "wb") as f:
            dill.dump(self, f)
    
    @classmethod
    def load_dill(self, file_path: str) -> 'Structure':
        # [NOTICE] (1.) traverse the structure and rebuild the SignalType(s)? (2.) 除了 SignalType 这种, 像 arith 这种带 pool 的情况, 读取后 pool 是没有的, 会不会导致对象不一致?
        with open(file_path, "rb") as f:
            return dill.load(f)

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

