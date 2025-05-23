# This file is part of nodalhdl (https://github.com/Gralerfics/nodalhdl), distributed under the GPLv3. See LICENSE.

from .signal import *
from .structure import *

import hashlib


class UniqueNamingTemplates:
    """
        should be @staticmethod factories, returning a callable(cls, *args, **kwargs) wrapped by classmethod().
    """
    @staticmethod
    def args_kwargs_sha256_16():
        def _naming(cls, *args, **kwargs):
            return f"{cls.__name__}_{hashlib.sha256((str(args) + str(kwargs)).encode('utf-8')).hexdigest()[:16]}"
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
    def input_type_args_1i1o(input_name: str, output_name: str, output_type: SignalType = Auto):
        def _setup(input_type: SignalType = Auto):
            s = Structure()
            
            s.add_port(input_name, Input[input_type])
            s.add_port(output_name, Output[output_type])
            
            return s
        
        return _setup


class OperatorDeductionTemplates: # TODO 前两个太具体的要不要搬到 bits 里面去
    @staticmethod
    def equi_bases_wider_output_2i1o(input_path_1: str, input_path_2: str, output_path: str):
        def _deduction(s: Structure, io: IOProxy):
            i1, i2, o = io.access(input_path_1), io.access(input_path_2), io.access(output_path)
            
            # base type
            merged_base_type = i1.type.base_type.merge(i2.type.base_type).merge(o.type.base_type)
            o.update(merged_base_type)
            i1.update(merged_base_type)
            i2.update(merged_base_type)
            
            # width
            o.update(Bits[max(i1.type.W, i2.type.W)] if i1.type.W is not None and i2.type.W is not None else merged_base_type)
            i1.update(Bits[o.type.W] if i2.type.W is not None and o.type.W is not None and i2.type.W < o.type.W else merged_base_type)
            i2.update(Bits[o.type.W] if i1.type.W is not None and o.type.W is not None and i1.type.W < o.type.W else merged_base_type)
        
        return _deduction
    
    @staticmethod
    def equi_bases_add_width_output_2i1o(input_path_1: str, input_path_2: str, output_path: str):
        def _deduction(s: Structure, io: IOProxy):
            i1, i2, o = io.access(input_path_1), io.access(input_path_2), io.access(output_path)
            
            # base type
            merged_base_type = i1.type.base_type.merge(i2.type.base_type).merge(o.type.base_type)
            o.update(merged_base_type)
            i1.update(merged_base_type)
            i2.update(merged_base_type)
            
            # width
            o.update(Bits[i1.type.W + i2.type.W] if i1.type.W is not None and i2.type.W is not None else merged_base_type)
            i1.update(Bits[o.type.W - i2.type.W] if i2.type.W is not None and o.type.W is not None else merged_base_type)
            i2.update(Bits[o.type.W - i1.type.W] if i1.type.W is not None and o.type.W is not None else merged_base_type)
        
        return _deduction
    
    @staticmethod
    def equi_types(*port_paths):
        def _deduction(s: Structure, io: IOProxy):
            P = [io.access(path) for path in port_paths]
            
            full_type = Auto
            for p in P:
                full_type = full_type.merge(p.type)
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
            raise Exception("Method `generation` must be defined for an operator (only deduction method provided now)")
        
        # deduction and apply
        rid = RuntimeId.create()
        s.deduction(rid)
        if s.is_runtime_applicable:
            s.apply_runtime(rid)
        
        # register structure to the pool
        s.register_unique_name(maybe_unique_name)
        
        return s


class UniquelyNamedReusable(metaclass = UniquelyNamedReusableMeta):
    determined_in_determined_out_required = False
    
    @staticmethod
    def setup(*args, **kwargs) -> Structure:
        return Structure()
    
    """
        Define the following two methods to make it an operator (do not decomment here):

            @staticmethod
            def deduction(s: Structure, io: IOProxy): ...
            
            @staticmethod
            def generation(s: Structure, h: HDLFileModel, io: IOProxy): ...
        
        Notes:
            1. There are two main ways to help identify the port types:
                a. define origin_signal_type in setup();
                b. define deduction to deduce the types, which will be applied in UniquelyNamedReusableMeta.__call__().
            2. TODO 类型合法性的检查
                对于 basic_arch，内部结构不会因运行时类型发生变化，但内部结构对允许的类型也有要求，不满足可能导致错误；
                    故检查应该在任意时刻进行，或者说只要运行时类型更新，就应该问一下该结构，类型是否合法；
                    那么这个过程应该可以嵌入 custom_deduction 中，而在 UniquelyNamedReusable 这里可以单独拉出一个 assertion 函数，和 deduction 一起放入 custom_deduction。
                    而 setup 中的检查主要是限制用户调用的方式。
                关于 DIDO：
                    basic_arch 中应该都是满足 DIDO 性质的结构生成器，即可以有 Auto 或其他什么不定类型，但只要输入确定，输出也必须确定。
                    既然允许不定类型等，那么 deduction 就基本都是要实现的了，否则除非输出类型在 setup 中就被确定，运行时中将无法应对；
                    setup 中确定类型主要是配合首次 deduction 尽量使生成的模块直接可以 apply 变成 reusable 的。
                放一些典型的例子作为参考：
                    a. BitsUnsignedMultiply 的 setup 生成结构需要 W 属性（也即定态），并要求是 Bits，故严格来说 setup 中需要 assert 一下这点；
                        其结构一旦生成必然确定，输出类型也在 setup 中直接算出，所以不用 deduction（给 Auto 的话就算不 assert 也会在 setup 中出错）。
                    b. BitsAdd 只要求是 Bits，它直接实现 generation，所以不用一些属性，可以是 Auto 的，故 setup 结束后不一定类型确定；
                        那么就需要 deduction（类似的说明见下 DIDO）。
                    c. 类似 a. 中, BitsReductionOr 输出在 setup 中直接确定为 Bit，故不需要 deduction。
                    d. FxPMultiply 中更是需要 fully determined.
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
    naming = UniqueNamingTemplates.args_kwargs_sha256_16()


import sys
_current_module = sys.modules[__name__]
__all__ = [name for name in dir() if not name.startswith('_') and getattr(getattr(_current_module, name, None), "__module__", None) == __name__]

