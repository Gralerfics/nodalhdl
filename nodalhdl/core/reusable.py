from .signal import *
from .structure import *

import hashlib


class UniqueNamingTemplates:
    """
        should be @staticmethod factories, returning a callable(cls, *args, **kwargs) wrapped by classmethod().
    """
    @staticmethod
    def args_kwargs_md5_16():
        def _naming(cls, *args, **kwargs):
            return f"{cls.__name__}_{hashlib.md5((str(args) + str(kwargs)).encode('utf-8')).hexdigest()[:16]}"
        return classmethod(_naming)
    
    @staticmethod
    def args_kwargs_all_values():
        def _naming(cls, *args, **kwargs):
            # seems that kwargs is consistent with the input ordering when iterating
            res = f"{cls.__name__}"
            res = res + "_" + "_".join(map(str, args)) if len(args) > 0 else res
            res = res + "_" + "_".join(map(str, kwargs.values())) if len(kwargs) > 0 else res
            return res
        return classmethod(_naming)


class OperatorSetupTemplates:
    @staticmethod
    def input_type_args_2i1o(input_name_1: str, input_name_2: str, output_name: str, output_type: SignalType = Auto):
        def _setup(input_type_1: SignalType = Auto, input_type_2: SignalType = None):
            if input_type_2 is None:
                input_type_2 = input_type_1
            
            s = Structure()
            
            s.add_port(input_name_1, Input[input_type_1])
            s.add_port(input_name_2, Input[input_type_2])
            s.add_port(output_name, Output[output_type])
            
            return s
        
        return _setup
    
    @staticmethod
    def input_type_args_1i1o(input_name: str = "a", output_name: str = "r", output_type: SignalType = Auto):
        def _setup(input_type: SignalType = Auto):
            s = Structure()
            
            s.add_port(input_name, Input[input_type])
            s.add_port(output_name, Output[output_type])
            
            return s
        
        return _setup


class OperatorDeductionTemplates:
    @staticmethod
    def wider_as_output_2i1o(input_path_1: str, input_path_2: str, output_path: str):
        def _deduction(s: Structure, io: IOProxy):
            i1, i2, o = io.access(input_path_1), io.access(input_path_2), io.access(output_path)
            
            merged_base = i1.type.base.merges(i2.type.base).merges(o.type.base)
            o.update(merged_base[max(i1.type.W, i2.type.W)] if hasattr(i1.type, "W") and hasattr(i2.type, "W") else merged_base)
            i1.update(merged_base[o.type.W] if hasattr(i2.type, "W") and hasattr(o.type, "W") and i2.type.W < o.type.W else merged_base)
            i2.update(merged_base[o.type.W] if hasattr(i1.type, "W") and hasattr(o.type, "W") and i1.type.W < o.type.W else merged_base)
        
        return _deduction
    
    @staticmethod
    def equal_types(*port_paths):
        def _deduction(s: Structure, io: IOProxy):
            P = [io.access(path) for path in port_paths]
            
            full_type = Auto
            for p in P:
                full_type = full_type.merges(p.type)
            for p in P:
                p.update(full_type)
        
        return _deduction


class UniquelyNamedReusableMeta(type):
    def __call__(cls, *args, **kwargs):
        # behavioral methods overriding
        """
            e.g. you can add customized `_naming: <func>` in kwargs to override the naming staticmethod defined in cls.
                and these attributes will be ignored later.
        """
        _setup = kwargs.pop("_setup", cls.setup)
        _deduction = kwargs.pop("_deduction", getattr(cls, "deduction", None))
        _generation = kwargs.pop("_generation", getattr(cls, "generation", None))
        _naming = kwargs.pop("_naming", cls.naming) # _naming = lambda *args, **kwargs: ..., no cls
        _unique_name = kwargs.pop("_unique_name", _naming(*args, **kwargs))
        
        # return existed reusable structure (will not be in the pool if not reusable)
        maybe_unique_name = _unique_name
        maybe_s = ReusablePool.fetch(maybe_unique_name)
        if maybe_s is not None:
            return maybe_s
        
        # setup
        s: Structure = _setup(*args, **kwargs)
        
        # save arguments
        s.custom_params["_setup_args"] = args
        s.custom_params["_setup_kwargs"] = kwargs
        
        # for operators
        s.custom_deduction = _deduction
        s.custom_generation = _generation
        if s.custom_deduction is None and s.custom_generation is not None: # custom_deduction can be passed
            s.custom_deduction = lambda s, io: None
        if s.custom_generation is None and s.custom_deduction is not None: # custom_generation is necessary
            raise Exception("generation method must be defined for an operator (only deduction method provided now)")
        
        # deduction and apply
        rid = RuntimeId.create()
        s.deduction(rid)
        if s.is_runtime_applicable:
            s.apply_runtime(rid)
        
        # only save reusable structures to the pool
        s.register_unique_name(maybe_unique_name)
        
        return s


class UniquelyNamedReusable(metaclass = UniquelyNamedReusableMeta):
    @staticmethod
    def setup(*args, **kwargs) -> Structure:
        return Structure()
    
    """
        Define the following two methods to make it an operator (do not decomment here):

            @staticmethod
            def deduction(s: Structure, io: IOProxy): ...
            
            @staticmethod
            def generation(s: Structure, h: HDLFileModel, io: IOProxy): ...
    """
    
    """
        `naming`:
            (*arg, **kwargs) may differ, but different arguments can lead to the same structure/unique_name (by defining `naming`);
            different structures must have different unique name;
            same structures can have different unique names, but not recommended.
        should be @classmethod, or UniqueNamingTemplates.<...> will automatically wrap classmethod(). Use:
            @classmethod
            def naming(cls, a: ...): # argument list (cls excluded) should be totally same to the setup(...)
                return ...
        or the template below.
    """
    naming = UniqueNamingTemplates.args_kwargs_md5_16()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

