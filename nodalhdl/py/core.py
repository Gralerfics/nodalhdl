from ..core.signal import *

from typing import Dict, Tuple


class ComputeElement:
    """
        对其的运算会记录轨迹（计算图）
        Variable / Element
        
        TODO 这里的重载信息如何记录到Engine中？
    """
    def __init__(self, type_tuple: Tuple):
        self.type_tuple: Tuple = type_tuple
        self.track = None
        pass # TODO
    
        # runtime
        # self.signal_type = 


class Engine:
    def __init__(self):
        self.convertors: Dict[Tuple, callable] = {}
    
    """
        actions
    """
    def register_convertor(type_keys: Tuple, func: callable):
        pass
    
    def combinational_to_structure(f: callable):
        pass


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

