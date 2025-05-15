from .signal import *


def static(*args, **kwargs):
    def decorator(func):
        for k, v in {**kwargs, **{k: None for k in args}}.items():
            setattr(func, k, v)
        
        return func
    
    return decorator


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

