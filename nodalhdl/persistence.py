from .core.structure import Structure

from .basic.arith import Add, Subtract


class StructurePersistence:
    pass


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
                "...": <Node> {
                    "name": "...",
                    "original_signal_type": "... (type_name, 和 types 中对应)",
                    "is_port": ...,
                    "located_net_id": "... (id, 随意 id, 和 nets 中对应即可)"
                },
                ...
            },
            "ports_outside": [
                ...
                {
                    "key": (sid, inst_name),
                    "value": <StructuralNodes> { ... }
                },
                ...
            ],
            "nodes": [
                ...
                <Node> { ... },
                ...
            ],
            "nets": {
                ...
                "... (id)": <Net> {
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
    },
    "types": {
        ...
        "... (type_name)": <SignalType> TODO
        ...
    }
}
"""