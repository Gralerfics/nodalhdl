from .core.structure import Structure, Node, StructuralNodes
from .core.signal import *
from .basic.arith import Add, Subtract

import json


class StructurePersistence:
    @staticmethod
    def to_json(structure: Structure) -> str:
        """
            Convert a Structure object and its substructures to a JSON string.
        """
        res_dict = { "structures": {} }
        
        def _to_dict(s: Structure, d: dict):
            # basic info
            s_dict = {
                "id": s.id,
                "unique_name": s.unique_name,
                "allow_reusing": s.allow_reusing,
                "custom_params": s.custom_params,
                "ports_inside_flipped": {},
                "ports_outside": [],
                "nodes_and_ports": {},
                "nets": {},
                "substructures": {}
            }
            
            def _add_node_or_port_and_nets(n: Node) -> dict:
                # add nets
                if n.located_net and n.located_net.id not in s_dict["nets"]:
                    s_dict["nets"][n.located_net.id] = {
                        "latency": n.located_net.latency
                    }
                
                # add nodes and ports
                s_dict["nodes_and_ports"][n.id] = {
                    "id": n.id,
                    "name": n.name,
                    "origin_signal_type": n.origin_signal_type.def_str(),
                    "is_port": n.is_port,
                    "located_net_id": n.located_net.id if n.located_net else None
                }
            
            def _convert_structural_nodes(obj: Union[StructuralNodes, Node]) -> dict:
                if isinstance(obj, Node):
                    _add_node_or_port_and_nets(obj)
                    return obj.id
                else:
                    return { k: _convert_structural_nodes(v) for k, v in obj.items() }
            
            # ports_inside_flipped
            s_dict["ports_inside_flipped"] = _convert_structural_nodes(s.ports_inside_flipped)
            
            # ports_outside
            for (sid, inst_name), ports in s.ports_outside.items():
                s_dict["ports_outside"][f"({sid}, {inst_name})"] = _convert_structural_nodes(ports)
            
            # current structure's info
            d["structures"][s.id] = s_dict
            
            # recursively add substructures
            for subs in s.substructures.values():
                _to_dict(subs, d)
        
        _to_dict(structure, res_dict)
        
        return json.dumps(res_dict, indent = 4)    
    @staticmethod
    def from_json(json_str: str) -> Structure:
        """
            Convert a JSON string back to a Structure object (with substructures references).
        """
        pass # TODO


"""
{
    "structures": {
        ...
        "... (sid)": <Structure> {
            "id": "...",
            "unique_name": "...",
            "allow_reusing": ...,
            "custom_params": { ... },
            "ports_inside_flipped": <StructuralNodes> {
                ...
                "...": "... (node_id)",
                ...
            },
            "ports_outside": {
                ...
                "(sid, inst_name)": <StructuralNodes> { ... },
                ...
            },
            "nodes_and_ports": {
                ...
                "... (node_id)": <Node> {
                    "id": "...",
                    "name": "...",
                    "origin_signal_type": <SignalType> "... (.def_str())",
                    "is_port": ...,
                    "located_net_id": "... (net_id)"
                },
                ...
            },
            "nets": {
                ...
                "... (net_id)": <Net> {
                    "latency": ...
                },
                ...
            },
            "substructures": {
                ...
                "... (inst_name)": "... (sid)",
                ...
            }
        },
        ...
    }
},
    # "types": {
    #     ...
    #     "Bundle_...": <SignalType> {
    #         "_base": "Bundle",
    #         "_args": {
    #             "a": {
    #                 "_base": "UInt",
                    
    #             }
    #         }
    #     },
    #     "... (type_name)": <SignalType> {
    #         "_base": "Input", # _base (& _args), 需要从 .signal 中 eval, 无 _args 则无参
    #         "_args": {
    #             "_type": "Bundle_..." # _type, types 中前面有的 type_name; 三者皆无的字典是真字典
    #         }
    #     }
    #     ...
    # }
"""